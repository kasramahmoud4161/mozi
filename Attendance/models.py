from django.db import models

# مدل دوربین
class Camera(models.Model):
    name = models.CharField(max_length=255)
    stream_url = models.URLField()
    
    def __str__(self):
        return self.name

# مدل دانش‌آموز
class Student(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# مدل رکورد حضور و غیاب
class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[('present','حاضر'),('absent','غایب')], default='present')
    
    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"
