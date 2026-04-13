from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Camera
from .forms import CameraForm
from surveillance.engine import engine_manager, _broadcast_camera_status, probe_camera_index


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == 'admin')
    )


@login_required
def camera_dashboard(request):
    cameras = Camera.objects.all()
    return render(request, 'camera/camera_dashboard.html', {
        'cameras':  cameras,
        'is_admin': is_admin(request.user),
    })


@login_required
@user_passes_test(is_admin, login_url='home')
def camera_register(request):
    if request.method == 'POST':
        form = CameraForm(request.POST)
        if form.is_valid():
            cam = form.save()
            if cam.is_active:
                engine_manager.start_camera(cam)
            messages.success(request, f"Camera '{cam.name}' registered successfully.")
            return redirect('camera_dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CameraForm()
    return render(request, 'camera/camera_register.html', {
        'form':     form,
        'is_admin': True,
    })


@login_required
@user_passes_test(is_admin, login_url='home')
def camera_edit(request, pk):
    cam = get_object_or_404(Camera, pk=pk)
    if request.method == 'POST':
        form = CameraForm(request.POST, instance=cam)
        if form.is_valid():
            cam = form.save()
            # Invalidate face embedding cache in case the camera changed
            engine_manager.invalidate_target_cache()
            engine_manager.stop_camera(cam.pk)
            if cam.is_active:
                engine_manager.start_camera(cam)
            messages.success(request, f"Camera '{cam.name}' updated.")
            return redirect('camera_dashboard')
    else:
        form = CameraForm(instance=cam)
    return render(request, 'camera/camera_register.html', {
        'form':     form,
        'is_admin': True,
        'editing':  cam,
    })


@login_required
@user_passes_test(is_admin, login_url='home')
def camera_delete(request, pk):
    cam = get_object_or_404(Camera, pk=pk)
    engine_manager.stop_camera(cam.pk)
    name = cam.name
    cam.delete()
    messages.success(request, f"Camera '{name}' removed.")
    return redirect('camera_dashboard')


@login_required
@user_passes_test(is_admin, login_url='home')
def camera_toggle(request, pk):
    cam          = get_object_or_404(Camera, pk=pk)
    cam.is_active = not cam.is_active

    if cam.is_active:
        cam.status = 'unknown'
        cam.save()
        engine_manager.start_camera(cam)
    else:
        engine_manager.stop_camera(cam.pk)
        cam.status          = 'offline'
        cam.went_offline_at = timezone.now()
        cam.save()
        _broadcast_camera_status(cam.pk, cam.name, cam.location, 'offline')

    return JsonResponse({
        'is_active': cam.is_active,
        'name':      cam.name,
        'status':    cam.status,
    })


@login_required
def camera_status_json(request):
    """
    Full camera status list for the dashboard. Called on page load and
    periodically by the camera dashboard JS to sync state.
    """
    cameras = Camera.objects.all().values(
        'id', 'name', 'location', 'index_or_url',
        'status', 'is_active', 'last_seen_at', 'went_offline_at'
    )
    data = []
    for c in cameras:
        c['last_seen_at']    = c['last_seen_at'].strftime("%Y-%m-%d %H:%M:%S") \
                               if c['last_seen_at'] else None
        c['went_offline_at'] = c['went_offline_at'].strftime("%Y-%m-%d %H:%M:%S") \
                               if c['went_offline_at'] else None
        c['is_running']      = c['id'] in engine_manager.running_ids()
        data.append(c)
    return JsonResponse({'cameras': data})


@login_required
@user_passes_test(is_admin, login_url='home')
def discover_cameras(request):
    """
    Probe integer indices 0–5 and return which are accessible.
    Useful for the admin to find which index their USB/virtual camera is on
    after a server restart. Non-blocking — uses probe_camera_index().
    """
    found = []
    for idx in range(6):
        accessible = probe_camera_index(idx, timeout=3.0)
        found.append({
            'index':      idx,
            'accessible': accessible,
            'label':      f"Camera {idx}",
        })
    return JsonResponse({'discovered': found})
