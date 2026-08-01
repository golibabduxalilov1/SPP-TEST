import uuid

from django.db import migrations, models


def _backfill_uuids(apps, schema_editor):
    """AddField below assigns the SAME literal default to every existing
    row (Postgres computes a callable default once for the ALTER TABLE
    statement) -- give each pre-existing row its own distinct uuid4 before
    the unique constraint is added, or that AlterField fails/would be wrong."""
    GibLabImportBatch = apps.get_model("orders", "GibLabImportBatch")
    for batch in GibLabImportBatch.objects.all():
        batch.uuid = uuid.uuid4()
        batch.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_remove_order_product_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="giblabimportbatch",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, db_index=True),
        ),
        migrations.RunPython(_backfill_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="giblabimportbatch",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="giblabimportbatch",
            name="import_plan",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="giblabimportbatch",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="giblabimportbatch",
            name="consumed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="giblabimportbatch",
            name="file_checksum",
            field=models.CharField(db_index=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="giblabimportbatch",
            name="status",
            field=models.CharField(
                choices=[
                    ("validated", "Tekshirildi"),
                    ("consuming", "Import qilinmoqda"),
                    ("completed", "Yakunlandi"),
                    ("failed", "Xatolik"),
                    ("expired", "Muddati o'tgan"),
                ],
                default="validated",
                max_length=16,
            ),
        ),
    ]
