from django.db import models
from blog.models import MyUser  # وارد کردن مدل کاربر سفارشی
from persiantools.jdatetime import JalaliDateTime

class Conversation(models.Model):
    """
    مدلی برای نگهداری یک مکالمه بین دو یا چند کاربر.
    """
    participants = models.ManyToManyField(
        MyUser, 
        related_name='conversations', 
        verbose_name='شرکت‌کنندگان'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='ایجاد شده در')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین به‌روزرسانی')

    class Meta:
        verbose_name = 'مکالمه'
        verbose_name_plural = 'مکالمات'
        ordering = ('-updated_at',)

    def __str__(self):
        participant_names = []
        for user in self.participants.all():
             if hasattr(user, 'profile'):
                 name = f"{user.profile.first_name} {user.profile.last_name}".strip()
                 participant_names.append(name or user.phone)
             else:
                 participant_names.append(user.phone)
        return ", ".join(participant_names)

    def get_jalali_updated_at(self):
        """
        (اصلاح شد)
        تبدیل تاریخ میلادی به‌روزرسانی به جلالی.
        """
        if not self.updated_at:
            return "-"
        try:
            # FIX: استفاده از کانستراکتور به جای fromgregorian
            return JalaliDateTime(self.updated_at).strftime('%Y/%m/%d - %H:%M')
        except Exception:
            return self.updated_at


class Message(models.Model):
    """
    مدلی برای ذخیره هر پیام در یک مکالمه.
    """
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages', 
        verbose_name='مکالمه'
    )
    sender = models.ForeignKey(
        MyUser, 
        on_delete=models.CASCADE, 
        related_name='sent_messages', 
        verbose_name='فرستنده'
    )
    content = models.TextField(verbose_name='محتوای پیام')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='زمان ارسال')
    is_read = models.BooleanField(default=False, verbose_name='خوانده شده')

    class Meta:
        verbose_name = 'پیام'
        verbose_name_plural = 'پیام‌ها'
        ordering = ('timestamp',)

    def __str__(self):
        return f"پیام از {self.sender.phone} در {self.timestamp}"

    def get_jalali_timestamp(self):
        """
        (اصلاح شد)
        تبدیل تاریخ میلادی ارسال به جلالی.
        """
        if not self.timestamp:
            return "-"
        try:
            # FIX: استفاده از کانستراکتور به جای fromgregorian
            return JalaliDateTime(self.timestamp).strftime('%Y/%m/%d - %H:%M')
        except Exception:
            return self.timestamp