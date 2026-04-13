/* ============================================================
   BUTTERFLY SURVEILLANCE SYSTEM — Main JavaScript
   Handles: navbar, toasts, WS notifications, photo/webcam/crop
   ============================================================ */

'use strict';

/* ── Navbar mobile toggle ──────────────────────────────────── */
(function initNav() {
  const toggle = document.getElementById('b-nav-toggle');
  const links  = document.getElementById('b-nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', () => links.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (!toggle.contains(e.target) && !links.contains(e.target))
        links.classList.remove('open');
    });
  }
})();

/* ── Toast system ──────────────────────────────────────────── */
const Toasts = (function() {
  let container;

  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'b-toasts';
      document.body.appendChild(container);
    }
    return container;
  }

  const ICONS = {
    success: '<i class="fas fa-check-circle" style="color:#2ecc71"></i>',
    error:   '<i class="fas fa-times-circle" style="color:#e74c3c"></i>',
    warning: '<i class="fas fa-exclamation-triangle" style="color:#f39c12"></i>',
    info:    '<i class="fas fa-info-circle" style="color:#3498db"></i>',
    assignment: '<i class="fas fa-tasks" style="color:#4ecca3"></i>',
    detection:  '<i class="fas fa-eye" style="color:#e74c3c"></i>',
    approved:   '<i class="fas fa-check-double" style="color:#2ecc71"></i>',
    rejected:   '<i class="fas fa-ban" style="color:#e74c3c"></i>',
    pass_back:  '<i class="fas fa-undo" style="color:#f39c12"></i>',
    verification: '<i class="fas fa-shield-alt" style="color:#3498db"></i>',
  };

  function show(type, title, message, duration = 6000) {
    const c = getContainer();
    const t = document.createElement('div');
    t.className = `b-toast b-toast--${type}`;
    t.innerHTML = `
      <div class="b-toast__icon">${ICONS[type] || ICONS.info}</div>
      <div style="flex:1">
        <div class="b-toast__title">${title}</div>
        ${message ? `<div class="b-toast__msg">${message}</div>` : ''}
      </div>
      <button class="b-toast__close" onclick="this.closest('.b-toast').remove()">✕</button>
    `;
    c.appendChild(t);
    if (duration > 0) setTimeout(() => t.remove(), duration);
    return t;
  }

  return { show };
})();

/* ── Django messages → Toasts ──────────────────────────────── */
(function djangoMessages() {
  document.querySelectorAll('[data-django-message]').forEach(el => {
    const type = el.dataset.messageType || 'info';
    const map  = { success:'success', error:'error', warning:'warning', info:'info', debug:'info' };
    Toasts.show(map[type] || 'info', el.dataset.messageTitle || '', el.textContent.trim());
    el.remove();
  });
})();

/* ── Notification bell count ───────────────────────────────── */
function updateNotifBadge(count) {
  document.querySelectorAll('[data-notif-badge]').forEach(el => {
    el.setAttribute('data-count', count);
    el.textContent = count > 99 ? '99+' : (count || '');
  });
}

/* ── WebSocket (surveillance channel) ─────────────────────── */
(function initWS() {
  const proto   = location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl   = `${proto}://${location.host}/ws/pose/`;
  let   ws      = null;
  let   retries = 0;

  function connect() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      retries = 0;
      console.log('[BF] WS connected');
      ws.send(JSON.stringify({ type: 'PING' }));
    };

    ws.onmessage = ({ data }) => {
      let msg;
      try { msg = JSON.parse(data); } catch { return; }
      handleWS(msg);
    };

    ws.onclose = () => {
      const delay = Math.min(1000 * 2 ** retries++, 30000);
      console.log(`[BF] WS closed — retry in ${delay}ms`);
      setTimeout(connect, delay);
    };

    ws.onerror = e => console.warn('[BF] WS error', e);
  }

  function handleWS(msg) {
    switch (msg.type) {

      case 'NOTIFICATION': {
        const type = msg.notification_type || 'info';
        const badge = document.querySelector('[data-notif-badge]');
        if (badge) {
          const cur = parseInt(badge.getAttribute('data-count') || '0', 10);
          updateNotifBadge(cur + 1);
        }
        Toasts.show(type, msg.title, msg.message);
        break;
      }

      case 'INITIAL_NOTIFICATIONS': {
        (msg.notifications || []).forEach(n =>
          Toasts.show(n.notification_type || 'info', n.title, n.message, 8000)
        );
        break;
      }

      case 'TARGET_MATCH':
        Toasts.show('detection', `TARGET MATCH: ${msg.name}`, `Camera: ${msg.camera}`, 10000);
        break;

      case 'ALARM':
        Toasts.show('warning', `ALARM: ${msg.action}`, `Camera: ${msg.camera}`, 8000);
        break;

      case 'STAT_UPDATE':
        document.querySelectorAll(`[data-stat-camera="${msg.camera_id}"]`).forEach(el => {
          el.textContent = msg.count;
        });
        break;

      case 'CAMERA_STATUS':
        document.querySelectorAll(`[data-cam-status="${msg.camera_id}"]`).forEach(el => {
          el.textContent = msg.status;
          el.className   = `b-badge b-badge--${msg.status === 'online' ? 'green' : 'gray'}`;
        });
        break;

      case 'PONG':
        break;
    }
  }

  // Only connect if user is logged in (check for nav presence)
  if (document.querySelector('.b-nav')) connect();

  // Expose for other scripts
  window.BFSocket = { send: d => ws && ws.readyState === 1 && ws.send(JSON.stringify(d)) };
})();

/* ── Live notification count polling (fallback) ────────────── */
(function pollNotifCount() {
  const badge = document.querySelector('[data-notif-badge]');
  if (!badge) return;
  async function poll() {
    try {
      const r = await fetch('/notifications/count/');
      const d = await r.json();
      updateNotifBadge(d.count || 0);
    } catch {}
  }
  poll();
  setInterval(poll, 30000);
})();

/* ══════════════════════════════════════════════════════════════
   PHOTO UPLOADER WITH WEBCAM CAPTURE + CROP
   ══════════════════════════════════════════════════════════════

   Usage in HTML:
     <div class="b-photo-uploader" data-uploader data-field="id_image">
       <img class="b-photo-preview" src="/static/img/placeholder.png" alt="photo">
       ...buttons rendered by macro in base.html
     </div>
*/

(function initPhotoUploaders() {

  document.querySelectorAll('[data-uploader]').forEach(uploader => {
    const fieldId  = uploader.dataset.field;
    const input    = document.getElementById(fieldId);
    const preview  = uploader.querySelector('.b-photo-preview');
    if (!input || !preview) return;

    /* ── File pick ── */
    uploader.querySelector('[data-action="pick"]')?.addEventListener('click', () => input.click());

    input.addEventListener('change', () => {
      const file = input.files[0];
      if (file) {
        const url = URL.createObjectURL(file);
        preview.src = url;
      }
    });

    /* ── Webcam capture ── */
    const camBtn    = uploader.querySelector('[data-action="webcam"]');
    const cropBtn   = uploader.querySelector('[data-action="crop"]');
    const cancelBtn = uploader.querySelector('[data-action="cancel"]');
    const useBtn    = uploader.querySelector('[data-action="use"]');
    const snapBtn   = uploader.querySelector('[data-action="snap"]');
    const recropBtn = uploader.querySelector('[data-action="recrop"]');

    // Elements inside the modal bound to THIS uploader
    const modalId   = uploader.dataset.modal;
    const modal     = document.getElementById(modalId);
    if (!modal) return;

    const video     = modal.querySelector('.b-cam-video');
    const canvas    = modal.querySelector('.b-cam-canvas');
    const cropWrap  = modal.querySelector('.b-cam-cropper-wrap');
    const cropImg   = modal.querySelector('.b-cam-cropper-img');
    const snapBtnM  = modal.querySelector('[data-modal-snap]');
    const useBtnM   = modal.querySelector('[data-modal-use]');
    const cancelM   = modal.querySelector('[data-modal-cancel]');

    let stream      = null;
    let capturedDataURL = null;
    let cropRect    = null;

    function closeModal() {
      modal.classList.remove('open');
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
      video.srcObject = null;
      cropWrap.style.display = 'none';
      video.style.display   = 'block';
      snapBtnM && (snapBtnM.style.display = 'inline-flex');
      useBtnM  && (useBtnM.style.display  = 'none');
    }

    camBtn?.addEventListener('click', async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
        });
        video.srcObject = stream;
        await video.play();
        modal.classList.add('open');
        capturedDataURL = null;
        cropRect = null;
      } catch (err) {
        Toasts.show('error', 'Camera Error', err.message);
      }
    });

    cancelM?.addEventListener('click', closeModal);
    modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });

    snapBtnM?.addEventListener('click', () => {
      // Draw current frame to canvas
      canvas.width  = video.videoWidth  || 640;
      canvas.height = video.videoHeight || 480;
      canvas.getContext('2d').drawImage(video, 0, 0);
      capturedDataURL = canvas.toDataURL('image/jpeg', .92);

      // Stop video, show crop UI
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
      video.style.display   = 'none';
      snapBtnM.style.display = 'none';
      cropWrap.style.display = 'block';
      cropImg.src = capturedDataURL;

      useBtnM && (useBtnM.style.display = 'inline-flex');

      // Init crop interaction
      initCrop(cropWrap, cropImg);
    });

    useBtnM?.addEventListener('click', () => {
      if (!capturedDataURL) return;

      // If a crop rect was drawn, slice it
      let finalDataURL = capturedDataURL;
      if (cropRect) {
        const tmpCanvas = document.createElement('canvas');
        const img       = new Image();
        img.onload = () => {
          const scaleX = img.naturalWidth  / cropImg.clientWidth;
          const scaleY = img.naturalHeight / cropImg.clientHeight;
          const w = cropRect.w * scaleX;
          const h = cropRect.h * scaleY;
          const x = cropRect.x * scaleX;
          const y = cropRect.y * scaleY;
          tmpCanvas.width  = w;
          tmpCanvas.height = h;
          tmpCanvas.getContext('2d').drawImage(img, x, y, w, h, 0, 0, w, h);
          finalDataURL = tmpCanvas.toDataURL('image/jpeg', .92);
          applyPhoto(finalDataURL);
        };
        img.src = capturedDataURL;
      } else {
        applyPhoto(finalDataURL);
      }
    });

    function applyPhoto(dataURL) {
      // Convert base64 → File and assign to input
      fetch(dataURL)
        .then(r => r.blob())
        .then(blob => {
          const file = new File([blob], 'webcam_capture.jpg', { type: 'image/jpeg' });
          const dt   = new DataTransfer();
          dt.items.add(file);
          input.files = dt.files;
          preview.src = dataURL;
          Toasts.show('success', 'Photo captured', 'Image ready — remember to save the form.', 4000);
          closeModal();
        });
    }

    /* ── Crop interaction ── */
    function initCrop(wrap, img) {
      // Remove old overlay
      wrap.querySelector('.b-crop-overlay')?.remove();
      wrap.querySelector('.b-crop-box')?.remove();

      const overlay = document.createElement('div');
      overlay.className = 'b-crop-overlay';
      wrap.appendChild(overlay);

      const box = document.createElement('div');
      box.className = 'b-crop-box';
      wrap.appendChild(box);

      let start = null;
      let dragging = false;

      overlay.addEventListener('mousedown', e => {
        const rect = img.getBoundingClientRect();
        start = {
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        };
        dragging = true;
        cropRect  = null;
        box.style.display = 'none';
      });

      document.addEventListener('mousemove', e => {
        if (!dragging || !start) return;
        const rect = img.getBoundingClientRect();
        const cx   = Math.min(Math.max(e.clientX - rect.left, 0), rect.width);
        const cy   = Math.min(Math.max(e.clientY - rect.top,  0), rect.height);
        const x = Math.min(start.x, cx);
        const y = Math.min(start.y, cy);
        const w = Math.abs(cx - start.x);
        const h = Math.abs(cy - start.y);
        box.style.left   = x + 'px';
        box.style.top    = y + 'px';
        box.style.width  = w + 'px';
        box.style.height = h + 'px';
        box.style.display = w > 10 && h > 10 ? 'block' : 'none';
      });

      document.addEventListener('mouseup', e => {
        if (!dragging) return;
        dragging = false;
        if (!start) return;
        const rect = img.getBoundingClientRect();
        const cx   = Math.min(Math.max(e.clientX - rect.left, 0), rect.width);
        const cy   = Math.min(Math.max(e.clientY - rect.top,  0), rect.height);
        const x = Math.min(start.x, cx);
        const y = Math.min(start.y, cy);
        const w = Math.abs(cx - start.x);
        const h = Math.abs(cy - start.y);
        if (w > 10 && h > 10) {
          cropRect = { x, y, w, h };
        }
        start = null;
      });
    }
  });
})();

/* ── Acknowledge assignment ────────────────────────────────── */
function bfAcknowledge(pk, csrfToken, cardEl) {
  fetch(`/assignments/${pk}/acknowledge/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
  })
  .then(r => r.json())
  .then(d => {
    if (d.status === 'ok') {
      cardEl.classList.remove('status-pending');
      cardEl.classList.add('status-acknowledged');
      cardEl.querySelector('[data-ack-btn]')?.remove();
      const badge = cardEl.querySelector('.b-badge');
      if (badge) { badge.textContent = 'Acknowledged'; badge.className = 'b-badge b-status--acknowledged'; }
      Toasts.show('success', 'Acknowledged', 'Assignment marked as acknowledged.');
    }
  })
  .catch(() => Toasts.show('error', 'Error', 'Could not acknowledge.'));
}

/* ── Snap modal ────────────────────────────────────────────── */
function openSnap(src) {
  const modal = document.getElementById('snapModal');
  if (!modal) return;
  document.getElementById('snapModalImg').src = src;
  modal.classList.add('open');
}
document.getElementById('snapModal')?.addEventListener('click', function() {
  this.classList.remove('open');
});

/* ── Confirm dialogs ───────────────────────────────────────── */
function bfConfirm(msg) { return confirm(msg); }