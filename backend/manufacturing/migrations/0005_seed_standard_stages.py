from django.db import migrations

from orders.constants import OPERATION_SEEDS, STANDARD_OPERATION_CODES

LEGACY_OMBOR_CODE = "OMBOR"
QADOQLASH_CODE = "QADOQLASH"


def _remap_fk(model, fk_field, unique_together_fields, old_id, new_id):
    """Point every row's `fk_field` at `new_id` instead of `old_id`.

    For models with a unique_together constraint spanning `fk_field`, a row
    can't be repointed if the same "other" value already has a row on
    `new_id` (that would collide) — those rows are left on `old_id` so no
    history is lost or silently duplicated; the old stage stays in the
    database (deactivated) to keep them valid.
    """
    queryset = model.objects.filter(**{fk_field: old_id})
    if not unique_together_fields:
        queryset.update(**{fk_field: new_id})
        return

    other_field = next(f for f in unique_together_fields if f != fk_field)
    taken = set(
        model.objects.filter(**{fk_field: new_id}).values_list(other_field, flat=True)
    )
    for row in queryset:
        other_value = getattr(row, f"{other_field}_id", getattr(row, other_field))
        if other_value in taken:
            continue
        setattr(row, fk_field, new_id)
        row.save(update_fields=[fk_field])
        taken.add(other_value)


def seed_standard_stages(apps, schema_editor):
    Operation = apps.get_model("manufacturing", "Operation")
    Machine = apps.get_model("manufacturing", "Machine")
    Order = apps.get_model("orders", "Order")
    Part = apps.get_model("orders", "Part")
    PartRoute = apps.get_model("orders", "PartRoute")
    OrderStageProgress = apps.get_model("orders", "OrderStageProgress")

    for seed in OPERATION_SEEDS:
        Operation.objects.update_or_create(
            code=seed["code"],
            defaults={
                "name": seed["name"],
                "measure_unit": seed["measure_unit"],
                "qr_scan_required": seed["qr_scan_required"],
                "order_index": seed["order_index"],
                "is_active": True,
            },
        )

    ombor = Operation.objects.filter(code=LEGACY_OMBOR_CODE).first()
    qadoqlash = Operation.objects.filter(code=QADOQLASH_CODE).first()
    if ombor and qadoqlash and ombor.id != qadoqlash.id:
        _remap_fk(PartRoute, "operation_id", ["part_id", "operation_id"], ombor.id, qadoqlash.id)
        _remap_fk(OrderStageProgress, "stage_id", ["order_id", "stage_id"], ombor.id, qadoqlash.id)
        Part.objects.filter(current_operation_id=ombor.id).update(current_operation_id=qadoqlash.id)
        Order.objects.filter(current_stage_id=ombor.id).update(current_stage_id=qadoqlash.id)
        Machine.objects.filter(operation_id=ombor.id).update(operation_id=qadoqlash.id)

    # Any stage outside the 13 standard codes (custom/admin-created stages,
    # and the now-superseded OMBOR) is deactivated but kept in the database —
    # its historical PartRoute/OrderStageProgress/Machine rows stay valid, it
    # just no longer appears in new routes, the terminal, or the admin list.
    Operation.objects.exclude(code__in=STANDARD_OPERATION_CODES).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("manufacturing", "0004_delete_shift"),
        ("orders", "0004_normalize_priority_choices"),
    ]

    operations = [
        migrations.RunPython(seed_standard_stages, migrations.RunPython.noop),
    ]
