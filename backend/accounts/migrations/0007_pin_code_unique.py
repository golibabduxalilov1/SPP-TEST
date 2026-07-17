from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_pin_code_nullable_and_stage_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='pin_code',
            field=models.CharField(blank=True, help_text='Terminal PIN kodi', max_length=8, null=True, unique=True),
        ),
    ]
