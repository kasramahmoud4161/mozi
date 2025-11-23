from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # FIX: تغییر نام تابع از login_view به user_login برای مطابقت با views.py
# FIX: تغییر مسیر از '' به 'login/'
    path('login/', views.user_login, name='login'), 

    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    # ------------------ مدیریت پروفایل کاربر ------------------
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'), 
    
    # ------------------ داشبوردها و صفحات اصلی ------------------
    path('', views.home_modules_view, name='home_modules'),
    path('dashboard/', views.dashboard_view, name='dashboard'), 
    path('search/', views.global_search_view, name='global_search'),
    # ------------------ ماژول حضور و غیاب ------------------
    path('attendance/manage/', views.attendance_manage_view, name='attendance_manage'),
    path('attendance/report/', views.attendance_report_view, name='attendance_report'),
    
    # ------------------ ماژول نمرات ------------------
    path('grades/entry/', views.grade_entry_view, name='grade_entry'),
    path('grades/report/', views.grade_report_view, name='grade_report'),
    path('ajax/load-exams/', views.load_exams_ajax, name='ajax_load_exams'), # مسیر AJAX
    
    # ------------------ مدیریت کاربران (انحصاری مدیر) ------------------
    path('admin/user/create/', views.admin_user_create_view, name='admin_user_create'), # این باید اینجا بماند
    # FIX: این خط تکراری است و باید حذف شود
    # path('admin/user/create/', views.admin_user_create_view, name='admin_user_create'),

# ==========================================================
# 7. ماژول تکالیف (بخش جدید)
# ==========================================================
    path('assignments/', views.assignment_list_view, name='assignment_list'),
    path('assignments/create/', views.assignment_create_view, name='assignment_create'),
    path('assignments/<int:assignment_id>/submit/', views.submission_create_view, name='submission_create')
]