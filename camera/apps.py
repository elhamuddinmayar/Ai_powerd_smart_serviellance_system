from django.apps import AppConfig
import sys
import os


class CameraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'camera'

    def ready(self):
        # Skip during management commands that don't need the engine
        ignored_cmds = [
            'migrate', 'makemigrations', 'shell', 'test',
            'collectstatic', 'createsuperuser',
        ]
        if any(cmd in sys.argv for cmd in ignored_cmds):
            return

        # With Daphne (ASGI), the server doesn't use Django's StatReloader
        # in the same way runserver does.  The safest cross-server guard is
        # to check whether we are inside the reloader *parent* process:
        #   - runserver reloader parent : RUN_MAIN is not set → skip
        #   - runserver worker child    : RUN_MAIN='true'     → run
        #   - daphne (no reloader)      : RUN_MAIN not set    → run
        #
        # So: skip ONLY when 'runserver' is in argv AND RUN_MAIN is unset.
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from .models import Camera
            from surveillance.engine import engine_manager

            active_cameras = Camera.objects.filter(is_active=True)

            for cam in active_cameras:
                # Reset to 'unknown' so the dashboard shows a spinner until
                # the thread confirms the camera is actually readable.
                Camera.objects.filter(pk=cam.pk).update(status='unknown')
                engine_manager.start_camera(cam)
                print(f"[CameraApp] Auto-started: {cam.name} ({cam.index_or_url})")

        except Exception as e:
            print(f"[CameraApp] Could not auto-start cameras: {e}")