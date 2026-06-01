import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_work_sessions'),
    ]

    operations = [
        migrations.AddField(
            model_name='skill',
            name='related_task_types',
            field=models.CharField(
                blank=True,
                help_text='Типы задач через запятую: Front,Back,Design',
                max_length=120,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='collaboration_score',
            field=models.FloatField(
                default=5.0,
                help_text='Насколько эффективен в команде (1–10)',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(10),
                ],
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='reliability_score',
            field=models.FloatField(
                default=5.0,
                help_text='Надёжность по solo-задачам (1–10)',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(10),
                ],
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='solo_tasks_completed',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='solo_tasks_failed',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='specialization',
            field=models.CharField(
                blank=True,
                help_text='Основная специализация (код типа задачи: Front, Back, …)',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='team_tasks_completed',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='team_tasks_failed',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
