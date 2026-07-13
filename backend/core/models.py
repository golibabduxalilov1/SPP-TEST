from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=64, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor} {self.action}"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    level = models.CharField(
        max_length=16,
        choices=[("info", "info"), ("warning", "warning"), ("error", "error"), ("success", "success")],
        default="info",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict, blank=True)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


class LiveLogEvent(models.Model):
    """Lightweight feed used for the dashboard's live terminal logs panel."""

    EVENT_TYPES = [
        ("scan", "Skan"),
        ("sync", "Offline sync"),
        ("order", "Yangi buyurtma"),
        ("conflict", "Konflikt"),
        ("packaging", "Qadoqlash"),
        ("warehouse", "Ombor"),
        ("fraud", "Soxta skan bloklandi"),
    ]
    event_type = models.CharField(max_length=16, choices=EVENT_TYPES)
    message = models.CharField(max_length=255)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
