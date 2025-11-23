from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.validators import MinValueValidator
from persiantools.jdatetime import JalaliDateTime
# خط پکیج جلالی حذف شد

class MyUserManager(BaseUserManager):
    def create_user(self, n_code, phone, password=None):
        """
        یک کاربر معمولی با شماره تلفن، کد ملی و رمز عبور داده شده ایجاد و ذخیره می‌کند.
        """
        if not phone:
            raise ValueError("کاربران باید شماره تلفن داشته باشند")
        if not n_code:
            raise ValueError("کاربران باید کد ملی داشته باشند")

        user = self.model(
            phone=phone,
            n_code=n_code,
        )

        user.set_password(password)
        user.save(using=self._db)
        # ایجاد پروفایل همزمان با ایجاد کاربر
        Profile.objects.get_or_create(user=user) 
        return user

    def create_superuser(self, n_code, phone, password=None):
        """
        یک سوپریوزر (مدیر کل) با شماره تلفن، کد ملی و رمز عبور داده شده ایجاد و ذخیره می‌کند.
        """
        user = self.create_user(
            phone=phone,
            password=password,
            n_code=n_code,
        )
        # دسترسی‌های مدیر کل رو تنظیم می‌کنه
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        # پروفایل سوپریوزر رو می‌گیره (یا می‌سازه) و نقشش رو 'admin' می‌ذاره
        profile, created = Profile.objects.get_or_create(user=user)
        profile.role = 'admin'
        profile.level = '1' # یا هر سطح پیش‌فرض دیگه
        profile.save()

        return user


class MyUser(AbstractBaseUser, PermissionsMixin):
    """
    مدل کاربر سفارشی با لاگین بر اساس شماره تلفن.
    """
    n_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=11, unique=True, verbose_name='شماره تلفن (نام کاربری)')
    
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    is_admin = models.BooleanField(default=False, verbose_name='ادمین (دسترسی کل)')
    is_staff = models.BooleanField(default=False, verbose_name='کارمند (دسترسی به ادمین)')
    
    objects = MyUserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["n_code"]

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.phone

    def get_full_name(self):
        if hasattr(self, 'profile'):
            name = f"{self.profile.first_name} {self.profile.last_name}".strip()
            return name or self.phone
        return self.phone

    def get_short_name(self):
        if hasattr(self, 'profile') and self.profile.first_name:
            return self.profile.first_name
        return self.phone


class Profile(models.Model):
    """
    مدل پروفایل برای نگهداری اطلاعات تکمیلی کاربران.
    """
    ROLE_CHOICES = (
        ('student', 'دانش آموز'),
        ('teacher', 'معلم'),
        ('admin', 'مدیر'),
    )
    STATUS_LEVEL = (
        ('1', 'سطح یک'),
        ('2', 'سطح دو'),
        ('3', 'سطح سه'),
    )
    
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='profile', verbose_name='کاربر')
    first_name = models.CharField(max_length=100, blank=True, verbose_name='نام')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='نام خانوادگی')
    fName = models.CharField(max_length=100, blank=True, verbose_name='نام پدر')
    followName = models.CharField(max_length=100, blank=True, verbose_name='مسئول پیگیری')
    level = models.CharField(max_length=3, choices=STATUS_LEVEL, verbose_name='سطح/کلاس')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student', verbose_name='نقش کاربر')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name else self.user.phone

    class Meta:
        verbose_name = 'پروفایل'
        verbose_name_plural = 'پروفایل‌ها'


# ==========================================================
# 2. مدل حضور و غیاب
# ==========================================================
class presenceAbsence(models.Model):
    STATUS_CHOICES = (
        ('present', 'حاضر'),
        ('absent', 'غایب'),
        ('late', 'تاخیر'),
    )
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, verbose_name='کاربر')
    # FIX: فیلد تاریخ استاندارد جنگو
    publish_date = models.DateField(verbose_name='تاریخ', null=True, blank=True)
    presenceAbsence = models.CharField(max_length=10, choices=STATUS_CHOICES, default='absent', verbose_name='وضعیت')
    # FIX: فیلد زمان استاندارد جنگو
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت', null=True, blank=True)

    def __str__(self):
        return f"{self.user.phone} - {self.publish_date}"

    class Meta:
        verbose_name = 'حضور و غیاب'
        verbose_name_plural = 'حضور و غیاب'


# ==========================================================
# 3. مدل‌های نمرات و دروس
# ==========================================================
class Course(models.Model):
    name = models.CharField(max_length=150, verbose_name='نام درس')
    level = models.CharField(max_length=3, choices=Profile.STATUS_LEVEL, verbose_name='سطح/پایه')
    teacher = models.ForeignKey(MyUser, on_delete=models.CASCADE, verbose_name='معلم مسئول')
    
    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"
    
    class Meta:
        verbose_name = 'درس'
        verbose_name_plural = 'دروس'

class Exam(models.Model):
    EXAM_TYPES = (
        ('Class', 'کلاسی'),
        ('Midterm', 'میان ترم'),
        ('Final', 'پایان ترم'),
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams', verbose_name='درس')
    exam_type = models.CharField(max_length=50, choices=EXAM_TYPES, verbose_name='نوع آزمون')
    max_score = models.IntegerField(default=20, verbose_name='حداکثر نمره')
    # FIX: فیلد تاریخ استاندارد جنگو
    exam_date = models.DateField(verbose_name='تاریخ آزمون', null=True, blank=True)
    
    def __str__(self):
        return f"{self.course.name} - {self.get_exam_type_display()}"
    
    class Meta:
        verbose_name = 'آزمون'
        verbose_name_plural = 'آزمون‌ها'

class Grade(models.Model):
    student = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='grades', verbose_name='دانش آموز')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='grades', verbose_name='آزمون')
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='نمره کسب شده')

    def __str__(self):
        return f"{self.student.phone} - {self.exam.course.name}: {self.score}"
    
    class Meta:
        verbose_name = 'نمره'
        verbose_name_plural = 'نمرات'
        unique_together = ('student', 'exam') # هر دانش آموز برای هر آزمون فقط یک نمره دارد


# ==========================================================
# 4. مدل‌های تکالیف
# ==========================================================
class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments', verbose_name='درس')
    title = models.CharField(max_length=200, verbose_name='عنوان تکلیف')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    file = models.FileField(upload_to='assignments/%Y/%m/%d/', blank=True, null=True, verbose_name='فایل پیوست')
    # FIX: فیلد تاریخ استاندارد جنگو
    due_date = models.DateField(verbose_name='تاریخ سررسید', null=True, blank=True)
    # FIX: فیلد زمان استاندارد جنگو
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد', null=True, blank=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'تکلیف'
        verbose_name_plural = 'تکالیف'
        ordering = ['-due_date']

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions', verbose_name='تکلیف')
    student = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='submitted_assignments', verbose_name='دانش آموز')
    file = models.FileField(upload_to='submissions/%Y/%m/%d/', verbose_name='فایل ارسالی')
    # FIX: فیلد زمان استاندارد جنگو
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ارسال', null=True, blank=True)

    def __str__(self):
        return f"ارسال {self.assignment.title} توسط {self.student.phone}"
    
    class Meta:
        verbose_name = 'ارسال تکلیف'
        verbose_name_plural = 'ارسال‌های تکالیف'
        unique_together = ('assignment', 'student') # هر دانش آموز برای هر تکلیف فقط یک فایل می‌تواند ارسال کند