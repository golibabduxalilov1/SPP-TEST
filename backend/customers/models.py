from django.db import models


class Customer(models.Model):
    """Mijoz — identified by phone number so repeat orders can be linked automatically."""

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32, unique=True)
    address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.phone})"
