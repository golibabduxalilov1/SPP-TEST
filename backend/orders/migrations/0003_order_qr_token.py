from django.db import migrations, models

import orders.models


def backfill_qr_tokens(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    seen = set(Order.objects.exclude(qr_token="").values_list("qr_token", flat=True))
    for order in Order.objects.filter(qr_token=""):
        token = orders.models.generate_order_qr_token()
        while token in seen:
            token = orders.models.generate_order_qr_token()
        seen.add(token)
        order.qr_token = token
        order.save(update_fields=["qr_token"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_initial"),
    ]

    operations = [
        # Step 1: add as a plain, non-unique field so existing rows don't all
        # collide on the same default value (a callable default is evaluated
        # once for the whole ALTER TABLE, not per row).
        migrations.AddField(
            model_name="order",
            name="qr_token",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        # Step 2: backfill a unique token per existing row.
        migrations.RunPython(backfill_qr_tokens, noop_reverse),
        # Step 3: now that every row has a unique value, enforce it and switch
        # the default to the generator for future inserts.
        migrations.AlterField(
            model_name="order",
            name="qr_token",
            field=models.CharField(blank=True, default=orders.models.generate_order_qr_token, max_length=64, unique=True),
        ),
    ]
