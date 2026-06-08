from channels.generic.websocket import AsyncWebsocketConsumer
import json


class CameraConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the camera status dashboard.
    Every connected client joins 'camera_group' and receives
    CAMERA_STATUS messages pushed by the engine threads.
    """

    async def connect(self):
        await self.channel_layer.group_add("camera_group", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("camera_group", self.channel_name)

    async def forward_to_websocket(self, event):
        """Called by engine._broadcast_camera_status()"""
        await self.send(text_data=json.dumps(event["payload"]))