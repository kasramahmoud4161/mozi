from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q # <- Q و Count را اضافه کنید
from django.db import transaction
from django.http import Http404

from .models import Conversation, Message
from .forms import MessageForm
# Profile را هم برای لیست کردن کاربران نیاز داریم
from blog.models import MyUser, Profile 

@login_required
def chat_list_view(request):
    """
    نمایش لیست تمام مکالمات کاربر، همراه با تعداد خوانده نشده‌ها.
    """
    
    # شمارش پیام‌هایی که خوانده نشده (is_read=False)
    # و فرستنده آن‌ها کاربر فعلی نیست (sender != request.user)
    conversations = request.user.conversations.all().prefetch_related(
        'participants__profile'
    ).annotate(
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user)
        )
    ).order_by('-updated_at') # مرتب‌سازی بر اساس آخرین فعالیت
    
    context = {
        'conversations': conversations
    }
    return render(request, 'chat/message_list.html', context)


@login_required
@transaction.atomic
def chat_detail_view(request, conversation_id):
    """
    نمایش پیام‌های یک مکالمه خاص و مدیریت ارسال پیام جدید.
    """
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related('messages__sender__profile', 'participants__profile'),
        id=conversation_id
    )
    
    if request.user not in conversation.participants.all():
        raise Http404("شما اجازه دسترسی به این مکالمه را ندارید.")

    # پس از ورود کاربر به چت، تمام پیام‌های خوانده نشده را "خوانده شده" می‌کنیم
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            
            conversation.save() 
            
            return redirect('chat:chat_detail', conversation_id=conversation_id)
    else:
        form = MessageForm()
        
    context = {
        'conversation': conversation,
        'messages': conversation.messages.all(),
        'form': form
    }
    return render(request, 'chat/message_detail.html', context)


@login_required
@transaction.atomic
def start_chat_view(request, user_id):
    """
    ایجاد یک مکالمه جدید با یک کاربر دیگر یا یافتن مکالمه قبلی.
    """
    other_user = get_object_or_404(MyUser, id=user_id)
    
    if other_user == request.user:
        return redirect('chat:chat_list')

    existing_conversation = Conversation.objects.annotate(
        participant_count=Count('participants')
    ).filter(
        participants=request.user, 
        participant_count=2
    ).filter(
        participants=other_user
    ).first()
    
    if existing_conversation:
        return redirect('chat:chat_detail', conversation_id=existing_conversation.id)
    else:
        new_conversation = Conversation.objects.create()
        new_conversation.participants.add(request.user, other_user)
        return redirect('chat:chat_detail', conversation_id=new_conversation.id)


@login_required
def chat_new_view(request):
    """
    (جدید)
    صفحه "شروع مکالمه جدید" - لیستی از کاربران را نمایش می‌دهد.
    """
    # فعلا همه کاربران بجز خود کاربر را لیست می‌کنیم
    # بعداً می‌توان این را بر اساس نقش (دانش‌آموز/معلم) فیلتر کرد
    users_to_chat_with = MyUser.objects.exclude(
        id=request.user.id
    ).select_related('profile').order_by('profile__last_name', 'profile__first_name')

    context = {
        'users_list': users_to_chat_with
    }
    return render(request, 'chat/new_chat_list.html', context)