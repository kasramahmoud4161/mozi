# mozi/blog/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    MyUser,
    Profile,
    presenceAbsence,
    Course,
    Exam,
    Grade,
    Assignment,
    Submission
)

# Import فیلترهای تاریخ جلالی برای ادمین
from jalali_date.admin import ModelAdminJalaliMixin, StackedInlineJalaliMixin # TabularInlineJalaliMixin
# Import کلاس‌های فیلتر تاریخ
from jalali_date.fields import JalaliDateField, JalaliDateTimeField
from jalali_date.widgets import AdminJalaliDateWidget, AdminSplitJalaliDateTime

# ==========================================================
# 1. Custom User Admin (MyUser and Profile)
# ==========================================================

class ProfileInline(StackedInlineJalaliMixin, admin.StackedInline): # یا TabularInlineJalaliMixin
    model = Profile
    can_delete = False
    verbose_name_plural = 'اطلاعات پروفایل'
    fk_name = 'user'
    fields = ('first_name', 'last_name', 'fName', 'level', 'role', 'followName')
    readonly_fields = ('role',)

class MyUserAdmin(ModelAdminJalaliMixin, BaseUserAdmin):
    list_display = ('phone', 'get_full_name', 'get_level', 'get_role', 'is_active', 'is_staff', 'is_admin') # is_staff اضافه شد
    list_filter = ('profile__role', 'profile__level', 'is_admin', 'is_active', 'is_staff') # is_staff اضافه شد
    fieldsets = (
        (None, {'fields': ('phone', 'n_code', 'password')}),
        ('اطلاعات کاربر', {'fields': ('get_full_name_display', 'get_level_display', 'get_role_display')}),
        ('اطلاعات دسترسی', {'fields': ('is_active', 'is_staff', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}), # فیلدهای دسترسی کامل اضافه شد
        ('اطلاعات ورود', {'fields': ('last_login',)}),
    )
    search_fields = ('phone', 'n_code', 'profile__first_name', 'profile__last_name')
    ordering = ('profile__last_name', 'profile__first_name')
    filter_horizontal = ('groups', 'user_permissions',) # برای فیلدهای ManyToMany دسترسی‌ها
    inlines = (ProfileInline,)
    readonly_fields = ('get_full_name_display', 'get_level_display', 'get_role_display', 'last_login')

    @admin.display(description='نام کامل')
    def get_full_name(self, obj):
         if hasattr(obj, 'profile'):
            return f"{obj.profile.first_name} {obj.profile.last_name}".strip() or obj.phone # اگه اسم خالی بود، شماره رو نشون بده
         return obj.phone
    @admin.display(description='سطح/کلاس')
    def get_level(self, obj):
         if hasattr(obj, 'profile'):
             return obj.profile.get_level_display()
         return '-'
    @admin.display(description='نقش')
    def get_role(self, obj):
         if hasattr(obj, 'profile'):
             return obj.profile.get_role_display()
         return '-'
    @admin.display(description='نام کامل')
    def get_full_name_display(self, obj):
         return self.get_full_name(obj)
    @admin.display(description='سطح/کلاس')
    def get_level_display(self, obj):
         return self.get_level(obj)
    @admin.display(description='نقش')
    def get_role_display(self, obj):
         return self.get_role(obj)

    # get_form رو فعلا ساده نگه می‌داریم تا مطمئن شیم کار می‌کنه
    # def get_form(self, request, obj=None, **kwargs):
    #     form = super().get_form(request, obj, **kwargs)
    #     is_superuser = request.user.is_superuser
    #     if not is_superuser:
    #          if 'is_admin' in form.base_fields:
    #              form.base_fields['is_admin'].disabled = True
    #              form.base_fields['is_admin'].help_text = "فقط مدیر کل می‌تواند این وضعیت را تغییر دهد."
    #     return form

admin.site.register(MyUser, MyUserAdmin)

# ==========================================================
# 2. ثبت مدل‌های مدیریت‌شده
# ==========================================================

@admin.register(presenceAbsence)
class PresenceAbsenceAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('get_user_name', 'publish_date', 'presenceAbsence', 'created_at')
    list_filter = ('presenceAbsence', ('publish_date', admin.DateFieldListFilter), 'user__profile__level')
    search_fields = ('user__phone', 'user__profile__first_name', 'user__profile__last_name')
    formfield_overrides = {
        JalaliDateField: {'widget': AdminJalaliDateWidget},
        JalaliDateTimeField: {'widget': AdminSplitJalaliDateTime},
    }

    @admin.display(description='نام کاربر')
    def get_user_name(self, obj):
         if hasattr(obj.user, 'profile'):
             name = f"{obj.user.profile.first_name} {obj.user.profile.last_name}".strip()
             return name or obj.user.phone
         return obj.user.phone

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return qs
        elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            teacher_courses = Course.objects.filter(teacher=request.user)
            student_levels = teacher_courses.values_list('level', flat=True).distinct()
            return qs.filter(user__profile__level__in=student_levels)
        return qs.none()

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'get_teacher_name')
    list_filter = ('level', 'teacher__profile__last_name') # فیلتر بر اساس نام خانوادگی معلم
    search_fields = ('name', 'teacher__profile__last_name', 'teacher__profile__first_name')

    @admin.display(description='معلم')
    def get_teacher_name(self, obj):
        if hasattr(obj.teacher, 'profile'):
            name = f"{obj.teacher.profile.first_name} {obj.teacher.profile.last_name}".strip()
            return name or obj.teacher.phone
        return obj.teacher.phone

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return qs
        elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            return qs.filter(teacher=request.user)
        return qs.none()

    # محدود کردن انتخاب معلم در فرم ادمین
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "teacher":
            # نمایش معلم‌ها بر اساس نام خانوادگی
            kwargs["queryset"] = MyUser.objects.filter(profile__role='teacher').order_by('profile__last_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Exam)
class ExamAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('get_course_name_level', 'exam_type', 'max_score', 'exam_date')
    list_filter = ('exam_type', 'course__level', 'course__teacher__profile__last_name', ('exam_date', admin.DateFieldListFilter))
    search_fields = ('course__name',)
    formfield_overrides = { JalaliDateField: {'widget': AdminJalaliDateWidget}, }
    # نمایش بهتر انتخاب درس در فرم
    raw_id_fields = ('course',) # یا autocomplete_fields اگر Django >= 2.0

    @admin.display(description='درس (سطح)')
    def get_course_name_level(self, obj):
        return f"{obj.course.name} ({obj.course.get_level_display()})"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return qs
        elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            return qs.filter(course__teacher=request.user)
        return qs.none()

    # محدود کردن انتخاب درس در فرم ادمین
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "course":
            if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
                kwargs["queryset"] = Course.objects.all().order_by('name')
            elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
                 kwargs["queryset"] = Course.objects.filter(teacher=request.user).order_by('name')
            else:
                 kwargs["queryset"] = Course.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('get_student_name', 'get_exam_info', 'score')
    list_filter = ('exam__course__level', 'exam__exam_type', 'exam__course__teacher__profile__last_name')
    search_fields = ('student__phone', 'student__profile__last_name', 'student__profile__first_name', 'exam__course__name')
    #raw_id_fields = ('student', 'exam',) # استفاده از autocomplete بهتر است
    autocomplete_fields = ('student', 'exam',) # جستجوی بهتر برای دانش آموز و آزمون

    @admin.display(description='دانش آموز')
    def get_student_name(self, obj):
         if hasattr(obj.student, 'profile'):
            name = f"{obj.student.profile.first_name} {obj.student.profile.last_name}".strip()
            return name or obj.student.phone
         return obj.student.phone
    @admin.display(description='آزمون')
    def get_exam_info(self, obj):
        # اضافه کردن تاریخ برای خوانایی بیشتر
        date_str = obj.exam.exam_date.strftime('%y/%m/%d') if obj.exam.exam_date else ''
        return f"{obj.exam.course.name} - {obj.exam.get_exam_type_display()} ({date_str})"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return qs
        elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            return qs.filter(exam__course__teacher=request.user)
        return qs.none()

    # (اختیاری) محدود کردن انتخاب دانش آموز و آزمون در فرم ادمین
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "student":
            # نمایش دانش آموزان بر اساس نام خانوادگی
            kwargs["queryset"] = MyUser.objects.filter(profile__role='student').order_by('profile__last_name')
        elif db_field.name == "exam":
            # فیلتر کردن آزمون‌ها بر اساس معلم (اگر کاربر معلم است)
             if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
                  kwargs["queryset"] = Exam.objects.filter(course__teacher=request.user).select_related('course').order_by('course__name', '-exam_date')
             else:
                  kwargs["queryset"] = Exam.objects.select_related('course').order_by('course__name', '-exam_date')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ==========================================================
# 3. ثبت مدل‌های تکالیف
# ==========================================================

@admin.register(Assignment)
class AssignmentAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('title', 'get_course_name_level', 'due_date', 'file', 'created_at')
    list_filter = ('course__level', 'course__teacher__profile__last_name', ('due_date', admin.DateFieldListFilter))
    search_fields = ('title', 'course__name')
    formfield_overrides = {
        JalaliDateField: {'widget': AdminJalaliDateWidget},
        JalaliDateTimeField: {'widget': AdminSplitJalaliDateTime},
    }
    raw_id_fields = ('course',)

    @admin.display(description='درس (سطح)')
    def get_course_name_level(self, obj):
         return f"{obj.course.name} ({obj.course.get_level_display()})"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return qs
        elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            return qs.filter(course__teacher=request.user)
        return qs.none()

    # محدود کردن انتخاب درس در فرم ادمین
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "course":
            if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
                kwargs["queryset"] = Course.objects.all().order_by('name')
            elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
                 kwargs["queryset"] = Course.objects.filter(teacher=request.user).order_by('name')
            else:
                 kwargs["queryset"] = Course.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Submission)
class SubmissionAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    list_display = ('get_assignment_title', 'get_student_name', 'submitted_at', 'file')
    list_filter = ('assignment__course__level', ('submitted_at', admin.DateFieldListFilter))
    search_fields = ('student__phone', 'student__profile__last_name', 'assignment__title')
    #raw_id_fields = ('student', 'assignment',)
    autocomplete_fields = ('student', 'assignment',)
    formfield_overrides = { JalaliDateTimeField: {'widget': AdminSplitJalaliDateTime}, }

    @admin.display(description='تکلیف')
    def get_assignment_title(self, obj):
         return obj.assignment.title
    @admin.display(description='دانش آموز')
    def get_student_name(self, obj):
          if hasattr(obj.student, 'profile'):
             name = f"{obj.student.profile.first_name} {obj.student.profile.last_name}".strip()
             return name or obj.student.phone
          return obj.student.phone

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'admin'):
            return qs
        elif hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            return qs.filter(assignment__course__teacher=request.user)
        return qs.none()