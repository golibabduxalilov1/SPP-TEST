from django.conf import settings
from django.db import models


class ScanEvent(models.Model):
    class Source(models.TextChoices):
        ONLINE = "online", "Tarmoqda"
        OFFLINE_SYNC = "offline_sync", "Oflayn sinxronizatsiya"

    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Qabul qilindi"
        REJECTED = "rejected", "Rad etildi"
        CONFLICT = "conflict", "Muammoli holat"

    client_scan_id = models.CharField(max_length=128, unique=True)
    qr_token = models.CharField(max_length=64)
    part = models.ForeignKey("orders.Part", on_delete=models.SET_NULL, null=True, blank=True, related_name="scan_events")
    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="scan_events")
    operation = models.ForeignKey("manufacturing.Operation", on_delete=models.SET_NULL, null=True, blank=True)
    machine = models.ForeignKey("manufacturing.Machine", on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    device_id = models.CharField(max_length=128, blank=True)
    scanned_at_client = models.DateTimeField(null=True, blank=True)
    received_at_server = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.ONLINE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACCEPTED)
    error_code = models.CharField(max_length=32, blank=True)
    batch = models.ForeignKey("OfflineSyncBatch", on_delete=models.SET_NULL, null=True, blank=True, related_name="scans")

    class Meta:
        ordering = ["-received_at_server"]

    def __str__(self):
        return f"{self.qr_token} [{self.status}]"


class OfflineSyncBatch(models.Model):
    client_batch_id = models.CharField(max_length=128, unique=True)
    device_id = models.CharField(max_length=128)
    operation = models.ForeignKey("manufacturing.Operation", on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    accepted_count = models.PositiveIntegerField(default=0)
    conflict_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-received_at"]


class Conflict(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        RESOLVED = "resolved", "Hal qilingan"

    scan_event = models.OneToOneField(ScanEvent, on_delete=models.CASCADE, related_name="conflict")
    reason_code = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.CharField(
        max_length=16,
        choices=[("accepted", "Qabul qilindi"), ("rejected", "Rad qilindi"), ("requeued", "Qayta ishlashga yuborildi")],
        blank=True,
    )
    resolution_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
