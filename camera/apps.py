from django.apps import AppConfig
import sys

class CameraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'camera'

    def ready(self):
        # 1. Skip during management commands that don't need the engine
        ignored_cmds = [
            'migrate', 'makemigrations', 'shell', 'test', 
            'collectstatic', 'createsuperuser'
        ]
        if any(cmd in sys.argv for cmd in ignored_cmds):
            return

        # 2. Attempt to auto-start active cameras
        try:
            from .models import Camera
            from surveillance.engine import engine_manager

            active_cameras = Camera.objects.filter(is_active=True)
            
            for cam in active_cameras:
                # Reset status to 'unknown' so dashboard reflects startup state
                # Using .update() is efficient as it stays at the DB level
                Camera.objects.filter(pk=cam.pk).update(status='unknown')
                
                # Start the engine for this camera
                engine_manager.start_camera(cam)
                print(f"[CameraApp] Auto-started: {cam.name} ({cam.index_or_url})")

        except Exception as e:
            print(f"[CameraApp] Could not auto-start cameras: {e}")