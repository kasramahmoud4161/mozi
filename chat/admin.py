# mozi/chat/admin.py

from django.contrib import admin
from .models import Conversation, Message
from jalali_date.admin import ModelAdminJalaliMixin # برای نمایش بهتر تاریخ جلالی

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    # نمایش فیلدهای مهم و زمان به صورت جلالی (اگر متد مدل درست باشد)
    fields = ('sender', 'content', 'get_jalali_timestamp', 'is_read')
    readonly_fields = ('sender', 'content', 'get_jalali_timestamp', 'is_read')
    can_delete = False

    @admin.display(description='زمان ارسال')
    def get_jalali_timestamp(self, obj):
        # اطمینان از وجود متد قبل از فراخوانی
        if hasattr(obj, 'get_jalali_timestamp'):
            return obj.get_jalali_timestamp()
        return obj.timestamp # بازگشت به حالت پیش‌فرض اگر متد نبود

@admin.register(Conversation)
class ConversationAdmin(ModelAdminJalaliMixin, admin.ModelAdmin): # Mixin اضافه شد
    list_display = ('id', 'get_participants_display', 'get_jalali_created_at', 'get_jalali_updated_at') # نمایش جلالی
    search_fields = ('participants__phone', 'participants__profile__last_name')
    filter_horizontal = ('participants',)
    inlines = [MessageInline]
    # نمایش تاریخ ایجاد و آپدیت به صورت فقط خواندنی
    readonly_fields = ('get_jalali_created_at', 'get_jalali_updated_at')

    @admin.display(description='شرکت‌کنندگان')
    def get_participants_display(self, obj):
        # نمایش نام به جای شماره تلفن
        participants = []
        for user in obj.participants.all():
            if hasattr(user, 'profile'):
                 name = f"{user.profile.first_name} {user.profile.last_name}".strip()
                 participants.append(name or user.phone)
            else:
                 participants.append(user.phone)
        return ", ".join(participants)

    @admin.display(description='ایجاد شده در')
    def get_jalali_created_at(self, obj):
        if hasattr(obj, 'created_at') and obj.created_at:
             try:
                 # استفاده از متد مدل اگر وجود داشته باشد (فرض می‌کنیم از persiantools استفاده شده)
                 from persiantools.jdatetime import JalaliDateTime
                 return JalaliDateTime(obj.created_at).strftime('%Y/%m/%d - %H:%M')
             except ImportError:
                 return obj.created_at # بازگشت به حالت پیش‌فرض
        return '-'

    @admin.display(description='آخرین به‌روزرسانی')
    def get_jalali_updated_at(self, obj):
        if hasattr(obj, 'updated_at') and obj.updated_at:
             try:
                 from persiantools.jdatetime import JalaliDateTime
                 return JalaliDateTime(obj.updated_at).strftime('%Y/%m/%d - %H:%M')
             except ImportError:
                 return obj.updated_at
        return '-'


@admin.register(Message)
class MessageAdmin(ModelAdminJalaliMixin, admin.ModelAdmin): # Mixin اضافه شد
    list_display = ('get_sender_name', 'conversation_id', 'content_snippet', 'get_jalali_timestamp_display', 'is_read') # نام و تاریخ جلالی
    list_filter = ('is_read', ('timestamp', admin.DateFieldListFilter)) # فیلتر جلالی
    search_fields = ('sender__phone', 'sender__profile__last_name', 'content')
    list_select_related = ('sender__profile', 'conversation') # بهینه‌سازی کوئری
    autocomplete_fields = ('sender', 'conversation') # جستجوی بهتر

    @admin.display(description='فرستنده')
    def get_sender_name(self, obj):
        if hasattr(obj.sender, 'profile'):
            name = f"{obj.sender.profile.first_name} {obj.sender.profile.last_name}".strip()
            return name or obj.sender.phone
        return obj.sender.phone

    @admin.display(description='خلاصه پیام')
    def content_snippet(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    @admin.display(description='زمان ارسال')
    def get_jalali_timestamp_display(self, obj):
        # اطمینان از وجود متد قبل از فراخوانی
        if hasattr(obj, 'get_jalali_timestamp'):
            return obj.get_jalali_timestamp()
        return obj.timestamp