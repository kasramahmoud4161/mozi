"""
URL configuration for mozi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# mozi/urls.py

# mozi/urls.py

from django.contrib import admin
from django.urls import path , include
from django.conf import settings
from django.conf.urls.static import static
from blog import views as blog_views # <-- Add this import

admin.autodiscover()
import blog.admin
import chat.admin

urlpatterns = [
    # FIX: Move the custom admin URL here, *before* admin.site.urls
    path('admin/user/create/', blog_views.admin_user_create_view, name='admin_user_create'),
    path('Attendance/', include('Attendance.urls')),
    path('admin/', admin.site.urls), # Default admin URLs now come after the custom one
    path('', include('blog.urls')),
    path('chat/', include('chat.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)