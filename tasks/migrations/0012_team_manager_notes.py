from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0011_rename_member_users_to_members'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='manager_notes',
            field=models.TextField(
                blank=True,
                help_text='Видны только менеджерам',
                verbose_name='Заметки менеджера',
            ),
        ),
    ]
