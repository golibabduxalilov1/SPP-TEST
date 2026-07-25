import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_assigned_machines_forward(apps, schema_editor):
    """Preserve every existing (employee, machine) assignment — user.assigned_machines
    is still the old plain M2M at this point in the migration history, so this reads
    from it one last time before 0005 repoints the field at the new through model."""
    User = apps.get_model("accounts", "User")
    EmployeeStageMachine = apps.get_model("accounts", "EmployeeStageMachine")
    rows = [
        EmployeeStageMachine(employee_id=user.id, machine_id=machine.id, stage_id=machine.operation_id)
        for user in User.objects.prefetch_related("assigned_machines")
        for machine in user.assigned_machines.all()
    ]
    EmployeeStageMachine.objects.bulk_create(rows, ignore_conflicts=True)


def copy_assigned_machines_backward(apps, schema_editor):
    apps.get_model("accounts", "EmployeeStageMachine").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_remove_user_hired_at_remove_user_multi_shift_enabled_and_more'),
        ('manufacturing', '0004_delete_shift'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeStageMachine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stage_machine_links', to=settings.AUTH_USER_MODEL)),
                ('machine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='manufacturing.machine')),
                ('stage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='manufacturing.operation')),
            ],
        ),
        migrations.AddConstraint(
            model_name='employeestagemachine',
            constraint=models.UniqueConstraint(fields=('employee', 'machine'), name='unique_employee_machine'),
        ),
        migrations.RunPython(copy_assigned_machines_forward, copy_assigned_machines_backward),
    ]
