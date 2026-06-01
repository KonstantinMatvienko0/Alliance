from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_user_performance_stats'),
        ('tasks', '0010_team_members_m2m'),
    ]

    # Удаляем FK после копирования в tasks.0010 (поле member_users).

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='team',
        ),
    ]
