from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from .models import MyUser, Profile, presenceAbsence, Course, Exam, Grade, Assignment, Submission
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


# ==========================================================
# 1. فرم ورود (Login Form)
# ==========================================================

class UserLoginForm(AuthenticationForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'شماره تماس'
        self.fields['username'].widget.attrs['placeholder'] = 'شماره تماس'
        self.fields['password'].widget.attrs['placeholder'] = 'رمز عبور'

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(username=username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
        return self.cleaned_data


# ==========================================================
# 2. فرم ثبت کاربر (Admin User Creation Form)
# ==========================================================

class AdminUserCreationForm(forms.Form): 
    
    n_code = forms.CharField(label='کد ملی', max_length=10)
    phone = forms.CharField(label='شماره تماس (نام کاربری)', max_length=11)
    password = forms.CharField(label='رمز عبور', widget=forms.PasswordInput)
    password2 = forms.CharField(label='تکرار رمز عبور', widget=forms.PasswordInput)
    
    first_name = forms.CharField(label='نام', max_length=100, required=False)
    last_name = forms.CharField(label='نام خانوادگی', max_length=150, required=False)
    fName = forms.CharField(label='نام پدر', max_length=100, required=False)
    followName = forms.CharField(label='مسئول پیگیری', max_length=100, required=False)
    level = forms.ChoiceField(label='سطح/کلاس', choices=Profile.STATUS_LEVEL)
    
    # (جدید) فیلد انتخاب نقش
    role = forms.ChoiceField(label='نقش کاربر', choices=Profile.ROLE_CHOICES, initial='student')

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if MyUser.objects.filter(phone=phone).exists():
            raise forms.ValidationError("کاربری با این شماره تماس قبلاً ثبت شده است.")
        return phone
        
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password and password2 and password != password2:
            raise forms.ValidationError(
                "رمز عبور و تکرار آن یکسان نیستند."
            )
        return cleaned_data

# ==========================================================
# 3. فرم ویرایش پروفایل (Profile Update Form)
# ==========================================================

class ProfileUpdateForm(forms.ModelForm):
    phone = forms.CharField(label='شماره تماس', max_length=11)
    
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'fName', 'followName', 'level']
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) 
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.initial['phone'] = self.user.phone
            
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if self.user and MyUser.objects.exclude(pk=self.user.pk).filter(phone=phone).exists():
            raise forms.ValidationError("این شماره تماس قبلاً توسط کاربر دیگری ثبت شده است.")
        return phone
        
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if self.user and commit:
            self.user.phone = self.cleaned_data['phone']
            self.user.save()
            
        if commit:
            profile.save()
            
        return profile
    
# ==========================================================
# 4. فرم حضور و غیاب (Attendance Form)
# ==========================================================

class PresenceAbsenceForm(forms.ModelForm):
    
    presenceAbsence = forms.ChoiceField(
        label='وضعیت',
        choices=(
            ('Present', 'حاضر'),
            ('Absent', 'غایب'),
            ('Late', 'تأخیر'),
        ),
        widget=forms.HiddenInput() 
    )
    
    publish_date = forms.CharField(widget=forms.HiddenInput())
    
    class Meta:
        model = presenceAbsence 
        exclude = ['publish_date', 'created_at'] 
        widgets = {
            'user': forms.HiddenInput(),
        }

# ==========================================================
# 5. فرم فیلتر گزارش حضور و غیاب (Attendance Report Filter)
# ==========================================================

class AttendanceReportFilterForm(forms.Form):
    
    date_from = forms.CharField(label='از تاریخ', max_length=10, required=False, 
                                widget=forms.TextInput(attrs={'placeholder': 'مثال: 1403/01/01'}))
    date_to = forms.CharField(label='تا تاریخ', max_length=10, required=False,
                              widget=forms.TextInput(attrs={'placeholder': 'مثال: 1403/01/30'}))
    
    level = forms.ChoiceField(label='سطح/کلاس', choices=[('', 'همه سطوح')] + list(Profile.STATUS_LEVEL), required=False)
    
    status_choices = (
        ('', 'همه وضعیت‌ها'),
        ('Present', 'حاضر'),
        ('Absent', 'غایب'),
        ('Late', 'تأخیر'),
    )
    status = forms.ChoiceField(label='وضعیت', choices=status_choices, required=False)

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
        
# ==========================================================
# 6. فرم‌های مدیریت نمرات
# ==========================================================

# فرم فیلتر برای انتخاب درس و آزمون (برای Grade Entry) - نامش را عوض می‌کنیم
class GradeEntryFilterForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        label='انتخاب درس',
        required=True
    )
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.none(), # کوئری ست آزمون‌ها با AJAX پر می‌شود
        label='انتخاب آزمون',
        required=True
    )

# فرم فیلتر جدید برای گزارش نمرات (ویژه معلم/ادمین)
class GradeReportFilterForm(forms.Form):
    # فیلدهای قبلی را حذف یا کامنت می‌کنیم، فعلا فقط دانش آموز
    # level = forms.ChoiceField(label='سطح/پایه', choices=[('', 'همه سطوح')] + list(Profile.STATUS_LEVEL), required=False)
    student = forms.ModelChoiceField(
        queryset=MyUser.objects.none(), # این کوئری ست در ویو تنظیم می‌شود
        label='انتخاب دانش‌آموز',
        required=False # اجازه می‌دهیم خالی باشد تا همه نمایش داده شوند (بعدا پیاده سازی می‌شود)
    )
    # exam_type = forms.ChoiceField(label='نوع آزمون', choices=[('', 'همه آزمون‌ها')] + list(Exam.EXAM_TYPES), required=False)

    def __init__(self, *args, **kwargs):
        # کوئری ست دانش آموزان را از ویو دریافت می‌کنیم
        students_queryset = kwargs.pop('students_queryset', None)
        super().__init__(*args, **kwargs)
        if students_queryset is not None:
            # نمایش نام و نام خانوادگی در لیست دانش آموزان
            self.fields['student'].queryset = students_queryset
            self.fields['student'].label_from_instance = lambda obj: f"{obj.profile.first_name} {obj.profile.last_name} ({obj.phone})"

    # ==========================================================
class GradeEntryForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'exam', 'score'] # فیلدهایی که در formset نیاز داریم
        widgets = {
            # دانش آموز و آزمون باید از قبل مشخص شده باشند، پس مخفی می‌کنیم
            'student': forms.HiddenInput(),
            'exam': forms.HiddenInput(),
            # استایل بهتر برای فیلد نمره
            'score': forms.NumberInput(attrs={'class': 'score-input', 'min': '0', 'step': '0.25'})
        }
    
# ==========================================================
# 7. فرم‌های مدیریت تکالیف (Assignments)
# ==========================================================

class AssignmentForm(forms.ModelForm):
    # FIX: تعریف صریح due_date به عنوان CharField
    due_date = forms.CharField(
        label='تاریخ سررسید',
        widget=forms.TextInput(attrs={'placeholder': 'مثال: 1404/01/30'})
    )

    class Meta:
        model = Assignment
        # FIX: حذف due_date از fields و استفاده از exclude برای created_at
        fields = ['course', 'title', 'description', 'file']
        
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class SubmissionForm(forms.ModelForm):
    
    class Meta:
        model = Submission
        fields = ['file']