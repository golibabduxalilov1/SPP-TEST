import random

from django.conf import settings
from django.db import models


def generate_package_no():
    from django.utils import timezone

    return f"PKG-{timezone.now():%y%m%d}-{random.randint(1000, 9999)}"


class Package(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Ochiq"
        COMPLETED = "completed", "Yakunlangan"
        WAREHOUSE = "warehouse", "Omborda"
        DELIVERED = "delivered", "Topshirildi"

    package_no = models.CharField(max_length=32, unique=True, default=generate_package_no)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="packages")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    qr_token = models.CharField(max_length=64, unique=True, default=generate_package_no)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.package_no


class PackageItem(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="items")
    part = models.ForeignKey("orders.Part", on_delete=models.CASCADE, related_name="package_items")
    scanned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["package", "part"]
