from django import forms
from .models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'پیام خود را اینجا بنویسید...'
            })
        }
        labels = {
            'content': ''  # ما لیبل را خالی می‌گذاریم چون placeholder داریم
        }