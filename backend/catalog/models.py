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
