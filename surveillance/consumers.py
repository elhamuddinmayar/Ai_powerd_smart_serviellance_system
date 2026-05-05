from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
import logging

logger = logging.getLogger(__name__)

class PoseConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        
        await self.channel_layer.group_add("surveillance_group", self.channel_name)

        if self.user and self.user.is_authenticated:
            self.personal_group = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.personal_group, self.channel_name)
            
            await self.accept()

            unread = await self._get_unread_notifications()
            if unread:
                await self.send(text_data=json.dumps({
                    "type": "INITIAL_NOTIFICATIONS",
                    "notifications": unread
                }))
        else:
            self.personal_group = None
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("surveillance_group", self.channel_name)
        if self.personal_group:
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action_type = data.get("type")

            if action_type == "MARK_READ":
                notif_id = data.get("notification_id")
                if notif_id:
                    await self._mark_notification_read(notif_id)
            
            elif action_type == "PING":
                await self.send(text_data=json.dumps({"type": "PONG"}))

        except Exception as e:
            logger.error(f"WebSocket Receive Error: {e}")

    # ------------------------------------------------------------------
    # Channel Layer Handlers
    # ------------------------------------------------------------------

    async def forward_to_websocket(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    async def send_notification(self, event):
        """
        Receives personal notifications pushed by engine.py or views.py.

        ── Root cause of the KeyError ────────────────────────────────────
        engine.py sends supervisor notifications WITHOUT 'notification_id'
        (it creates the Notification object but forgets to include its pk
        in the channel-layer message).  Using .get() with a None default
        makes the handler safe regardless of which caller sent the event.
        ─────────────────────────────────────────────────────────────────
        """
        created_at = event.get("created_at")
        if not isinstance(created_at, str) and created_at:
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")

        await self.send(text_data=json.dumps({
            "type":              "NOTIFICATION",
            # ↓ was event["notification_id"] — crashes when key is absent
            "notification_id":   event.get("notification_id"),
            "notification_type": event.get("notification_type", "info"),
            "title":             event.get("title", ""),
            "message":           event.get("message", ""),
            "event_id":          event.get("event_id"),
            "created_at":        created_at,
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