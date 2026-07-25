from django.db import migrations

_DEFAULT_SHIFTS = ["1-smena", "2-smena", "3-smena"]


def seed_shifts(apps, schema_editor):
    Shift = apps.get_model("manufacturing", "Shift")
    if Shift.objects.exists():
        return
    for name in _DEFAULT_SHIFTS:
        Shift.objects.create(name=name, is_active=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('manufacturing', '0002_shift'),
    ]

    operations = [
        migrations.RunPython(seed_shifts, noop_reverse),
    ]
