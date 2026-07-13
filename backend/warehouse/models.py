from django.conf import settings
from django.db import models


class WarehouseEvent(models.Model):
    class EventType(models.TextChoices):
        RECEIVE = "receive", "Qabul qilindi"
        DELIVER = "deliver", "Topshirildi"

    package = models.ForeignKey("packaging.Package", on_delete=models.CASCADE, related_name="warehouse_events")
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.package.package_no} — {self.event_type}"
