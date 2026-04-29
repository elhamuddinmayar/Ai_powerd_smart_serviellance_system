/* ============================================================
   BUTTERFLY SURVEILLANCE SYSTEM — Main JavaScript v2
   Handles: navbar, toasts, WS, photo/webcam/crop, mobile UX
   ============================================================ */

'use strict';

/* ── Navbar mobile toggle ──────────────────────────────────── */
(function initNav() {
  const toggle = document.getElementById('b-nav-toggle');
  const links  = document.getElementById('b-nav-links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', e => {
    e.stopPropagation();
    const open = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open);
    toggle.innerHTML = open ? '<i class="fas fa-times"></i>' : '<i class="fas fa-bars"></i>';
  });

  document.addEventListener('click', e => {
    if (links.classList.contains('open') && !links.contains(e.target) && !toggle.contains(e.target)) {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.innerHTML = '<i class="fas fa-bars"></i>';
    }
  });

  // Close on nav link click (mobile)
  links.querySelectorAll('.b-nav__link').forEach(link => {
    link.addEventListener('click', () => {
      links.classList.remove('open');
      toggle.innerHTML = '<i class="fas fa-bars"></i>';
    });
  });
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
    success:      '<i class="fas fa-check-circle" style="color:#4ecca3"></i>',
    error:        '<i class="fas fa-times-circle" style="color:#e94560"></i>',
    warning:      '<i class="fas fa-exclamation-triangle" style="color:#f39c12"></i>',
    info:         '<i class="fas fa-info-circle" style="color:#3498db"></i>',
    assignment:   '<i class="fas fa-tasks" style="color:#4ecca3"></i>',
    detection:    '<i class="fas fa-eye" style="color:#e94560"></i>',
    approved:     '<i class="fas fa-check-double" style="color:#2ecc71"></i>',
    rejected:     '<i class="fas fa-ban" style="color:#e94560"></i>',
    pass_back:    '<i class="fas fa-undo" style="color:#f39c12"></i>',
    verification: '<i class="fas fa-shield-alt" style="color:#3498db"></i>',
  };

  function show(type, title, message, duration = 6000) {
    const c = getContainer();
    const t = document.createElement('div');
    t.className = `b-toast b-toast--${type}`;
    t.innerHTML = `
      <div class="b-toast__icon">${ICONS[type] || ICONS.info}</div>
      <div style="flex:1;min-width:0;">
        <div class="b-toast__title">${title}</div>
        ${message ? `<div class="b-toast__msg">${message}</div>` : ''}
      </div>
      <button class="b-toast__close" aria-label="Close">✕</button>
    `;
    t.querySelector('.b-toast__close').addEventListener('click', () => t.remove());
    c.appendChild(t);
    if (duration > 0) setTimeout(() => { if (t.parentNode) t.remove(); }, duration);
    return t;
  }

  return { show };
})();

/* ── Django messages → Toasts ──────────────────────────────── */
(function djangoMessages() {
  document.querySelectorAll('[data-django-message]').forEach(el => {
    const type = el.dataset.messageType || 'info';
    const map  = { success:'success', error:'error', warning:'warning', info:'info', debug:'info' };
    Toasts.show(map[type] || 'info', el.dataset.messageTitle || 'Notice', el.textContent.trim());
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
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${proto}://${location.host}/ws/pose/`;
  let ws      = null;
  let retries = 0;
  let pingTimer = null;

  function connect() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      retries = 0;
      ws.send(JSON.stringify({ type: 'PING' }));
      pingTimer = setInterval(() => ws.readyState === 1 && ws.send(JSON.stringify({ type: 'PING' })), 25000);
    };

    ws.onmessage = ({ data }) => {
      let msg;
      try { msg = JSON.parse(data); } catch { return; }
      handleWS(msg);
    };

    ws.onclose = () => {
      clearInterval(pingTimer);
      const delay = Math.min(1000 * 2 ** retries++, 30000);
      setTimeout(connect, delay);
    };

    ws.onerror = e => console.warn('[BF] WS error', e);
  }

  function handleWS(msg) {
    switch (msg.type) {
      case 'NOTIFICATION': {
        const badge = document.querySelector('[data-notif-badge]');
        if (badge) updateNotifBadge((parseInt(badge.getAttribute('data-count') || '0', 10)) + 1);
        Toasts.show(msg.notification_type || 'info', msg.title, msg.message);
        break;
      }
      case 'INITIAL_NOTIFICATIONS':
        (msg.notifications || []).forEach(n =>
          Toasts.show(n.notification_type || 'info', n.title, n.message, 8000)
        );
        break;
      case 'TARGET_MATCH':
        Toasts.show('detection', `TARGET MATCH: ${msg.name}`, `Camera: ${msg.camera}`, 10000);
        break;
      case 'ALARM':
        Toasts.show('warning', `ALARM: ${msg.action}`, `Camera: ${msg.camera}`, 8000);
        break;
      case 'STAT_UPDATE':
        document.querySelectorAll(`[data-stat-camera="${msg.camera_id}"]`).forEach(el => { el.textContent = msg.count; });
        break;
      case 'CAMERA_STATUS':
        document.querySelectorAll(`[data-cam-status="${msg.camera_id}"]`).forEach(el => {
          el.textContent = msg.status;
          el.className   = `b-badge b-badge--${msg.status === 'online' ? 'green' : 'gray'}`;
        });
        break;
    }
  }

  if (document.querySelector('.b-nav')) connect();
  window.BFSocket = { send: d => ws && ws.readyState === 1 && ws.send(JSON.stringify(d)) };
})();

/* ── Notification count polling (fallback) ─────────────────── */
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

/* ═══════════════════════════════════════════════════════════
   PHOTO UPLOADER WITH WEBCAM + CROP
   ═══════════════════════════════════════════════════════════ */
(function initPhotoUploaders() {
  document.querySelectorAll('[data-uploader]').forEach(uploader => {
    const fieldId = uploader.dataset.field;
    const input   = document.getElementById(fieldId);
    const preview = uploader.querySelector('.b-photo-preview');
    if (!input || !preview) return;

    /* File pick */
    uploader.querySelector('[data-action="pick"]')?.addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
      const file = input.files[0];
      if (file) preview.src = URL.createObjectURL(file);
    });

    const modalId = uploader.dataset.modal;
    const modal   = document.getElementById(modalId);
    if (!modal) return;

    const video    = modal.querySelector('.b-cam-video');
    const canvas   = modal.querySelector('.b-cam-canvas');
    const cropWrap = modal.querySelector('.b-cam-cropper-wrap');
    const cropImg  = modal.querySelector('.b-cam-cropper-img');
    const snapBtnM = modal.querySelector('[data-modal-snap]');
    const useBtnM  = modal.querySelector('[data-modal-use]');
    const cancelM  = modal.querySelector('[data-modal-cancel]');

    let stream = null;
    let capturedDataURL = null;
    let cropRect = null;

    function closeModal() {
      modal.classList.remove('open');
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
      video.srcObject = null;
      cropWrap.style.display = 'none';
      video.style.display    = 'block';
      if (snapBtnM) snapBtnM.style.display = 'inline-flex';
      if (useBtnM)  useBtnM.style.display  = 'none';
    }

    uploader.querySelector('[data-action="webcam"]')?.addEventListener('click', async () => {
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
      canvas.width  = video.videoWidth  || 640;
      canvas.height = video.videoHeight || 480;
      canvas.getContext('2d').drawImage(video, 0, 0);
      capturedDataURL = canvas.toDataURL('image/jpeg', .92);
      if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
      video.style.display    = 'none';
      snapBtnM.style.display = 'none';
      cropWrap.style.display = 'block';
      cropImg.src = capturedDataURL;
      if (useBtnM) useBtnM.style.display = 'inline-flex';
      initCrop(cropWrap, cropImg);
    });

    useBtnM?.addEventListener('click', () => {
      if (!capturedDataURL) return;
      if (cropRect) {
        const img = new Image();
        img.onload = () => {
          const scaleX = img.naturalWidth  / cropImg.clientWidth;
          const scaleY = img.naturalHeight / cropImg.clientHeight;
          const tmpCanvas = document.createElement('canvas');
          tmpCanvas.width  = cropRect.w * scaleX;
          tmpCanvas.height = cropRect.h * scaleY;
          tmpCanvas.getContext('2d').drawImage(img,
            cropRect.x * scaleX, cropRect.y * scaleY,
            cropRect.w * scaleX, cropRect.h * scaleY,
            0, 0, tmpCanvas.width, tmpCanvas.height
          );
          applyPhoto(tmpCanvas.toDataURL('image/jpeg', .92));
        };
        img.src = capturedDataURL;
      } else {
        applyPhoto(capturedDataURL);
      }
    });

    function applyPhoto(dataURL) {
      fetch(dataURL)
        .then(r => r.blob())
        .then(blob => {
          const file = new File([blob], 'webcam_capture.jpg', { type: 'image/jpeg' });
          const dt   = new DataTransfer();
          dt.items.add(file);
          input.files = dt.files;
          preview.src = dataURL;
          Toasts.show('success', 'Photo captured', 'Image ready — save the form to apply.', 4000);
          closeModal();
        });
    }

    function initCrop(wrap, img) {
      wrap.querySelector('.b-crop-overlay')?.remove();
      wrap.querySelector('.b-crop-box')?.remove();

      const overlay = document.createElement('div');
      overlay.className = 'b-crop-overlay';
      wrap.appendChild(overlay);

      const box = document.createElement('div');
      box.className = 'b-crop-box';
      wrap.appendChild(box);

      let start = null, dragging = false;

      function getPos(e, rect) {
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
          x: Math.min(Math.max(clientX - rect.left, 0), rect.width),
          y: Math.min(Math.max(clientY - rect.top,  0), rect.height),
        };
      }

      function startCrop(e) {
        e.preventDefault();
        const rect = img.getBoundingClientRect();
        const pos  = getPos(e, rect);
        start = pos;
        dragging = true;
        cropRect = null;
        box.style.display = 'none';
      }

      function moveCrop(e) {
        if (!dragging || !start) return;
        e.preventDefault();
        const rect = img.getBoundingClientRect();
        const pos  = getPos(e, rect);
        const x = Math.min(start.x, pos.x);
        const y = Math.min(start.y, pos.y);
        const w = Math.abs(pos.x - start.x);
        const h = Math.abs(pos.y - start.y);
        box.style.left   = x + 'px';
        box.style.top    = y + 'px';
        box.style.width  = w + 'px';
        box.style.height = h + 'px';
        box.style.display = w > 10 && h > 10 ? 'block' : 'none';
      }

      function endCrop(e) {
        if (!dragging) return;
        dragging = false;
        if (!start) return;
        const rect = img.getBoundingClientRect();
        const clientX = e.changedTouches ? e.changedTouches[0].clientX : e.clientX;
        const clientY = e.changedTouches ? e.changedTouches[0].clientY : e.clientY;
        const cx = Math.min(Math.max(clientX - rect.left, 0), rect.width);
        const cy = Math.min(Math.max(clientY - rect.top,  0), rect.height);
        const w = Math.abs(cx - start.x);
        const h = Math.abs(cy - start.y);
        if (w > 10 && h > 10) cropRect = { x: Math.min(start.x, cx), y: Math.min(start.y, cy), w, h };
        start = null;
      }

      /* Mouse events */
      overlay.addEventListener('mousedown', startCrop);
      document.addEventListener('mousemove', moveCrop);
      document.addEventListener('mouseup',   endCrop);

      /* Touch events for mobile */
      overlay.addEventListener('touchstart', startCrop, { passive: false });
      document.addEventListener('touchmove',  moveCrop, { passive: false });
      document.addEventListener('touchend',   endCrop);
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
      const badge = cardEl.querySelector('.b-badge[class*="status"]');
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

/* ── Print helper ──────────────────────────────────────────── */
function printPage() {
  document.body.setAttribute('data-print-time', new Date().toLocaleString());
  window.print();
}