from django.shortcuts import render, redirect
from django.views import View
from .models import Student, AttendanceRecord
from django.contrib import messages
import datetime

class AttendanceReportView(View):
    def get(self, request):
        students = Student.objects.all()
        today = datetime.date.today()

        # Optional: فیلتر بر اساس تاریخ از query params
        start_date = request.GET.get('start_date', today - datetime.timedelta(days=30))
        end_date = request.GET.get('end_date', today)

        # تبدیل به datetime.date
        if isinstance(start_date, str):
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        data = []
        for student in students:
            total_days = AttendanceRecord.objects.filter(
                student=student,
                date__range=[start_date, end_date]
            ).count()
            present_days = AttendanceRecord.objects.filter(
                student=student,
                date__range=[start_date, end_date],
                status='present'
            ).count()
            absent_days = total_days - present_days
            percent_present = round((present_days / total_days) * 100, 2) if total_days > 0 else 0
            data.append({
                'student': student.get_full_name or student.phone,
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'percent_present': percent_present
            })

        context = {
            'data': data,
            'start_date': start_date,
            'end_date': end_date
        }
        return render(request, 'attendance_report.html', context)
class AttendanceManageView(View):
    def get(self, request):
        today = datetime.date.today()
        students = Student.objects.all()
        attendance_today = {record.student.id: record.status for record in AttendanceRecord.objects.filter(date=today)}
        context = {
            'students': students,
            'attendance_today': attendance_today,
            'today': today,
        }
        return render(request, 'attendance_manage.html', context)

    def post(self, request):
        today = datetime.date.today()
        for student_id, status in request.POST.items():
            if student_id.startswith('status_'):
                sid = int(student_id.split('_')[1])
                AttendanceRecord.objects.update_or_create(
                    student_id=sid,
                    date=today,
                    defaults={'status': status}
                )
        messages.success(request, 'وضعیت حضور و غیاب برای امروز با موفقیت ثبت شد.')
        return redirect('blog:attendance_manage')
class DashboardView(View):
    def get(self, request):
        return render(request, 'dashboard.html')

# ثبت دانش‌آموز
class EnrollmentView(View):
    def get(self, request):
        return render(request, 'enroll.html')

    def post(self, request):
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        if name:
            student = Student.objects.create(name=name, phone=phone)
            messages.success(request, f"دانش‌آموز {student.name} با موفقیت ثبت شد.")
        else:
            messages.error(request, "نام دانش‌آموز الزامی است.")
        return redirect('attendance_enroll')

# پخش دوربین
class CameraStreamView(View):
    def get(self, request, camera_id):
        camera = get_object_or_404(Camera, id=camera_id)
        return render(request, 'stream.html', {'camera': camera})

# لیست دوربین‌ها
class CameraListView(View):
    def get(self, request):
        cameras = Camera.objects.all()
        return render(request, 'camera_list.html', {'cameras': cameras})
