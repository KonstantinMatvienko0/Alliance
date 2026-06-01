from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_task_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='cohesion_score',
            field=models.FloatField(default=5.0, help_text='Средняя совместимость участников (1–10)'),
        ),
        migrations.AddField(
            model_name='team',
            name='dominant_task_type',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='team',
            name='synergy_score',
            field=models.FloatField(default=5.0, help_text='Слаженность команды по завершённым командным задачам (1–10)'),
        ),
        migrations.AddField(
            model_name='team',
            name='tasks_completed_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='team',
            name='tasks_failed_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
