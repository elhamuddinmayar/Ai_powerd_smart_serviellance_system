from celery import shared_task
from django.utils import timezone
from surveillance.models import DetectionEvent, TargetPerson, TargetAssignment, Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@shared_task
def async_save_detection(camera_id, person_count, action, matched_target_id=None, matched_name='', assignment_id=None):
    # 1. Create the DB record
    target_obj = TargetPerson.objects.filter(pk=matched_target_id).first() if matched_target_id else None
    assignment_obj = TargetAssignment.objects.filter(pk=assignment_id).first() if assignment_id else None

    event = DetectionEvent.objects.create(
        timestamp=timezone.now(),
        person_count=person_count,
        action=action,
        matched_target=target_obj,
        matched_target_name=matched_name,
        camera_id=camera_id,
        related_assignment=assignment_obj,
        verification_status='pending' if (matched_target_id or action != 'Normal') else 'unreviewed',
    )

    channel_layer = get_channel_layer()

    # 2. Handle Target Match Notifications
    if event and matched_target_id and assignment_obj and assignment_obj.assigned_by:
        notif = Notification.objects.create(
            recipient=assignment_obj.assigned_by,
            notification_type='verification',
            title=f"Target Found: {matched_name}",
            message=f"Detected on Camera {camera_id}",
            related_assignment=assignment_obj,
            related_event=event,
        )
        
        async_to_sync(channel_layer.group_send)(
            f"user_{assignment_obj.assigned_by.id}",
            {
                "type": "send_notification",
                "notification_id": notif.id,
                "title": notif.title,
                "message": notif.message,
                "created_at": notif.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    # 3. Handle Global Activity Feed (Activity Log)
    if action != 'Normal':
        async_to_sync(channel_layer.group_send)(
            "surveillance_group",
            {
                "type": "forward_to_websocket",
                "payload": {
                    "type": "ACTIVITY_LOG",
                    "action": action,
                    "camera_id": camera_id,
                    "timestamp": event.timestamp.strftime("%H:%M:%S")
                }
            }
        )

    return event.id