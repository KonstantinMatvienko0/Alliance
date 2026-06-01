from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_worker_characteristics'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='velocity_score',
            field=models.FloatField(
                default=5.0,
                help_text='Скорость и соблюдение сроков (1–10)',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(10),
                ],
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='type_stats',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Статистика по типам задач: completed, failed, on_time',
            ),
        ),
    ]
