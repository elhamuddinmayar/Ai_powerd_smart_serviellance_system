from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
import logging

logger = logging.getLogger(__name__)

class PoseConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        
        # 1. Join Global Surveillance (Detections, Status)
        await self.channel_layer.group_add("surveillance_group", self.channel_name)

        # 2. Join Personal Notifications
        if self.user and self.user.is_authenticated:
            self.personal_group = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.personal_group, self.channel_name)
            
            await self.accept()

            # 3. Push initial state (Unread Notifications)
            unread = await self._get_unread_notifications()
            if unread:
                await self.send(text_data=json.dumps({
                    "type": "INITIAL_NOTIFICATIONS",
                    "notifications": unread
                }))
        else:
            # We allow anonymous dashboard viewing but no personal notifications
            self.personal_group = None
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("surveillance_group", self.channel_name)
        if self.personal_group:
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming messages from the frontend UI."""
        try:
            data = json.loads(text_data)
            action_type = data.get("type")

            if action_type == "MARK_READ":
                notif_id = data.get("notification_id")
                if notif_id:
                    await self._mark_notification_read(notif_id)
            
            # Keep-alive ping from client
            elif action_type == "PING":
                await self.send(text_data=json.dumps({"type": "PONG"}))

        except Exception as e:
            logger.error(f"WebSocket Receive Error: {e}")

    # ------------------------------------------------------------------
    # Channel Layer Handlers (Engine -> WebSocket)
    # ------------------------------------------------------------------

    async def forward_to_websocket(self, event):
        """
        Receives STAT_UPDATE, TARGET_MATCH, and CAMERA_STATUS from engine.
        Optimized to handle the high-frequency stream.
        """
        await self.send(text_data=json.dumps(event["payload"]))

    async def send_notification(self, event):
        """
        Receives personal notifications (e.g., Target found specifically for this user).
        """
        # Ensure timestamp is stringified for JSON
        created_at = event.get("created_at")
        if not isinstance(created_at, str) and created_at:
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")

        await self.send(text_data=json.dumps({
            "type": "NOTIFICATION",
            "notification_id": event["notification_id"],
            "notification_type": event.get("notification_type", "info"),
            "title": event["title"],
            "message": event["message"],
            "event_id": event.get("event_id"),
            "created_at": created_at,
        }))

    # ------------------------------------------------------------------
    # Database Operations
    # ------------------------------------------------------------------

    @database_sync_to_async
    def _get_unread_notifications(self):
        from surveillance.models import Notification
        try:
            qs = Notification.objects.filter(
                recipient=self.user, is_read=False
            ).order_by('-created_at')[:15]
            
            # Values conversion to handle DateTimeField serialization
            notifications = []
            for n in qs:
                notifications.append({
                    "id": n.id,
                    "notification_type": n.notification_type,
                    "title": n.title,
                    "message": n.message,
                    "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })
            return notifications
        except Exception as e:
            logger.error(f"DB Error in _get_unread_notifications: {e}")
            return []

    @database_sync_to_async
    def _mark_notification_read(self, notif_id):
        from surveillance.models import Notification
        Notification.objects.filter(pk=notif_id, recipient=self.user).update(is_read=True)
