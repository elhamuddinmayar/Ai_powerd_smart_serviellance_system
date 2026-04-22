import os
import cv2
import uuid
import threading
import time
import numpy as np
import torch
from django.utils import timezone
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from ultralytics import YOLO
from deepface import DeepFace

# -- Path Configuration --
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOLO_PATH = os.path.join(BASE_DIR, 'surveillance', 'models', 'yolo11n_models', 'yolo11n-pose.pt')

# -- Detection Constants --
DEEPFACE_MODEL      = "Facenet512"
DEEPFACE_BACKEND    = "retinaface"
THRESHOLD           = 0.30
FACE_CHECK_INTERVAL = 5
MATCH_COOLDOWN_SEC  = 15

# -- YOLO Model Loader --
_yolo_model = None
_yolo_lock  = threading.Lock()

def get_yolo_model():
    global _yolo_model
    with _yolo_lock:
        if _yolo_model is None:
            model = YOLO(YOLO_PATH)
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            model.to(device)
            _yolo_model = model
        return _yolo_model

# -- Broadcast Helpers --
def _broadcast(data):
    try:
        cl = get_channel_layer()
        if cl:
            async_to_sync(cl.group_send)(
                "surveillance_group",
                {"type": "forward_to_websocket", "payload": data},
            )
    except Exception:
        pass

def _broadcast_camera_status(camera_id, camera_name, location, status):
    _broadcast({
        "type": "CAMERA_STATUS",
        "camera_id": camera_id,
        "status": status,
        "timestamp": timezone.now().isoformat()
    })

# -- Save snapshot to disk, returns relative path or None --
def _save_snapshot(frame):
    try:
        filename = f"{uuid.uuid4().hex}.jpg"
        save_dir = os.path.join(settings.MEDIA_ROOT, 'snapshots')
        os.makedirs(save_dir, exist_ok=True)
        full_path = os.path.join(save_dir, filename)
        cv2.imwrite(full_path, frame)
        return f"snapshots/{filename}"   # relative to MEDIA_ROOT
    except Exception as e:
        print(f"[snapshot] Failed to save: {e}")
        return None

# -- Save detection event to DB (no Celery) --
def _save_detection(camera_id, person_count, action,
                    matched_target_id=None, matched_name='',
                    assignment_id=None, frame=None):
    try:
        import django
        django.setup() if not django.apps.registry.apps.ready else None
    except Exception:
        pass

    try:
        from surveillance.models import DetectionEvent, TargetPerson, TargetAssignment, Notification

        target_obj     = TargetPerson.objects.filter(pk=matched_target_id).first() if matched_target_id else None
        assignment_obj = TargetAssignment.objects.filter(pk=assignment_id).first() if assignment_id else None

        # Save snapshot image
        snapshot_relative_path = _save_snapshot(frame) if frame is not None else None

        # Build the event without frame_snapshot first
        event = DetectionEvent(
            timestamp=timezone.now(),
            person_count=person_count,
            action=action,
            matched_target=target_obj,
            matched_target_name=matched_name,
            camera_id=camera_id,
            related_assignment=assignment_obj,
            verification_status='pending' if (matched_target_id or action != 'Normal') else 'unreviewed',
        )

        # Assign snapshot path correctly to ImageField
        if snapshot_relative_path:
            event.frame_snapshot.name = snapshot_relative_path

        event.save()

        channel_layer = get_channel_layer()

        # Notify supervisor/admin if target matched
        if matched_target_id and assignment_obj and assignment_obj.assigned_by:
            notif = Notification.objects.create(
                recipient=assignment_obj.assigned_by,
                notification_type='verification',
                title=f"Target Found: {matched_name}",
                message=f"Detected on Camera {camera_id}",
                related_assignment=assignment_obj,
                related_event=event,
            )
            try:
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
            except Exception as e:
                print(f"[notification] WebSocket send failed: {e}")

        # Also notify the target's uploaded_by (supervisor) directly
        # even if no assignment exists — this fixes supervisor history
        if matched_target_id and target_obj and target_obj.uploaded_by:
            supervisor = target_obj.uploaded_by
            # Only notify if not already notified via assignment
            if not (assignment_obj and assignment_obj.assigned_by == supervisor):
                try:
                    Notification.objects.create(
                        recipient=supervisor,
                        notification_type='detection',
                        title=f"Your target detected: {matched_name}",
                        message=f"Detected on Camera {camera_id}",
                        related_event=event,
                    )
                    async_to_sync(channel_layer.group_send)(
                        f"user_{supervisor.id}",
                        {
                            "type": "send_notification",
                            "title": f"Target Detected: {matched_name}",
                            "message": f"Detected on Camera {camera_id}",
                            "created_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                except Exception as e:
                    print(f"[supervisor notify] Failed: {e}")

        # Broadcast activity log for non-normal actions
        if action != 'Normal':
            try:
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
            except Exception as e:
                print(f"[activity_log] Broadcast failed: {e}")

        print(f"[_save_detection] Saved event {event.id} | action={action} | target={matched_name} | snapshot={snapshot_relative_path}")
        return event.id

    except Exception as e:
        import traceback
        print(f"[_save_detection] ERROR: {e}")
        traceback.print_exc()
        return None

# -- Face Recognition Worker Thread --
class DeepFaceWorker(threading.Thread):
    def __init__(self, on_match):
        super().__init__(daemon=True)
        self._queue  = []
        self._lock   = threading.Lock()
        self._event  = threading.Event()
        self.on_match = on_match
        self.targets  = []
        self.running  = True
        self._embedding_cache = {}
        self._last_match_time = {}

    def submit(self, frame, boxes):
        h, w = frame.shape[:2]
        crops = []
        for (x1, y1, x2, y2) in boxes:
            pw, ph = int((x2 - x1) * 0.2), int((y2 - y1) * 0.2)
            nx1 = max(0, int(x1) - pw)
            ny1 = max(0, int(y1) - ph)
            nx2 = min(w, int(x2) + pw)
            ny2 = min(h, int(y2) + ph)
            crops.append(frame[ny1:ny2, nx1:nx2])

        with self._lock:
            self._queue = [(frame.copy(), crops)]
        self._event.set()

    def run(self):
        while self.running:
            self._event.wait()
            self._event.clear()
            item = None
            with self._lock:
                if self._queue:
                    item = self._queue.pop(0)
            if not item or not self.targets:
                continue

            full_frame, crops = item

            for target in self.targets:
                if (time.time() - self._last_match_time.get(target['id'], 0)) < MATCH_COOLDOWN_SEC:
                    continue

                # Cache target embedding
                if target['id'] not in self._embedding_cache:
                    try:
                        res = DeepFace.represent(
                            img_path=target['path'],
                            model_name=DEEPFACE_MODEL,
                            detector_backend=DEEPFACE_BACKEND
                        )
                        if res:
                            self._embedding_cache[target['id']] = np.array(res[0]['embedding'])
                    except Exception as e:
                        print(f"[DeepFace] Target embed failed: {e}")
                        continue

                t_vec = self._embedding_cache.get(target['id'])
                if t_vec is None:
                    continue

                for crop in crops:
                    try:
                        res = DeepFace.represent(
                            img_path=crop,
                            model_name=DEEPFACE_MODEL,
                            detector_backend=DEEPFACE_BACKEND
                        )
                        if res:
                            c_vec = np.array(res[0]['embedding'])
                            dist  = 1.0 - (
                                np.dot(c_vec, t_vec) /
                                (np.linalg.norm(c_vec) * np.linalg.norm(t_vec))
                            )
                            if dist <= THRESHOLD:
                                self._last_match_time[target['id']] = time.time()
                                self.on_match(
                                    target['id'],
                                    target['name'],
                                    target.get('assignment_id'),
                                    full_frame.copy()
                                )
                                break
                    except Exception:
                        continue

    def stop(self):
        self.running = False
        self._event.set()   # unblock the wait() so thread exits cleanly


# -- Main Camera Thread --
class CameraThread(threading.Thread):
    def __init__(self, camera_obj):
        super().__init__(daemon=True)
        self.camera_id    = camera_obj.id
        self.camera_name  = camera_obj.name
        self.location     = camera_obj.location
        self.index_or_url = camera_obj.index_or_url
        self.running      = False
        self._deepface    = DeepFaceWorker(self._on_face_match)

    def _on_face_match(self, tid, name, aid, frame):
        # 1. Broadcast real-time alert immediately
        _broadcast({
            "type": "TARGET_MATCH",
            "name": name,
            "camera": self.camera_name,
            "camera_id": self.camera_id
        })

        # 2. Save to DB with snapshot — runs in DeepFaceWorker thread
        _save_detection(
            camera_id=self.camera_id,
            person_count=1,
            action='Normal',
            matched_target_id=tid,
            matched_name=name,
            assignment_id=aid,
            frame=frame,
        )

    def analyze_pose(self, keypoints_data):
        if keypoints_data is None or len(keypoints_data.xy) == 0:
            return "Normal"
        try:
            kp   = keypoints_data.xy[0].cpu().numpy()
            conf = keypoints_data.conf[0].cpu().numpy()

            # HAND WAVING
            if any(conf[1:3] > 0.5):
                eye_y = np.mean([kp[i][1] for i in [1, 2] if conf[i] > 0.5])
                if (conf[9]  > 0.5 and kp[9][1]  < (eye_y - 10)) or \
                   (conf[10] > 0.5 and kp[10][1] < (eye_y - 10)):
                    return "HAND WAVING"

            # FALL DETECTED
            if conf[0] > 0.5 and (conf[11] > 0.5 or conf[12] > 0.5):
                hip_y = np.mean([kp[i][1] for i in [11, 12] if conf[i] > 0.5])
                if kp[0][1] > (hip_y - 40):
                    return "FALL DETECTED"

        except Exception:
            pass
        return "Normal"

    def refresh_targets(self):
        try:
            from surveillance.models import TargetPerson, TargetAssignment
            active = TargetPerson.objects.filter(is_found=False).distinct()
            t_list = []
            for t in active:
                ass = TargetAssignment.objects.filter(target=t).last()
                t_list.append({
                    "id":            t.pk,
                    "name":          t.name,
                    "path":          t.image.path,
                    "assignment_id": ass.pk if ass else None
                })
            self._deepface.targets = t_list
        except Exception as e:
            print(f"[refresh_targets] Error: {e}")

    def run(self):
        self.running = True
        model = get_yolo_model()
        src   = int(self.index_or_url) if self.index_or_url.isdigit() else self.index_or_url

        self._deepface.start()
        self.refresh_targets()
        _broadcast_camera_status(self.camera_id, self.camera_name, self.location, 'online')

        frame_count       = 0
        last_action_save  = 0
        consecutive_fails = 0
        MAX_FAILS         = 10

        def open_capture():
            cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        cap = open_capture()

        while self.running:
            try:
                ret, frame = cap.read()
            except Exception as e:
                print(f"[Camera {self.camera_id}] cap.read() exception: {e}")
                ret, frame = False, None

            # Handle bad frame
            if not ret or frame is None:
                consecutive_fails += 1
                print(f"[Camera {self.camera_id}] Bad frame ({consecutive_fails}/{MAX_FAILS})")

                if consecutive_fails >= MAX_FAILS:
                    print(f"[Camera {self.camera_id}] Too many failures, reconnecting...")
                    try:
                        cap.release()
                    except Exception:
                        pass
                    time.sleep(2)
                    cap = open_capture()
                    consecutive_fails = 0
                    if not cap.isOpened():
                        print(f"[Camera {self.camera_id}] Reconnect failed, retrying in 5s...")
                        time.sleep(5)
                else:
                    time.sleep(0.1)
                continue

            # Good frame
            consecutive_fails = 0

            try:
                if frame_count % 2 == 0:
                    results = model.predict(source=frame, conf=0.50, verbose=False)

                    if results and len(results[0].boxes) > 0:
                        person_count = len(results[0].boxes)
                        action       = self.analyze_pose(results[0].keypoints)

                        if action != "Normal":
                            _broadcast({
                                "type": "ALARM",
                                "action": action,
                                "camera": self.camera_name,
                                "camera_id": self.camera_id
                            })

                            if (time.time() - last_action_save > 5):
                                # Save pose alarm in background thread with snapshot
                                threading.Thread(
                                    target=_save_detection,
                                    args=(self.camera_id, person_count, action),
                                    kwargs={"frame": frame.copy()},
                                    daemon=True
                                ).start()
                                last_action_save = time.time()

                        if frame_count % FACE_CHECK_INTERVAL == 0:
                            boxes = [tuple(b[:4]) for b in results[0].boxes.xyxy.cpu().numpy()]
                            self._deepface.submit(frame, boxes)

                        _broadcast({"type": "STAT_UPDATE", "count": person_count, "camera_id": self.camera_id})
                    else:
                        _broadcast({"type": "STAT_UPDATE", "count": 0, "camera_id": self.camera_id})

            except Exception as e:
                print(f"[Camera {self.camera_id}] Processing error: {e}")

            if frame_count % 600 == 0:
                self.refresh_targets()

            frame_count += 1

        try:
            cap.release()
        except Exception:
            pass

        self._deepface.stop()
        _broadcast_camera_status(self.camera_id, self.camera_name, self.location, 'offline')

    def stop(self):
        self.running = False


# -- Engine Manager --
class EngineManager:
    def __init__(self):
        self._threads = {}

    def start_camera(self, camera_obj):
        if camera_obj.id in self._threads and self._threads[camera_obj.id].is_alive():
            return
        t = CameraThread(camera_obj)
        self._threads[camera_obj.id] = t
        t.start()

    def stop_camera(self, camera_id):
        t = self._threads.pop(camera_id, None)
        if t:
            t.stop()


engine_manager = EngineManager()


def probe_camera_index(idx: int, timeout: float = 3.0) -> bool:
    result = [False]
    ev = threading.Event()
    def _try():
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, _ = cap.read()
            result[0] = ok
        cap.release()
        ev.set()
    threading.Thread(target=_try, daemon=True).start()
    ev.wait(timeout=timeout)
    return result[0]