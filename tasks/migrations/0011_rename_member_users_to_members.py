from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0010_team_members_m2m'),
        ('accounts', '0009_remove_user_team'),
    ]

    operations = [
        migrations.RenameField(
            model_name='team',
            old_name='member_users',
            new_name='members',
        ),
    ]
