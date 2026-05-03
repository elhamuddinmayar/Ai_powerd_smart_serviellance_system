from django.apps import AppConfig
import sys
import os


class SurveillanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'surveillance'

    def ready(self):
        # ── Do NOT start cameras here ────────────────────────────────────────
        # Camera auto-start is handled exclusively by CameraConfig.ready()
        # (camera/apps.py).  Starting cameras from two AppConfig.ready()
        # methods caused every camera to be launched twice on boot.
        #
        # We only import the engine module here so the shared frame buffer
        # (set_frame / get_frame) is initialised before any HTTP request hits.
        # ─────────────────────────────────────────────────────────────────────
        ignored_cmds = [
            'migrate', 'makemigrations', 'shell', 'test',
            'collectstatic', 'createsuperuser',
        ]
        if any(cmd in sys.argv for cmd in ignored_cmds):
            return

        try:
            from surveillance import engine  # noqa: F401
        except Exception as e:
            print(f"[SurveillanceApp] Engine import warning: {e}")