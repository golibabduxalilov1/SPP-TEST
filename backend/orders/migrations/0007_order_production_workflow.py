import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def start_existing_active_orders(apps, schema_editor):
    """Backfill current_stage for orders that predate this feature.

    Rather than parking every pre-existing active order on the very first
    stage (wrong and confusing for orders already deep into production),
    walk each order's actual PartRoute completion to land on the first
    active stage it's genuinely still waiting on.
    """

    Operation = apps.get_model("manufacturing", "Operation")
    Order = apps.get_model("orders", "Order")
    OrderStageProgress = apps.get_model("orders", "OrderStageProgress")
    Part = apps.get_model("orders", "Part")
    PartRoute = apps.get_model("orders", "PartRoute")

    active_stages = list(Operation.objects.filter(is_active=True).order_by("order_index", "id"))
    if not active_stages:
        return

    active_statuses = [
        "approved", "in_production", "partially_ready", "ready_for_packaging", "packaging", "warehouse",
    ]
    for order in Order.objects.filter(status__in=active_statuses, current_stage__isnull=True).iterator():
        has_parts = Part.objects.filter(order=order).exists()
        stage_for_order = None
        for stage in active_stages:
            routes_here = PartRoute.objects.filter(part__order=order, operation=stage)
            if has_parts and not routes_here.exists():
                continue  # none of this order's parts pass through this stage at all
            if has_parts and not routes_here.exclude(status__in=["completed", "not_required"]).exists():
                continue  # every part already finished this stage — it's not the current one
            stage_for_order = stage
            break

        # Every relevant stage already scanned complete (or no parts to check
        # against) — park it on the last active stage so it still shows up
        # and can be moved to "completed" normally instead of being skipped.
        if stage_for_order is None:
            stage_for_order = active_stages[-1]

        order.current_stage = stage_for_order
        order.stage_status = "in_progress"
        order.save(update_fields=["current_stage", "stage_status"])
        OrderStageProgress.objects.get_or_create(
            order=order,
            stage=stage_for_order,
            defaults={"status": "in_progress"},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("manufacturing", "0004_operation_is_active_and_seed_defaults"),
        ("orders", "0006_orderdetail_part"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Yangi"),
                    ("approved", "Tasdiqlangan"),
                    ("in_production", "Tsexda ishlab chiqarilmoqda"),
                    ("partially_ready", "Qisman tayyor"),
                    ("ready_for_packaging", "Qadoqlashga tayyor"),
                    ("packaging", "Qadoqlanmoqda"),
                    ("warehouse", "Tayyor omborda"),
                    ("completed", "Tugallangan"),
                    ("delivered", "Mijozga topshirildi"),
                    ("cancelled", "Bekor qilingan"),
                ],
                default="draft",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="current_stage",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="current_orders",
                to="manufacturing.operation",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="stage_status",
            field=models.CharField(
                choices=[
                    ("not_started", "Boshlanmagan"),
                    ("in_progress", "Jarayonda"),
                    ("completed", "Bajarilgan"),
                ],
                default="not_started",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="OrderStageProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[("in_progress", "Jarayonda"), ("completed", "Bajarilgan")],
                        default="in_progress",
                        max_length=16,
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="completed_order_stages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stage_progress",
                        to="orders.order",
                    ),
                ),
                (
                    "stage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_stage_progress",
                        to="manufacturing.operation",
                    ),
                ),
            ],
            options={
                "ordering": ["started_at", "id"],
                "unique_together": {("order", "stage")},
            },
        ),
        migrations.RunPython(start_existing_active_orders, migrations.RunPython.noop),
    ]
