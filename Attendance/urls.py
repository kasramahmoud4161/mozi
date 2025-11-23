from django.urls import path
from .views import DashboardView, EnrollmentView, CameraStreamView, CameraListView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('enroll/', EnrollmentView.as_view(), name='attendance_enroll'),
    path('stream/<int:camera_id>/', CameraStreamView.as_view(), name='camera_stream'),
    path('cameras/', CameraListView.as_view(), name='camera_list'),
]
