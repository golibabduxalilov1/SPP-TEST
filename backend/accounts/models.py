import uuid

from django.contrib.auth.hashers import check_password
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


class EmploymentStatus(models.TextChoices):
    ACTIVE = "faol", "Faol"
    VACATION = "vacation", "Ta'til"
    SICK = "sick", "Kasallik"
    TERMINATED = "terminated", "Bo'shatilgan"


class Specialization(models.TextChoices):
    OPERATOR = "operator", "Operator"
    MASTER = "master", "Usta"
    ADJUSTER = "adjuster", "Sozlovchi"
    WELDER = "welder", "Payvandchi"
    CUTTER = "cutter", "Kesuvchi"
    ASSEMBLER = "assembler", "Yig'uvchi"
    PACKER = "packer", "Qadoqlovchi"
    OTHER = "other", "Boshqa"


# Roles allowed to use the terminal (PIN/QR-badge based session, not the admin panel).
# Ishlab chiqarish menejeri terminaldan foydalanishi ixtiyoriy, lekin ruxsat etilgan.
TERMINAL_ROLES = {Role.OPERATOR, Role.WAREHOUSE, Role.MANAGER}

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

# Roles that must never carry a terminal PIN, and must supply a password
# (admin-panel login) when created — they only ever log in with phone+password.
NO_PIN_ROLES = {Role.SUPER_ADMIN, Role.ADMIN, Role.DIRECTOR}


class UserManager(DjangoUserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        # `python manage.py createsuperuser` must always produce a Super Admin —
        # never leave it at the model's default role (Operator / Usta).
        extra_fields["role"] = Role.SUPER_ADMIN
        return super().create_superuser(username=username, email=email, password=password, **extra_fields)

    def get_by_pin(self, pin_code):
        """Identifies an active employee by raw PIN — pin_code_hash is salted, so
        this can't be a DB filter; it checks the hash of each candidate instead.
        Terminal login only ever runs this for a handful of active employees."""
        if not pin_code:
            return None
        candidates = self.filter(is_active_employee=True, pin_code_hash__isnull=False).exclude(pin_code_hash="")
        for candidate in candidates:
            if check_password(pin_code, candidate.pin_code_hash):
                return candidate
        return None


class User(AbstractUser):
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)
    phone = models.CharField(max_length=17, unique=True, validators=[phone_validator])
    pin_code_hash = models.CharField(
        max_length=128, blank=True, null=True, help_text="Terminal PIN kodining xavfsiz hashi",
    )
    badge_token = models.CharField(max_length=64, blank=True, unique=False, help_text="QR badge token")
    is_active_employee = models.BooleanField(default=True)
    employment_status = models.CharField(
        max_length=16, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Ishlab chiqarish bo'limi ("Tsex") — Operator/Usta uchun majburiy, qolgan
    # rollar uchun ishlatilmaydi (Ishlab chiqarish menejeri uchun `managed_departments`ga qarang).
    department = models.ForeignKey(
        "manufacturing.Tsex", on_delete=models.SET_NULL, null=True, blank=True, related_name="employees"
    )
    # Ishlab chiqarish menejeriga biriktirilgan (bir yoki bir nechta) tsexlar —
    # faqat ma'lumot sifatida saqlanadi, boshqa bo'limlarni cheklamaydi.
    managed_departments = models.ManyToManyField(
        "manufacturing.Tsex", blank=True, related_name="managers"
    )

    # Terminal quick-login (PIN) stage assignment — off by default (single stage).
    multi_stage_enabled = models.BooleanField(default=False)
    assigned_operation = models.ForeignKey(
        "manufacturing.Operation", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    assigned_operations = models.ManyToManyField(
        "manufacturing.Operation", blank=True, related_name="+"
    )
    # The exact machine(s) ("stanok") this employee works on, scoped per
    # stage via EmployeeStageMachine (through model) — each stage the
    # employee is assigned to has its own independent machine list. Never
    # call .set()/.add() on this manager from serializer code (the through
    # model has a required `stage` field incompatible with those methods) —
    # write EmployeeStageMachine rows directly instead.
    assigned_machines = models.ManyToManyField(
        "manufacturing.Machine", through="accounts.EmployeeStageMachine", blank=True, related_name="+"
    )

    specialization = models.CharField(max_length=16, choices=Specialization.choices, blank=True, null=True)

    # Omborchi terminaldan foydalanadimi — shunga qarab PIN majburiy bo'ladi.
    uses_terminal = models.BooleanField(default=False)

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
        # Ta'til/kasallik/bo'shatilgan holatidagi xodim hech qanday yo'l bilan
        # (admin panel, API, shell) faol deb belgilanmasin — terminal va boshqa
        # tekshiruvlar shu bittagina bayroqqa (is_active_employee) tayanadi.
        if self.employment_status != EmploymentStatus.ACTIVE:
            self.is_active_employee = False
        super().save(*args, **kwargs)

    @property
    def can_use_terminal(self):
        return self.role in TERMINAL_ROLES

    @property
    def can_use_admin(self):
        if self.is_superuser or self.role in ADMIN_ROLES:
            return True
        # Omborchi terminaldan foydalanmasa, login/parol orqali kira oladi.
        return self.role == Role.WAREHOUSE and not self.uses_terminal


class EmployeeStageMachine(models.Model):
    """One (employee, machine) work assignment — the through model behind
    User.assigned_machines. `stage` mirrors `machine.operation_id` (every
    Machine has a required, fixed operation) so per-stage machine lists can
    be queried directly without joining through Machine, but it must never
    be set independently of the machine it's attached to — all writes go
    through UserSerializer's diff-sync (bulk_create/delete), never .set()/
    .add() (blocked by the required `stage` field) or a hand-picked stage."""

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stage_machine_links")
    stage = models.ForeignKey("manufacturing.Operation", on_delete=models.CASCADE, related_name="+")
    machine = models.ForeignKey("manufacturing.Machine", on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "machine"], name="unique_employee_machine"),
        ]

    def save(self, *args, **kwargs):
        self.stage_id = self.machine.operation_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} @ {self.machine} ({self.stage})"


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
