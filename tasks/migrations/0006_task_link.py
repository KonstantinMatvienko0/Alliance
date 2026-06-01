from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0005_improvements'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='link',
            field=models.URLField(blank=True, help_text='External link (e.g. GitHub repo)', max_length=500),
        ),
    ]
