from django.conf import settings
from django.db import migrations, models


def copy_team_memberships(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Team = apps.get_model('tasks', 'Team')
    for user in User.objects.exclude(team_id=None).iterator():
        if user.team_id:
            try:
                team = Team.objects.get(pk=user.team_id)
            except Team.DoesNotExist:
                continue
            team.member_users.add(user)


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0009_team_target_types'),
        ('accounts', '0008_user_performance_stats'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='member_users',
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={'role': 'worker'},
                related_name='teams',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Участники',
            ),
        ),
        migrations.RunPython(copy_team_memberships, migrations.RunPython.noop),
    ]
