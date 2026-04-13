from django.apps import AppConfig
import sys
import os

class SurveillanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'surveillance'

    def ready(self):
        # Only start if we are running the actual server (not the auto-reloader)
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == 'true':
            try:
                # Use the new name from your engine.py
                from .engine import engine_manager
                from camera.models import Camera 

                print("--- Starting Butterfly Multi-Camera Engine ---")

                # This loops through the cameras you registered in the 'camera' app
                active_cameras = Camera.objects.all()
                
                for cam in active_cameras:
                    engine_manager.start_camera(cam)
                    
            except ImportError as e:
                print(f"[System Error] Import failed: {e}")
            except Exception as e:
                print(f"[System Error] Startup failed: {e}")