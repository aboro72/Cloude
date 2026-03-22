import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks_board', '0001_initial'),
        ('departments', '0002_department_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskboard',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='task_boards',
                to='departments.department',
                verbose_name='Abteilung',
            ),
        ),
    ]
