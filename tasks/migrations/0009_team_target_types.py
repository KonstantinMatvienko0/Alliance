from django.db import migrations, models


def backfill_metrics(apps, schema_editor):
    from tasks.services.performance_metrics import refresh_all_metrics
    refresh_all_metrics()


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0008_task_types'),
        ('accounts', '0008_user_performance_stats'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='target_types',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Типы задач, под которые собрана команда',
            ),
        ),
        migrations.RunPython(backfill_metrics, migrations.RunPython.noop),
    ]
