# 🦋 Butterfly — AI Smart Surveillance System

> Real-time pose & gesture recognition system with face matching, multi-camera support, and role-based access control.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Django](https://img.shields.io/badge/Django-5.x-green?style=flat-square&logo=django)
![YOLO](https://img.shields.io/badge/YOLO-v11-red?style=flat-square)
![DeepFace](https://img.shields.io/badge/DeepFace-Facenet512-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## ✨ Features

- 🎯 **Real-time Person Detection** — YOLO11 pose model on live camera feeds
- 🤸 **Pose Analysis** — Fall detection & hand waving gesture recognition
- 🧬 **Face Recognition** — DeepFace (Facenet512 + RetinaFace) for target matching
- 📷 **Multi-Camera Support** — Manage multiple cameras simultaneously
- 👥 **Role-Based Access** — Admin / Supervisor / Operator permission system
- 🔔 **Live WebSocket Alerts** — Real-time notifications via Django Channels
- 📸 **Auto Snapshots** — Captures frame on every detection event
- 📄 **PDF Reports** — Export approved detection events as official reports
- ✅ **Verification Workflow** — Supervisor approves/rejects detections before export
- 🌍 **Multi-language** — i18n support

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5, Django Channels, ASGI |
| AI/ML | YOLO11, DeepFace, PyTorch, OpenCV |
| Real-time | WebSockets, Redis |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite / PostgreSQL |

---

## 🚀 Setup

```bash
# 1. Clone the repo
git clone https://github.com/elhamuddinmayar/pose_and_gesture_recognition_system.git
cd pose_and_gesture_recognition_system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Run the server
python manage.py runserver
```

> Redis must be running for WebSocket support: `redis-server`

---

## 📁 Project Structure
├── camera/          # Camera model & management
├── surveillance/    # Core app — detection, targets, roles
├── core/            # Settings & routing
├── static/          # CSS, JS, assets
└── locale/          # i18n translations


---

## 👤 Author

**Elhamuddin Mayar**  
[![Portfolio](https://img.shields.io/badge/Portfolio-elhamuddinmayar.netlify.app-blue?style=flat-square)](https://elhamuddinmayar.netlify.app)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-elhamuddinmayar-blue?style=flat-square&logo=linkedin)](https://linkedin.com/in/elhamuddinmayar)

