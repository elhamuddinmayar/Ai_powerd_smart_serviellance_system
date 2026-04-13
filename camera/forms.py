from django import forms
from .models import Camera


class CameraForm(forms.ModelForm):
    class Meta:
        model  = Camera
        fields = ['name', 'index_or_url', 'location', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Computer Webcam',
                'class': 'cam-input',
            }),
            'index_or_url': forms.TextInput(attrs={
                'placeholder': 'e.g. 0  or  2  or  rtsp://192.168.1.5/stream',
                'class': 'cam-input',
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'e.g. Front Gate, Room 101',
                'class': 'cam-input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Optional notes about this camera...',
                'class': 'cam-input',
                'rows': 3,
            }),
        }