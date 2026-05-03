import asyncio
import cv2

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import Camera
from .forms  import CameraForm
from surveillance.engine import (
    engine_manager,
    _broadcast_camera_status,
    probe_camera_index,
    get_frame as engine_get_frame,
)


# ── Role helper ───────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.role == 'admin')
    )


# ── Views ─────────────────────────────────────────────────────────────────────

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
        messages.error(request, "Please fix the errors below.")
    else:
        form = CameraForm()
    return render(request, 'camera/camera_register.html', {
        'form': form, 'is_admin': True,
    })


@login_required
@user_passes_test(is_admin, login_url='home')
def camera_edit(request, pk):
    cam = get_object_or_404(Camera, pk=pk)
    if request.method == 'POST':
        form = CameraForm(request.POST, instance=cam)
        if form.is_valid():
            cam = form.save()
            engine_manager.invalidate_target_cache()
            engine_manager.stop_camera(cam.pk)
            if cam.is_active:
                engine_manager.start_camera(cam)
            messages.success(request, f"Camera '{cam.name}' updated.")
            return redirect('camera_dashboard')
    else:
        form = CameraForm(instance=cam)
    return render(request, 'camera/camera_register.html', {
        'form': form, 'is_admin': True, 'editing': cam,
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
    cam           = get_object_or_404(Camera, pk=pk)
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
    found = []
    for idx in range(6):
        found.append({
            'index':      idx,
            'accessible': probe_camera_index(idx, timeout=3.0),
            'label':      f"Camera {idx}",
        })
    return JsonResponse({'discovered': found})


# ── Placeholder builder ───────────────────────────────────────────────────────

def _build_placeholder():
    """Small black 640×360 JPEG returned when no frame is ready yet."""
    try:
        import numpy as np
        blank = np.zeros((360, 640, 3), dtype='uint8')
        cv2.putText(blank, 'CONNECTING...', (200, 190),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 180, 120), 2)
        _, buf = cv2.imencode('.jpg', blank, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return buf.tobytes()
    except Exception:
        return b''


_PLACEHOLDER = None


# ── Single-frame JPEG endpoint (ASGI-safe, replaces MJPEG stream) ─────────────
#
# ROOT CAUSE of the original MJPEG failure with Daphne:
#   StreamingHttpResponse with a persistent async generator requires Daphne to
#   keep an HTTP/1.1 chunked connection open and flush every chunk immediately.
#   In practice Daphne buffers the ASGI http.response.body events, so the
#   browser never receives any frames — it just spins forever.
#
# THE FIX — JS frame polling:
#   Instead of one long-lived MJPEG connection we serve one JPEG per call.
#   The browser JS requests /cameras/<pk>/frame/ roughly 25×/second and
#   replaces the <img> src with the new blob URL on each response.
#   Each request is a normal, short-lived HTTP exchange — Daphne handles these
#   perfectly. The camera thread continues to push frames into the shared buffer
#   (set_frame / get_frame) exactly as before; only the delivery mechanism changes.
#
# BENEFITS:
#   • Works with Daphne, uvicorn, gunicorn — any ASGI/WSGI server
#   • No persistent connections — scales to many simultaneous viewers
#   • Zero buffering issues
#   • Camera engine code is completely unchanged

@login_required
def camera_frame(request, pk):
    """
    Returns a single JPEG frame for the camera.
    Called by the JS poller ~25 times per second.
    Plain sync view — Django/Daphne wrap it in sync_to_async automatically,
    so the ASGI event loop is never blocked.
    """
    cam = get_object_or_404(Camera, pk=pk)

    if not cam.is_active:
        return HttpResponse(status=503)

    frame_bytes = engine_get_frame(cam.id)

    if not frame_bytes:
        global _PLACEHOLDER
        if _PLACEHOLDER is None:
            _PLACEHOLDER = _build_placeholder()
        frame_bytes = _PLACEHOLDER

        # Tell the JS poller this is a placeholder so it can show the overlay
        response = HttpResponse(frame_bytes, content_type='image/jpeg')
        response['X-Camera-Status'] = 'connecting'
        response['Cache-Control']   = 'no-cache, no-store, must-revalidate'
        response['Pragma']          = 'no-cache'
        response['Expires']         = '0'
        return response

    response = HttpResponse(frame_bytes, content_type='image/jpeg')
    response['X-Camera-Status'] = 'live'
    response['Cache-Control']   = 'no-cache, no-store, must-revalidate'
    response['Pragma']          = 'no-cache'
    response['Expires']         = '0'
    return response


# ── Legacy MJPEG stream (kept for backward-compat / direct URL access) ────────
#
# NOTE: This still exists so any bookmarked /stream/ URLs don't 404,
#       but the dashboard and viewer no longer use it — they use /frame/ + JS.

async def camera_stream(request, pk):
    """
    Legacy MJPEG endpoint — kept for backward compatibility only.
    New code should use camera_frame (JS polling) instead.
    """
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized — please log in.", status=401)

    try:
        cam = await sync_to_async(Camera.objects.get)(pk=pk)
    except Camera.DoesNotExist:
        return HttpResponse("Camera not found.", status=404)

    if not cam.is_active:
        return HttpResponse("Camera is disabled.", status=503)

    async def _gen():
        global _PLACEHOLDER
        try:
            while True:
                frame_bytes = engine_get_frame(cam.id)
                if not frame_bytes:
                    if _PLACEHOLDER is None:
                        _PLACEHOLDER = _build_placeholder()
                    frame_bytes = _PLACEHOLDER
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n'
                    + frame_bytes +
                    b'\r\n'
                )
                await asyncio.sleep(0.04)
        except (GeneratorExit, asyncio.CancelledError):
            pass

    response = StreamingHttpResponse(
        _gen(),
        content_type='multipart/x-mixed-replace; boundary=frame',
    )
    response['Cache-Control']     = 'no-cache, no-store, must-revalidate'
    response['X-Accel-Buffering'] = 'no'
    return response


# ── Camera viewer page ────────────────────────────────────────────────────────

@login_required
def camera_viewer(request, pk):
    cam = get_object_or_404(Camera, pk=pk)
    return render(request, 'camera/camera_viewer.html', {
        'cam':      cam,
        'is_admin': is_admin(request.user),
    })