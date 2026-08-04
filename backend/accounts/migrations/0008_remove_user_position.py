from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_user_photo_user_position'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='position',
        ),
    ]
