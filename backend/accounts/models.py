import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    DIRECTOR = "director", "Rahbar / Direktor"
    MANAGER = "manager", "Ishlab chiqarish menejeri"
    MASTER = "master", "Master / Tsex boshlig'i"
    TECHNOLOGIST = "technologist", "Texnolog / Konstruktor"
    OPERATOR = "operator", "Operator / Usta"
    PACKAGING = "packaging", "Qadoqlash operatori"
    WAREHOUSE = "warehouse", "Omborchi"
    SYSADMIN = "sysadmin", "Tizim administratori"


# Roles allowed to use the terminal (PIN/QR-badge based session, not the admin panel).
TERMINAL_ROLES = {Role.MASTER, Role.OPERATOR, Role.PACKAGING, Role.WAREHOUSE}

# Roles allowed to use the admin/web panel.
ADMIN_ROLES = {
    Role.SUPER_ADMIN,
    Role.DIRECTOR,
    Role.MANAGER,
    Role.MASTER,
    Role.TECHNOLOGIST,
    Role.SYSADMIN,
}


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)
    phone = models.CharField(max_length=32, blank=True)
    pin_code = models.CharField(max_length=8, blank=True, help_text="Terminal PIN kodi")
    badge_token = models.CharField(max_length=64, blank=True, unique=False, help_text="QR badge token")
    is_active_employee = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.role == Role.SUPER_ADMIN:
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    @property
    def can_use_terminal(self):
        return self.role in TERMINAL_ROLES

    @property
    def can_use_admin(self):
        return self.is_superuser or self.role in ADMIN_ROLES


class TerminalSession(models.Model):
    """A terminal (PWA) login session for an operator/master/packaging/warehouse employee."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="terminal_sessions")
    workstation = models.ForeignKey(
        "manufacturing.Workstation", on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions"
    )
    device_id = models.CharField(max_length=128)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.employee} @ {self.device_id}"
