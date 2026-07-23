import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^\+998\d{9}$",
    message="Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak.",
)

pin_code_validator = RegexValidator(
    regex=r"^[0-9]{4}$",
    message="PIN kod aynan 4 ta raqamdan iborat bo'lishi kerak.",
)


class Role(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Admin"
    DIRECTOR = "director", "Rahbar"
    MANAGER = "manager", "Ishlab chiqarish menejeri"
    OPERATOR = "operator", "Operator / Usta"
    WAREHOUSE = "warehouse", "Omborchi"


# Roles allowed to use the terminal (PIN/QR-badge based session, not the admin panel).
TERMINAL_ROLES = {Role.OPERATOR, Role.WAREHOUSE}

# Roles allowed to use the admin/web panel.
ADMIN_ROLES = {
    Role.SUPER_ADMIN,
    Role.ADMIN,
    Role.DIRECTOR,
    Role.MANAGER,
}

# Roles with the same overall privilege level as Super Admin (is_staff/is_superuser),
# except Admin may not create or promote another user to Super Admin (see UserViewSet).
SUPER_ADMIN_LEVEL_ROLES = {Role.SUPER_ADMIN, Role.ADMIN}


class UserManager(DjangoUserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        # `python manage.py createsuperuser` must always produce a Super Admin —
        # never leave it at the model's default role (Operator / Usta).
        extra_fields["role"] = Role.SUPER_ADMIN
        return super().create_superuser(username=username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)
    phone = models.CharField(max_length=17, unique=True, validators=[phone_validator])
    pin_code = models.CharField(
        max_length=4, blank=True, null=True, unique=True,
        validators=[pin_code_validator], help_text="Terminal PIN kodi (4 ta raqam)",
    )
    badge_token = models.CharField(max_length=64, blank=True, unique=False, help_text="QR badge token")
    is_active_employee = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Ishlab chiqarish bo'limi ("Tsex") — Operator/Usta uchun majburiy, Ishlab
    # chiqarish menejeri uchun ixtiyoriy, qolgan rollar uchun ishlatilmaydi.
    department = models.ForeignKey(
        "manufacturing.Tsex", on_delete=models.SET_NULL, null=True, blank=True, related_name="employees"
    )

    # Terminal quick-login (PIN) stage assignment — off by default (single stage).
    multi_stage_enabled = models.BooleanField(default=False)
    assigned_operation = models.ForeignKey(
        "manufacturing.Operation", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    assigned_operations = models.ManyToManyField(
        "manufacturing.Operation", blank=True, related_name="+"
    )
    # The exact machine(s) ("stanok") this employee works on within their
    # assigned stage(s) — always multi, independent of multi_stage_enabled.
    assigned_machines = models.ManyToManyField(
        "manufacturing.Machine", blank=True, related_name="+"
    )

    def __str__(self):
        return f"{self.get_full_name() or self.phone} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.pk:
            # A Super Admin's role can never be changed away from Super Admin,
            # through any code path (admin panel, API, shell) — it's a one-way promotion.
            previous_role = User.objects.filter(pk=self.pk).values_list("role", flat=True).first()
            if previous_role == Role.SUPER_ADMIN:
                self.role = Role.SUPER_ADMIN
        if self.role in SUPER_ADMIN_LEVEL_ROLES:
            self.is_staff = True
            self.is_superuser = True
        if not self.username:
            self.username = self.phone
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
    operation = models.ForeignKey(
        "manufacturing.Operation", on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions"
    )
    device_id = models.CharField(max_length=128)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.employee} @ {self.device_id}"
