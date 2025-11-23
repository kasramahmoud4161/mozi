from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # /chat/ -> لیست مکالمات
    path('', views.chat_list_view, name='chat_list'),
    
    # /chat/new/ -> (جدید) صفحه انتخاب کاربر برای چت
    path('new/', views.chat_new_view, name='chat_new'),
    
    # /chat/<int:conversation_id>/ -> نمایش یک مکالمه
    path('<int:conversation_id>/', views.chat_detail_view, name='chat_detail'),
    
    # /chat/start/<int:user_id>/ -> شروع چت با کاربر دیگر
    path('start/<int:user_id>/', views.start_chat_view, name='start_chat'),
]