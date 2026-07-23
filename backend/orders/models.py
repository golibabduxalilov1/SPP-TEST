import random
import string

from django.conf import settings
from django.db import models


def generate_order_no():
    from django.utils import timezone

    return f"{timezone.now():%y%m}-{random.randint(1000, 9999)}"


def generate_qr_token():
    chars = string.ascii_uppercase + string.digits
    return "SPP-P-" + "".join(random.choices(chars, k=6))


def generate_order_qr_token():
    chars = string.ascii_uppercase + string.digits
    return "SPP-O-" + "".join(random.choices(chars, k=6))


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Yangi"
        APPROVED = "approved", "Tasdiqlangan"
        IN_PRODUCTION = "in_production", "Jarayonda"
        PARTIALLY_READY = "partially_ready", "Qisman tayyor"
        WAREHOUSE = "warehouse", "Tayyor omborda"
        COMPLETED = "completed", "Tugallangan"
        DELIVERED = "delivered", "Mijozga topshirildi"
        CANCELLED = "cancelled", "Bekor qilingan"

    class StageStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Boshlanmagan"
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Bajarilgan"

    class Priority(models.TextChoices):
        LOW = "low", "Past"
        NORMAL = "normal", "Oddiy"
        HIGH = "high", "Yuqori"
        URGENT = "urgent", "Shoshilinch"

    order_no = models.CharField(max_length=32, unique=True, default=generate_order_no)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)
    product_name = models.CharField(max_length=200, blank=True)
    product_type = models.ForeignKey(
        "catalog.ProductType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    notes = models.TextField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.DRAFT
    )
    current_stage = models.ForeignKey(
        "manufacturing.Operation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_orders",
    )
    stage_status = models.CharField(
        max_length=16,
        choices=StageStatus.choices,
        default=StageStatus.NOT_STARTED,
    )
    qr_token = models.CharField(
        max_length=64, unique=True, default=generate_order_qr_token, blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.order_no} {self.product_name}"

    def recalculate_status(self):
        """Auto-derive order status from part completion, per spec section 5.4."""
        if self.status in (
            self.Status.CANCELLED,
            self.Status.COMPLETED,
            self.Status.DELIVERED,
        ):
            return
        parts = list(self.parts.all())
        if not parts:
            return
        statuses = {p.status for p in parts}
        if statuses == {"completed"}:
            new_status = self.Status.WAREHOUSE
        elif "completed" in statuses or "in_progress" in statuses:
            new_status = self.Status.PARTIALLY_READY
        elif statuses == {"pending"}:
            new_status = (
                self.Status.IN_PRODUCTION
                if self.status != self.Status.DRAFT
                else self.status
            )
        else:
            new_status = self.status
        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class OrderStageProgress(models.Model):
    """Order-level production history.

    Detail routes remain available to the QR/terminal workflow, while this
    model records the deliberately simpler whole-order production flow used
    by the production board.
    """

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Bajarilgan"

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="stage_progress"
    )
    stage = models.ForeignKey(
        "manufacturing.Operation",
        on_delete=models.PROTECT,
        related_name="order_stage_progress",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.IN_PROGRESS
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_order_stages",
    )

    class Meta:
        ordering = ["started_at", "id"]
        unique_together = ["order", "stage"]

    def __str__(self):
        return f"{self.order.order_no} -> {self.stage.name} ({self.status})"


class Product(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Part(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Tayyor"
        BLOCKED = "blocked", "Bloklangan"
        CONFLICT = "conflict", "Muammoli holat"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="parts")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="parts", null=True, blank=True
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    material = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)
    length_mm = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    width_mm = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    thickness_mm = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)
    area_m2 = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    edge_meter = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    drilling_count = models.PositiveIntegerField(default=0)
    qr_token = models.CharField(max_length=64, unique=True, default=generate_qr_token)
    current_operation = models.ForeignKey(
        "manufacturing.Operation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_parts",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def next_route_step(self):
        return (
            self.routes.filter(status__in=["pending", "blocked"])
            .order_by("sequence_index")
            .first()
        )


class PartRoute(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        IN_PROGRESS = "in_progress", "Jarayonda"
        COMPLETED = "completed", "Bajarildi"
        BLOCKED = "blocked", "Bloklangan"
        NOT_REQUIRED = "not_required", "Kerak emas"

    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="routes")
    operation = models.ForeignKey(
        "manufacturing.Operation", on_delete=models.PROTECT, related_name="part_routes"
    )
    sequence_index = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    machine = models.ForeignKey(
        "manufacturing.Machine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="part_routes",
    )

    class Meta:
        ordering = ["part", "sequence_index"]
        unique_together = ["part", "operation"]

    def __str__(self):
        return f"{self.part.code} -> {self.operation.code}"


class OrderDetail(models.Model):
    """Buyurtma detali — a concrete detail row belonging to one Order.

    Populated as an independent copy from the chosen ProductType's
    ProductTypeDetail rows at order-creation time (not FK-linked), so later
    edits to the standard template or to this row never affect the other.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="details")
    name = models.CharField(max_length=200)
    length_mm = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    width_mm = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    thickness_mm = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)
    material_type = models.CharField(max_length=100, blank=True)
    part = models.OneToOneField(
        Part,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_detail",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.order.order_no})"


class Label(models.Model):
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE, related_name="labels", null=True, blank=True
    )
    package = models.ForeignKey(
        "packaging.Package",
        on_delete=models.CASCADE,
        related_name="labels",
        null=True,
        blank=True,
    )
    printed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    printed_at = models.DateTimeField(auto_now_add=True)
    label_width_mm = models.PositiveSmallIntegerField(default=70)
    label_height_mm = models.PositiveSmallIntegerField(default=50)

    class Meta:
        ordering = ["-printed_at"]
