from django.db import models


class ProductType(models.Model):
    """Mahsulot turi — e.g. 'Shkaf A12', 'Stol B5'."""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductTypeDetail(models.Model):
    """Standart detal — a template detail row belonging to a ProductType."""

    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name="details")
    name = models.CharField(max_length=200)
    length_mm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    width_mm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    thickness_mm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    material_type = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.product_type.name})"


class Material(models.Model):
    """Reusable material catalog (panels, edge bands, linear stock, ...).

    `code` is deliberately NOT globally unique: source systems such as
    GibLab reuse the same code for visually different materials (e.g. a
    regular and an oval edge band sharing one code). Identity/deduplication
    for imported rows is instead `(source_system, external_id, category)`.
    """

    class Category(models.TextChoices):
        PANEL = "panel", "Plita"
        EDGE_BAND = "edge_band", "Kromka"
        LINEAR = "linear", "Chiziqli material"
        ACCESSORY = "accessory", "Furnitura"
        OTHER = "other", "Boshqa"

    code = models.CharField(max_length=64, blank=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.OTHER)
    length_mm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    width_mm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    thickness_mm = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    unit = models.CharField(max_length=16, blank=True)
    source_system = models.CharField(max_length=32, blank=True)
    external_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_system", "external_id", "category"],
                name="unique_material_source_identity",
                condition=~models.Q(source_system="") & ~models.Q(external_id=""),
            ),
        ]
        indexes = [
            models.Index(fields=["source_system", "external_id"]),
        ]

    def __str__(self):
        return self.name
