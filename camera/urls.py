from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.camera_dashboard,    name='camera_dashboard'),
    path('register/',               views.camera_register,     name='camera_register'),
    path('<int:pk>/edit/',          views.camera_edit,         name='camera_edit'),
    path('<int:pk>/delete/',        views.camera_delete,       name='camera_delete'),
    path('<int:pk>/toggle/',        views.camera_toggle,       name='camera_toggle'),
    path('status/',                 views.camera_status_json,  name='camera_status_json'),
    path('discover/',               views.discover_cameras,    name='discover_cameras'),

    # ── Live viewer ──────────────────────────────────────────────────────────
    path('<int:pk>/view/',          views.camera_viewer,       name='camera_viewer'),
    path('<int:pk>/frame/',         views.camera_frame,        name='camera_frame'),
    # ── Legacy MJPEG stream (kept so old bookmarks don't 404) ───────────────
    path('<int:pk>/stream/',        views.camera_stream,       name='camera_stream'),
]