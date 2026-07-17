from django.db import migrations


def backfill_phone(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    seen = set(User.objects.exclude(phone="").values_list("phone", flat=True))

    for index, user in enumerate(User.objects.filter(phone="").order_by("id"), start=1):
        candidate = f"+998700000{index:03d}"
        while candidate in seen:
            index += 1
            candidate = f"+998700000{index:03d}"
        seen.add(candidate)
        user.phone = candidate
        user.save(update_fields=["phone"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_phone, noop_reverse),
    ]
