# Generated manually — split from a single makemigrations run so the pin_code
# uniqueness constraint (0007) is only added after existing blank values are
# converted to NULL here, avoiding a unique-constraint failure on "" duplicates.

import django.db.models.deletion
from django.db import migrations, models


def blank_pin_codes_to_null(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(pin_code="").update(pin_code=None)


def null_pin_codes_to_blank(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(pin_code__isnull=True).update(pin_code="")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_user_managers'),
        ('manufacturing', '0003_remove_factory'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='assigned_workstation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='manufacturing.workstation'),
        ),
        migrations.AddField(
            model_name='user',
            name='assigned_workstations',
            field=models.ManyToManyField(blank=True, related_name='+', to='manufacturing.workstation'),
        ),
        migrations.AddField(
            model_name='user',
            name='multi_stage_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='user',
            name='pin_code',
            field=models.CharField(blank=True, help_text='Terminal PIN kodi', max_length=8, null=True),
        ),
        migrations.RunPython(blank_pin_codes_to_null, null_pin_codes_to_blank),
    ]
