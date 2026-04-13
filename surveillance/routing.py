from django.urls import re_path
from surveillance import consumers as surveillance_consumers
from camera import consumers as camera_consumers

websocket_urlpatterns = [
    re_path(r'ws/pose/$',   surveillance_consumers.PoseConsumer.as_asgi()),
    re_path(r'ws/camera/$', camera_consumers.CameraConsumer.as_asgi()),
]