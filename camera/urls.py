from django.urls import path
from . import views

urlpatterns = [

    path('',                    views.camera_dashboard,  name='camera_dashboard'),
    path('register/',           views.camera_register,   name='camera_register'),
    path('<int:pk>/edit/',      views.camera_edit,       name='camera_edit'),
    path('<int:pk>/delete/',    views.camera_delete,     name='camera_delete'),
    path('<int:pk>/toggle/',    views.camera_toggle,     name='camera_toggle'),
    path('status/',             views.camera_status_json,name='camera_status_json'),
    path('discover/',           views.discover_cameras,  name='discover_cameras'),
    path('',              views.camera_dashboard, name='camera_dashboard'),
    path('register/',     views.camera_register,  name='camera_register'),
    path('<int:pk>/edit/',   views.camera_edit,   name='camera_edit'),
    path('<int:pk>/delete/', views.camera_delete, name='camera_delete'),
    path('<int:pk>/toggle/', views.camera_toggle, name='camera_toggle'),
    path('status.json',   views.camera_status_json, name='camera_status_json'),

]