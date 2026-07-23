from django.db import models


class Operation(models.Model):

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    measure_unit = models.CharField(
        max_length=16,
        choices=[
            ("m2", "m²"),
            ("meter", "metr"),
            ("piece", "dona"),
            ("package", "qadoq"),
        ],
    )
    qr_scan_required = models.BooleanField(default=True)
    order_index = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order_index", "id"]

    def __str__(self):
        return self.name


class Tsex(models.Model):
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Device(models.Model):
    device_id = models.CharField(max_length=128, unique=True)
    tsex = models.ForeignKey(
        Tsex, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices"
    )
    label = models.CharField(max_length=150, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    offline_ready = models.BooleanField(default=False)

    def __str__(self):
        return self.device_id


class Printer(models.Model):
    name = models.CharField(max_length=150)
    tsex = models.ForeignKey(
        Tsex, on_delete=models.SET_NULL, null=True, blank=True, related_name="printers"
    )
    label_width_mm = models.PositiveSmallIntegerField(default=70)
    label_height_mm = models.PositiveSmallIntegerField(default=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Machine(models.Model):
    STATUS_CHOICES = [
        ("active", "Ishlayapti"),
        ("inactive", "Nofaol"),
        ("maintenance", "Ta'mirda"),
        ("broken", "Buzilgan"),
    ]
    machine_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=150)
    operation = models.ForeignKey(
        Operation, on_delete=models.PROTECT, related_name="machines"
    )
    tsex = models.ForeignKey(Tsex, on_delete=models.CASCADE, related_name="machines")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    terminal_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="machines",
    )
    printer = models.ForeignKey(
        Printer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="machines",
    )
    capacity_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Soatiga rejalashtirilgan quvvat (operatsiya birligida: m2/metr/dona)",
    )

    def __str__(self):
        return f"{self.machine_id} {self.name}"
