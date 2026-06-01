from django.db import migrations, models


def copy_type_to_types(apps, schema_editor):
    Task = apps.get_model('tasks', 'Task')
    for task in Task.objects.all().iterator():
        legacy_type = getattr(task, 'type', None) or 'BD'
        task.types = [legacy_type]
        task.save(update_fields=['types'])


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0007_team_characteristics'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='types',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(copy_type_to_types, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='task',
            name='type',
        ),
    ]
