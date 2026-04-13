# pose_gesture_system/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import surveillance.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pose_gesture_system.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            surveillance.routing.websocket_urlpatterns
        )
    ),
})