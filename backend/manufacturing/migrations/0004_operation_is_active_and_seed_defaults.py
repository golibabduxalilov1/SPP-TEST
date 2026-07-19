from django.db import migrations, models


DEFAULT_OPERATIONS = [
    {"code": "ARRA", "name": "Arra", "measure_unit": "m2", "qr_scan_required": True, "order_index": 1},
    {"code": "KROMKA", "name": "Kromka", "measure_unit": "meter", "qr_scan_required": True, "order_index": 2},
    {"code": "PRISADKA", "name": "Prisadka", "measure_unit": "piece", "qr_scan_required": True, "order_index": 3},
    {"code": "PAZ", "name": "Paz", "measure_unit": "meter", "qr_scan_required": False, "order_index": 4},
    {"code": "ROVER", "name": "Rover/CNC", "measure_unit": "meter", "qr_scan_required": False, "order_index": 5},
    {"code": "STOLYARKA", "name": "Stolyarka", "measure_unit": "piece", "qr_scan_required": False, "order_index": 6},
    {"code": "YIGISH", "name": "Yig'ish", "measure_unit": "piece", "qr_scan_required": True, "order_index": 7},
    {"code": "QADOQLASH", "name": "Qadoqlash", "measure_unit": "package", "qr_scan_required": True, "order_index": 8},
    {"code": "OMBOR", "name": "Tayyor ombor", "measure_unit": "package", "qr_scan_required": True, "order_index": 9},
]


def seed_default_operations(apps, schema_editor):
    Operation = apps.get_model("manufacturing", "Operation")
    for defaults in DEFAULT_OPERATIONS:
        values = defaults.copy()
        code = values.pop("code")
        Operation.objects.get_or_create(code=code, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("manufacturing", "0003_remove_factory"),
    ]

    operations = [
        migrations.AddField(
            model_name="operation",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterModelOptions(
            name="operation",
            options={"ordering": ["order_index", "id"]},
        ),
        migrations.RunPython(seed_default_operations, migrations.RunPython.noop),
    ]
