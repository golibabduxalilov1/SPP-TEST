import random
import string

from django.conf import settings
from django.core.validators import MinValueValidator
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
        NORMAL = "normal", "Oddiy"
        HIGH = "high", "Yuqori"
        URGENT = "urgent", "Shoshilinch"

    order_no = models.CharField(max_length=32, unique=True, default=generate_order_no)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)
    product_name = models.CharField(max_length=200, blank=True)
    product_quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
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
    material_ref = models.ForeignKey(
        "catalog.Material",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parts",
    )
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

    Entered manually (or produced as an Order snapshot from a GibLab import)
    and edited independently thereafter.
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


class BOM(models.Model):
    """Product specification/recipe — what makes up one unit of a Product.

    Orthogonal to `OrderDetail`: GibLab-imported orders get Parts + a BOM
    directly (no OrderDetail rows), keeping them on the legacy "Parts" board
    path in core.tablo (see project plan for why mixing the two would
    double-count quantity/area/edge).
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="boms")
    version = models.PositiveIntegerField(default=1)
    source_system = models.CharField(max_length=32, blank=True)
    source_project_uuid = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product", "version"]
        unique_together = ["product", "version"]

    def __str__(self):
        return f"BOM {self.product.name} v{self.version}"


class BOMItem(models.Model):
    class ItemType(models.TextChoices):
        PART = "part", "Detal"
        MATERIAL = "material", "Material"
        EDGE_BAND = "edge_band", "Kromka"

    class EdgeSide(models.TextChoices):
        TOP = "top", "Yuqori"
        BOTTOM = "bottom", "Past"
        LEFT = "left", "Chap"
        RIGHT = "right", "O'ng"

    bom = models.ForeignKey(BOM, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=16, choices=ItemType.choices)
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE, related_name="bom_items", null=True, blank=True
    )
    material = models.ForeignKey(
        "catalog.Material", on_delete=models.PROTECT, related_name="bom_items", null=True, blank=True
    )
    target_part = models.ForeignKey(
        Part, on_delete=models.CASCADE, related_name="bom_edge_items", null=True, blank=True,
        help_text="For EDGE_BAND rows: which part this edge belongs to.",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    unit = models.CharField(max_length=16, blank=True)
    edge_side = models.CharField(max_length=16, choices=EdgeSide.choices, null=True, blank=True)
    source_external_id = models.CharField(max_length=64, blank=True)
    sequence_index = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["bom", "sequence_index", "id"]
        indexes = [models.Index(fields=["bom", "item_type"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(item_type="edge_band", edge_side__isnull=False)
                    | (~models.Q(item_type="edge_band") & models.Q(edge_side__isnull=True))
                ),
                name="bomitem_edge_side_iff_edge_band",
            ),
        ]

    def __str__(self):
        return f"{self.bom} #{self.sequence_index} ({self.item_type})"


class GibLabImportBatch(models.Model):
    """Import history/idempotency record for GibLab `.project` file imports."""

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Yuklandi"
        VALIDATED = "validated", "Tekshirildi"
        IMPORTING = "importing", "Import qilinmoqda"
        COMPLETED = "completed", "Yakunlandi"
        FAILED = "failed", "Xatolik"

    source_system = models.CharField(max_length=32, default="giblab")
    original_filename = models.CharField(max_length=255, blank=True)
    file_checksum = models.CharField(max_length=64, unique=True)
    project_uuid = models.CharField(max_length=64, blank=True)
    file_version = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADED)
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="giblab_import_batches"
    )
    statistics = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"GibLabImportBatch #{self.pk} ({self.status})"
