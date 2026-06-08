from django.db import models
from django.utils import timezone


class Camera(models.Model):
    STATUS_CHOICES = [
        ('online',  'Online'),
        ('offline', 'Offline'),
        ('unknown', 'Unknown'),
    ]

    name         = models.CharField(max_length=100)
    index_or_url = models.CharField(max_length=255)
    location     = models.CharField(max_length=255)
    description  = models.TextField(blank=True, default='')
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unknown')
    is_active    = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    went_offline_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    # ── Map coordinates (optional — null if not set) ──────────────────────────
    latitude     = models.FloatField(null=True, blank=True)
    longitude    = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} [{self.index_or_url}] — {self.status}"

    def mark_online(self):
        self.status = 'online'
        self.last_seen_at = timezone.now()
        self.went_offline_at = None
        self.save(update_fields=['status', 'last_seen_at', 'went_offline_at'])

    def mark_offline(self):
        if self.status != 'offline':
            self.status = 'offline'
            self.went_offline_at = timezone.now()
            self.save(update_fields=['status', 'went_offline_at'])