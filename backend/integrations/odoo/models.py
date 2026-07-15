from django.db import models


class SyncLog(models.Model):
    """One row per Odoo polling attempt. SPP-only bookkeeping — never sent to Odoo."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Muvaffaqiyatli"
        FAILED = "failed", "Muvaffaqiyatsiz"

    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    orders_imported_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.status} ({self.orders_imported_count})"
