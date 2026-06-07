from django.urls import path
from . import views

urlpatterns = [
    path('set-language/<str:lang_code>/', views.set_language, name='set_lang'),
]