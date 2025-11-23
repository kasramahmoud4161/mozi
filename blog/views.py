from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.forms import modelformset_factory 
from django.db import transaction 
from django.db.models import Q 
from datetime import date
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from .models import (MyUser, Profile, presenceAbsence, Course, Exam, Grade,
                     Assignment, Submission) # مدل‌ها

# FIX: بلوک import فرم‌ها باید فقط یک بار و به شکل صحیح باشد
from .forms import (UserLoginForm, AdminUserCreationForm, ProfileUpdateForm,
                    PresenceAbsenceForm, AttendanceReportFilterForm,
                    
                    GradeEntryForm,         # <-- فرم مدل نمره
                    GradeEntryFilterForm,   # <-- فرم فیلتر صفحه ورود نمره
                    GradeReportFilterForm,  # <-- فرم فیلتر صفحه گزارش نمره
                    AssignmentForm, SubmissionForm)
 
# FIX: استفاده از persiantools.jdatetime برای سازگاری بهتر
from persiantools.jdatetime import JalaliDate as jdatetime_date
from persiantools.jdatetime import JalaliDateTime as jdatetime_datetime
from datetime import date, datetime 


# ==========================================================
# توابع تست دسترسی (Admin Check)
# ==========================================================

# تابع تست دسترسی (Admin Check)
# نام تابع را تغییر می‌دهیم تا شامل معلم هم بشود
def is_teacher_or_admin(user):
    # کاربر باید احراز هویت شده باشد و نقش معلم یا مدیر داشته باشد
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role in ['teacher', 'admin']

# تابع تست فقط برای مدیر کل
def is_superuser(user):
    # استفاده از is_admin جنگو که برای superuser است
    return user.is_authenticated and user.is_admin


# ==========================================================
# 1. صفحات احراز هویت (Login / Register / Logout)
# ==========================================================

def user_login(request):
    if request.user.is_authenticated:
        return redirect('blog:dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            first_name = user.profile.first_name if hasattr(user, "profile") and user.profile.first_name else user.phone
            messages.success(request, f'خوش آمدید، {first_name}!')
            return redirect('blog:dashboard')
        else:
            messages.error(request, 'شماره تماس یا رمز عبور نامعتبر است.')
    else:
        form = UserLoginForm()
        
    return render(request, 'login.html', {'form': form})

# تابع ثبت نام عمومی
@transaction.atomic
def user_register(request):
    if request.user.is_authenticated:
        return redirect('blog:dashboard')
        
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST) 
        
        if form.is_valid():
            user = MyUser.objects.create_user(
                n_code=form.cleaned_data['n_code'],
                phone=form.cleaned_data['phone'],
                password=form.cleaned_data['password']
            ) 
            
            profile = user.profile
            profile.first_name = form.cleaned_data.get('first_name', '')
            profile.last_name = form.cleaned_data.get('last_name', '')
            profile.fName = form.cleaned_data.get('fName', '')
            profile.level = form.cleaned_data['level']
            profile.save()
            
            messages.success(request, 'ثبت نام شما با موفقیت انجام شد. لطفا وارد شوید.')
            return redirect('blog:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'خطا در فیلد {form.fields[field].label}: {error}')
    else:
        form = AdminUserCreationForm()
    
    context = {
        'form': form,
        'title': 'ثبت نام کاربران'
    }
    return render(request, 'register.html', context) 

def user_logout(request):
    logout(request)
    messages.success(request, "شما با موفقیت از سامانه خارج شدید.")
    return redirect('blog:login')


# ==========================================================
# 2. صفحات عمومی بعد از ورود و داشبورد
# ==========================================================

@login_required
def home_modules_view(request):
    return render(request, 'home_modules.html')


@login_required
def dashboard_view(request):
    current_jalali_date = jdatetime_date.today().strftime('%Y/%m/%d')
    
    total_users = MyUser.objects.count()
    
    try:
        today_attendance = presenceAbsence.objects.filter(publish_date=current_jalali_date)
        
        total_present = today_attendance.filter(presenceAbsence='Present').count()
        total_absent = today_attendance.filter(presenceAbsence='Absent').count()
        total_late = today_attendance.filter(presenceAbsence='Late').count()
    except Exception:
        total_present = 0
        total_absent = 0
        total_late = 0
    
    context = {
        'current_jalali_date': current_jalali_date,
        'total_users': total_users,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_late': total_late,
    }
    return render(request, 'dashboard.html', context)


# ==========================================================
# 3. مدیریت پروفایل
# ==========================================================

@login_required
def profile_view(request):
    return render(request, 'profile.html')

@login_required
@transaction.atomic 
def profile_update_view(request):
    
    profile = request.user.profile
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save() 
            messages.success(request, 'اطلاعات پروفایل با موفقیت به‌روزرسانی شد.')
            return redirect('blog:profile_update')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label
                    messages.error(request, f'خطا در فیلد {label}: {error}')
    else:
        form = ProfileUpdateForm(instance=profile, user=request.user)
        
    return render(request, 'update_profile.html', {'form': form})


# ==========================================================
# 4. ماژول حضور و غیاب
# ==========================================================
@login_required
@user_passes_test(is_teacher_or_admin) # <-- تغییر کرد
def attendance_manage_view(request):
    
    selected_level = request.GET.get('class_level', '1') 
    selected_date_str = request.GET.get('attendance_date') # این تاریخ از URL می‌آید
    
    # --- (اصلاح ۱: تعریف تاریخ فیلتر) ---
    # ما به یک متغیر واحد برای تاریخی که می‌خواهیم فیلتر کنیم نیاز داریم
    # که هم در GET و هم در POST قابل دسترس باشد.
    
    filter_date = None
    
    if selected_date_str:
        try:
            # تاریخ رشته‌ای (مثلا 2025-10-31) را به آبجکت date تبدیل می‌کنیم
            filter_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "فرمت تاریخ وارد شده در URL نامعتبر است.")
            filter_date = date.today() # اگر فرمت بد بود، به امروز برمی‌گردیم
    else:
        # اگر هیچ تاریخی در URL نبود، تاریخ امروز را در نظر می‌گیریم
        filter_date = date.today()

    
    users_in_level = MyUser.objects.filter(profile__level=selected_level).order_by('profile__last_name')
    
    AttendanceFormSet = modelformset_factory(presenceAbsence, form=PresenceAbsenceForm, extra=0)
    
    initial_data = []
    
    for user in users_in_level:
        try:
            # --- (اصلاح ۲: استفاده از filter_date) ---
            # به جای today_date از filter_date استفاده می‌کنیم
            
            # --- (اصلاح ۳: استفاده از user) ---
            # به جای 'student' (که تعریف نشده) از 'user' (متغیر حلقه) استفاده می‌کنیم
            attendance_record = presenceAbsence.objects.get(
                publish_date=filter_date, 
                user=user 
            )
            initial_data.append(attendance_record)
        except presenceAbsence.DoesNotExist:
            initial_data.append({
                'user': user,
                'publish_date': filter_date,
                'presenceAbsence': 'Absent' 
            })
            
    if request.method == 'POST':
        formset = AttendanceFormSet(request.POST, queryset=presenceAbsence.objects.none())
        
        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    if form.has_changed():
                        instance = form.save(commit=False)
                        
                        if instance.pk is None: 
                            instance.user = MyUser.objects.get(pk=form.cleaned_data['user'])
                            instance.publish_date = form.cleaned_data['publish_date']
                            # FIX: چون مدل‌ها استاندارد هستند، از زمان استاندارد استفاده می‌کنیم
                            instance.created_at = datetime.now() 
                            
                        instance.save()
            
            # تاریخ را برای URL آماده می‌کنیم
            filter_date_str = filter_date.strftime('%Y-%m-%d')
            messages.success(request, f'وضعیت حضور و غیاب برای تاریخ {filter_date_str} با موفقیت به‌روزرسانی شد.')
            # FIX: ریدایرکت به URL به همراه پارامترها
            return redirect(f'/attendance/manage/?class_level={selected_level}&attendance_date={filter_date_str}')
        else:
            messages.error(request, 'خطا در اعتبارسنجی داده‌ها. لطفاً فرم را بررسی کنید.')
            
    else: # (درخواست GET)
        if initial_data and isinstance(initial_data[0], presenceAbsence):
            formset = AttendanceFormSet(queryset=presenceAbsence.objects.filter(id__in=[i.id for i in initial_data]))
        else:
             formset = AttendanceFormSet(initial=[i for i in initial_data if isinstance(i, dict)])

    context = {
        'formset': formset,
        'selected_level': selected_level,
        'filter_date': filter_date, # آبجکت date را به قالب می‌فرستیم
        'STATUS_LEVELS': Profile.STATUS_LEVEL 
    }
    return render(request, 'attendance.html', context)

@login_required
def attendance_report_view(request):
    
    report_data = presenceAbsence.objects.all().select_related('user__profile')
    
    if request.GET:
        form = AttendanceReportFilterForm(request.GET)
        if form.is_valid():
            data = form.cleaned_data
            
            if data['status']:
                report_data = report_data.filter(presenceAbsence=data['status'])

            if data['level']:
                report_data = report_data.filter(user__profile__level=data['level']) 
            
            if data['date_from']:
                report_data = report_data.filter(publish_date__gte=data['date_from'])
            
            if data['date_to']:
                report_data = report_data.filter(publish_date__lte=data['date_to'])
            
            report_data = report_data.order_by('-publish_date', '-created_at')
            
        else:
            messages.error(request, "خطا در فیلترهای جستجو.")
    else:
        form = AttendanceReportFilterForm()
        report_data = report_data.order_by('-publish_date', '-created_at')[:50]

    context = {
        'form': form,
        'report_data': report_data,
        'STATUS_LEVELS': Profile.STATUS_LEVEL, 
    }
    return render(request, 'attendance_report.html', context)


# ==========================================================
# 5. مدیریت کاربران (انحصاری مدیر)
# ==========================================================
# /home/kasra/Desktop/mozi/blog/views.py

@login_required
@user_passes_test(is_superuser) # <-- تغییر کرد به تابع جدید
@transaction.atomic
def admin_user_create_view(request):
    
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        
        if form.is_valid():
            user = MyUser.objects.create_user(
                n_code=form.cleaned_data['n_code'],
                phone=form.cleaned_data['phone'],
                password=form.cleaned_data['password']
            ) 
            
            profile = user.profile
            profile.first_name = form.cleaned_data.get('first_name')
            profile.last_name = form.cleaned_data.get('last_name')
            profile.fName = form.cleaned_data.get('fName')
            profile.level = form.cleaned_data['level']
            profile.followName = form.cleaned_data.get('followName')
            profile.role = form.cleaned_data['role']
            profile.save()
            
            if profile.role in ['teacher', 'admin']:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            
            messages.success(request, f'کاربر جدید ({profile.first_name} {profile.last_name}) با نقش {profile.get_role_display()} با موفقیت ثبت شد.')
            return redirect('blog:admin_user_create')
        
        else:
            # --- (اصلاح) ---
            # این حلقه حذف شد چون قالب جدید (admin_user_create_form.html)
            # خودش خطاها را زیر هر فیلد نشان می‌دهد و این حلقه باعث تکرار خطاها می‌شد.
            messages.error(request, 'خطا در اعتبارسنجی داده‌ها. لطفاً موارد قرمز رنگ را بررسی کنید.')
            # --- (پایان اصلاح) ---
            
    else:
        form = AdminUserCreationForm()
    
    context = {
        'levels': Profile.STATUS_LEVEL, 
        'roles': Profile.ROLE_CHOICES, 
        'form': form
    }
    return render(request, 'admin_user_create_form.html', context)
# ==========================================================
# 6. ماژول نمرات و AJAX
# ==========================================================
@login_required
@user_passes_test(is_teacher_or_admin) # <-- اضافه شد
def grade_entry_view(request):
    # ... بقیه کد ...
    # (حذف شرط if not (request.user.is_admin or request.user.is_staff):)

    # (تغییر کوئری دروس بر اساس نقش)
    if request.user.profile.role == 'admin': # اگر مدیر کل بود
        course_queryset = Course.objects.all()
    elif request.user.profile.role == 'teacher': # اگر معلم بود
        course_queryset = Course.objects.filter(teacher=request.user)
    else: # اگر دانش‌آموز بود (که نباید به اینجا برسد ولی محض احتیاط)
        course_queryset = Course.objects.none()
        messages.error(request, "شما اجازه دسترسی به این بخش را ندارید.")
        return redirect('blog:dashboard')

    # ... بقیه کد ...
    
    if request.user.is_admin:
        course_queryset = Course.objects.all()
    else:
        course_queryset = Course.objects.filter(teacher=request.user) 

    GradeFormSet = modelformset_factory(Grade, form=GradeEntryForm, extra=0)
    
    context = {
        'formset': None,
        'selected_course': None,
        'selected_exam': None,
        'max_score': None
    }
    
    filter_form = GradeEntryFilterForm(request.GET or None) # <-- خط اصلاح شده
    filter_form.fields['course'].queryset = course_queryset

    if 'course' in request.GET and request.GET['course']:
        try:
            course_id = request.GET['course']
            filter_form.fields['exam'].queryset = Exam.objects.filter(course_id=course_id)
        except:
            filter_form.fields['exam'].queryset = Exam.objects.none()
            
            
    if filter_form.is_valid():
        course = filter_form.cleaned_data['course']
        exam = filter_form.cleaned_data['exam']
        
        if exam.course != course:
            messages.error(request, "آزمون انتخاب شده متعلق به درس انتخاب شده نیست.")
            return redirect('blog:grade_entry')
        
        student_level = course.level
        student_queryset = MyUser.objects.filter(profile__level=student_level).order_by('profile__last_name')
        
        existing_grades = Grade.objects.filter(student__in=student_queryset, exam=exam)
        
        if request.method == 'POST':
            formset = GradeFormSet(request.POST, queryset=existing_grades)

            if formset.is_valid():
                instances = formset.save(commit=False)
                
                for instance in instances:
                    instance.save() 
                        
                for form in formset.deleted_forms:
                    form.instance.delete()

                messages.success(request, f'نمرات درس {course.name} برای آزمون {exam.get_exam_type_display()} با موفقیت ثبت شد.')
                return redirect('blog:grade_entry')
            else:
                messages.error(request, 'خطا در اعتبارسنجی داده‌ها. لطفاً نمرات را بررسی کنید.')
        
        else:
            students_with_grades = [g.student.id for g in existing_grades]
            students_without_grades = student_queryset.exclude(id__in=students_with_grades)
            
            initial_for_new_grades = [{
                'student': student,
                'exam': exam,
                'score': None
            } for student in students_without_grades]
            
            formset = GradeFormSet(queryset=existing_grades, initial=initial_for_new_grades)


        context.update({
            'formset': formset,
            'selected_course': course,
            'selected_exam': exam,
            'max_score': exam.max_score
        })
        
    return render(request, 'grade_entry.html', context)
    
@login_required
def grade_report_view(request):
    """
    نمایش گزارش نمرات.
    - دانش‌آموز: کارنامه خودش را می‌بیند.
    - معلم: می‌تواند دانش‌آموزان کلاس‌های خودش را فیلتر کند.
    - مدیر: می‌تواند همه دانش‌آموزان و کلاس‌ها را فیلتر کند.
    """
    context = {
        'form': None,
        'student_data': None,
        'students_grades': None,
        'title': 'گزارش نمرات'
    }
    user = request.user
    # استفاده از getattr برای جلوگیری از خطا اگر پروفایل وجود نداشته باشد
    profile = getattr(user, 'profile', None)

    if not profile:
        messages.error(request, "پروفایل کاربری شما یافت نشد. لطفاً با پشتیبانی تماس بگیرید.")
        return redirect('blog:dashboard') # یا هر صفحه‌ای که برای داشبورد اصلی دارید

    if profile.role == 'student':
        # --- منطق برای دانش‌آموز ---
        student_grades = Grade.objects.filter(student=user).select_related(
            'exam__course', 'student__profile'
        ).order_by('exam__course__name') # FIX: مرتب‌سازی بر اساس نام درس (exam_date حذف شد)

        # محاسبه معدل (ساده)
        total_score = sum(g.score for g in student_grades if g.score is not None)
        count = student_grades.count()
        average = total_score / count if count > 0 else None

        context['students_grades'] = student_grades
        context['student_data'] = {
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'level_display': profile.get_level_display(),
            'n_code': user.n_code,
            'average': f"{average:.2f}" if average is not None else "N/A"
        }
        context['title'] = 'کارنامه تحصیلی'

    elif profile.role in ['teacher', 'admin']:
        # --- منطق برای معلم یا مدیر ---
        
        # تعیین لیست دانش‌آموزانی که قابل فیلتر هستند
        students_queryset = MyUser.objects.none()
        if profile.role == 'admin':
             students_queryset = MyUser.objects.filter(profile__role='student').order_by('profile__last_name')
        elif profile.role == 'teacher':
             # معلم فقط دانش آموزان کلاس‌هایی که درس می‌دهد را ببیند
             teacher_courses = Course.objects.filter(teacher=user)
             student_levels = teacher_courses.values_list('level', flat=True).distinct()
             students_queryset = MyUser.objects.filter(profile__level__in=student_levels, profile__role='student').order_by('profile__last_name')

        # FIX: استفاده از نام صحیح فرم (GradeReportFilterForm)
        filter_form = GradeReportFilterForm(request.GET or None, students_queryset=students_queryset)
        context['form'] = filter_form

        if filter_form.is_valid():
            selected_student = filter_form.cleaned_data.get('student')
            if selected_student:
                # اگر دانش‌آموزی انتخاب شده بود، گزارش او را نمایش بده
                student_grades = Grade.objects.filter(student=selected_student).select_related(
                    'exam__course', 'student__profile'
                ).order_by('exam__course__name') # FIX: مرتب‌سازی بر اساس نام درس

                total_score = sum(g.score for g in student_grades if g.score is not None)
                count = student_grades.count()
                average = total_score / count if count > 0 else None
                
                selected_profile = getattr(selected_student, 'profile', None)
                if selected_profile:
                    context['student_data'] = {
                        'first_name': selected_profile.first_name,
                        'last_name': selected_profile.last_name,
                        'level_display': selected_profile.get_level_display(),
                        'n_code': selected_student.n_code,
                        'average': f"{average:.2f}" if average is not None else "N/A"
                    }
                context['students_grades'] = student_grades
                context['title'] = f'کارنامه {selected_profile.first_name or ""} {selected_profile.last_name or ""}'
            # else:
                # (می‌توانید منطقی برای زمانی که معلم دانش‌آموزی انتخاب نکرده اضافه کنید)
                # pass 
    else:
        # اگر نقش کاربر نه دانش‌آموز بود، نه معلم و نه مدیر
        messages.warning(request, "نقش کاربری شما برای دسترسی به این بخش تعریف نشده است.")
        return redirect('blog:dashboard') # یا صفحه اصلی

    return render(request, 'grade_report.html', context)    
@login_required
@user_passes_test(is_teacher_or_admin) # <-- باید از تابع بررسی دسترسی به‌روز شده استفاده کند
def load_exams_ajax(request):
    course_id = request.GET.get('course_id')

    # (کنترل دسترسی معلم به درس‌های خودش)
    # FIX: تورفتگی صحیح برای این بلاک
    if hasattr(request.user, 'profile'): # اول بررسی کنید پروفایل وجود دارد
        if request.user.profile.role == 'teacher':
             if not Course.objects.filter(id=course_id, teacher=request.user).exists():
                 return JsonResponse({'error': 'درس پیدا نشد یا اجازه دسترسی ندارید'}, status=403)
        elif request.user.profile.role != 'admin': # اگر نه معلم بود نه مدیر
             return JsonResponse({'error': 'اجازه دسترسی ندارید'}, status=403)
    else: # اگر کاربر پروفایل نداشت (برای کاربران لاگین شده نباید اتفاق بیفتد)
        return JsonResponse({'error': 'پروفایل پیدا نشد'}, status=403)

    # دریافت آزمون‌ها در صورت داشتن دسترسی
    try:
        exams = Exam.objects.filter(course_id=course_id).order_by('exam_date')
        data = [{'id': exam.id, 'name': f'{exam.get_exam_type_display()} ({exam.exam_date})'} for exam in exams]
        return JsonResponse(data, safe=False)
    except Course.DoesNotExist: # مدیریت حالتی که course_id نامعتبر است
        return JsonResponse({'error': 'شناسه درس نامعتبر است'}, status=404)
    except Exception as e: # مدیریت خطاهای عمومی
        # می‌توانید خطا را لاگ کنید: print(e) یا logging.error(e)
        return JsonResponse({'error': 'یک خطای غیرمنتظره رخ داد'}, status=500)
    
@login_required
def global_search_view(request):
    query = request.GET.get('q')
    results = {
        'users': [],
        'courses': [],
        'grades': []
    }
    
    if query:
        # جستجو در کاربران (بر اساس نام، نام خانوادگی یا کد ملی)
        user_results = MyUser.objects.filter(
            Q(n_code__icontains=query) | Q(phone__icontains=query) | 
            Q(profile__first_name__icontains=query) | Q(profile__last_name__icontains=query)
        ).distinct().select_related('profile')
        results['users'] = user_results[:10] # محدود کردن نتایج

        # جستجو در دروس
        course_results = Course.objects.filter(name__icontains=query).distinct()
        results['courses'] = course_results[:5]

        # در اینجا می‌توانید جستجوهای پیچیده‌تری را برای نمرات (بر اساس نمره یا آزمون) اضافه کنید.
        # برای سادگی، فعلاً فقط کاربران و دروس را نمایش می‌دهیم.

    context = {
        'query': query,
        'results': results,
        'title': f'نتایج جستجو برای "{query}"' if query else 'جستجوی سراسری'
    }
    return render(request, 'search_results.html', context)
# ==========================================================
# 7. ماژول تکالیف (جدید)
# ==========================================================

@login_required
def assignment_list_view(request):
    assignments_query = Assignment.objects.none()

    # (تغییر شرط به role)
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'admin':
            # مدیر کل: همه تکالیف را ببیند (یا تکالیف مربوط به دروسی که خودش تعریف کرده؟ - فعلا همه)
            assignments_query = Assignment.objects.all().select_related('course', 'course__teacher__profile').order_by('-due_date')
        elif request.user.profile.role == 'teacher':
            # معلم: تکالیف دروسی که خودش تدریس می‌کند
            assignments_query = Assignment.objects.filter(
                course__teacher=request.user
            ).select_related('course', 'course__teacher__profile').order_by('-due_date')
        else: # دانش‌آموز
            assignments_query = Assignment.objects.filter(
                course__level=request.user.profile.level
            ).select_related('course', 'course__teacher__profile').order_by('-due_date')
            
    # TODO: می‌توان لیست تکالیف ارسال شده (submitted) را هم به قالب فرستاد
    # تا دکمه "ارسال تکلیف" برای آنها غیرفعال شود.
            
    context = {
        'assignments': assignments_query,
        'title': 'لیست تکالیف'
    }
    return render(request, 'assignment_list.html', context)

@login_required
@user_passes_test(is_teacher_or_admin) # <-- FIX: استفاده از نام تابع جدید
@transaction.atomic
def assignment_create_view(request):
    """
    ویوی ایجاد تکلیف جدید توسط معلم/مدیر.
    """
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        # محدود کردن انتخاب درس به دروسی که این معلم تدریس می‌کند
        form.fields['course'].queryset = Course.objects.filter(teacher=request.user)
        
        if form.is_valid():
            try:
                assignment = form.save(commit=False)
                
                # فرم due_date را به عنوان رشته (CharField) برمی‌گرداند
                # ما باید آن را به شی JalaliDate تبدیل کنیم
                assignment.due_date = jdatetime_date.strptime(
                    form.cleaned_data['due_date'], '%Y/%m/%d'
                )
                
                # فیلدهای خودکار مدل را تنظیم می‌کنیم
                assignment.created_at = jdatetime_datetime.now()
                assignment.save()
                
                messages.success(request, 'تکلیف جدید با موفقیت ایجاد شد.')
                return redirect('blog:assignment_list')
                
            except ValueError:
                messages.error(request, 'فرمت تاریخ سررسید نامعتبر است. (مثال: 1404/01/30)')
            except Exception as e:
                messages.error(request, f'خطای سیستمی: {e}')
    else:
        form = AssignmentForm()
        # محدود کردن انتخاب درس به دروسی که این معلم تدریس می‌کند
        form.fields['course'].queryset = Course.objects.filter(teacher=request.user)

    context = {
        'form': form,
        'title': 'ایجاد تکلیف جدید'
    }
    return render(request, 'assignment_create.html', context)  
@login_required
@transaction.atomic
def submission_create_view(request, assignment_id):
    # (تغییر شرط به role)
    if hasattr(request.user, 'profile') and request.user.profile.role != 'student':
        messages.error(request, 'فقط دانش‌آموزان مجاز به ارسال تکلیف هستند.')
        return redirect('blog:assignment_list')
    
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # بررسی اینکه آیا دانش‌آموز قبلاً این تکلیف را ارسال کرده است یا خیر
    existing_submission = Submission.objects.filter(
        assignment=assignment, 
        student=request.user
    ).first()
    
    if existing_submission:
        messages.warning(request, f'شما قبلاً تکلیف "{assignment.title}" را ارسال کرده‌اید.')
        return redirect('blog:assignment_list')

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.submitted_at = jdatetime_datetime.now()
            submission.save()
            
            messages.success(request, f'تکلیف "{assignment.title}" با موفقیت ارسال شد.')
            return redirect('blog:assignment_list')
    else:
        form = SubmissionForm()
    
    context = {
        'form': form,
        'assignment': assignment,
        'title': f'ارسال تکلیف: {assignment.title}'
    }
    return render(request, 'submission_create.html', context)