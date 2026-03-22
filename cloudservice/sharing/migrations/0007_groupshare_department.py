from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sharing', '0006_teamsitenews_tags_teamsitenews_view_count'),
        ('departments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupshare',
            name='department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='team_sites',
                to='departments.department',
                verbose_name='Abteilung',
            ),
        ),
    ]
