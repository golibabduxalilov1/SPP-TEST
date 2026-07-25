from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_employeestagemachine'),
    ]

    operations = [
        # Django forbids AlterField from changing an M2M's through= model —
        # "you cannot alter to or from M2M fields, or add or remove
        # through= on M2M fields" — so the field must be dropped (removing
        # the old implicit join table, already emptied by 0004's data copy)
        # and re-added bound to the new through model.
        migrations.RemoveField(model_name='user', name='assigned_machines'),
        migrations.AddField(
            model_name='user',
            name='assigned_machines',
            field=models.ManyToManyField(blank=True, related_name='+', through='accounts.EmployeeStageMachine', to='manufacturing.machine'),
        ),
    ]
