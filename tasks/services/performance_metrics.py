"""Пересчёт характеристик работников и команд по истории задач."""

from django.db.models import Q

from accounts.models import User
from tasks.models import Task, Team
from tasks.type_utils import VALID_TASK_TYPE_CODES, aggregate_task_types

SOFT_SKILL_NAMES = {
    'коммуникация', 'communication', 'лидерство', 'leadership',
    'работа в команде', 'teamwork', 'адаптивность', 'adaptability',
}


def _clamp_score(value, low=1.0, high=10.0):
    return max(low, min(high, round(float(value), 2)))


def _completion_rate(completed, failed):
    total = completed + failed
    if total == 0:
        return 0.5
    return completed / total


def _worker_closed_tasks(user):
    """Завершённые solo- и командные задачи, где участвовал работник."""
    solo = Q(assigned_to=user)
    team = Q(team__members=user, assigned_to__isnull=True)
    return Task.objects.filter(solo | team).filter(
        status__in=('completed', 'failed'),
    ).select_related('team')


def _update_type_stats_and_velocity(user):
    type_stats = {}
    on_time = 0
    closed = 0

    for task in _worker_closed_tasks(user):
        closed += 1
        success = task.status == 'completed'
        if success and task.completed_at and task.completed_at <= task.due_date:
            on_time += 1

        for code in task.types or []:
            if code not in VALID_TASK_TYPE_CODES:
                continue
            bucket = type_stats.setdefault(
                code,
                {'completed': 0, 'failed': 0, 'on_time': 0},
            )
            if success:
                bucket['completed'] += 1
                if task.completed_at and task.completed_at <= task.due_date:
                    bucket['on_time'] += 1
            else:
                bucket['failed'] += 1

    user.type_stats = type_stats
    user.velocity_score = _clamp_score(
        1 + 9 * (on_time / closed if closed else 0.5)
    )


def refresh_worker_metrics(user):
    if user.role != 'worker':
        return

    solo_completed = Task.objects.filter(
        assigned_to=user, status='completed',
    ).count()
    solo_failed = Task.objects.filter(
        assigned_to=user, status='failed',
    ).count()
    team_completed = Task.objects.filter(
        team__members=user, assigned_to__isnull=True, status='completed',
    ).count()
    team_failed = Task.objects.filter(
        team__members=user, assigned_to__isnull=True, status='failed',
    ).count()

    user.solo_tasks_completed = solo_completed
    user.solo_tasks_failed = solo_failed
    user.team_tasks_completed = team_completed
    user.team_tasks_failed = team_failed

    user.reliability_score = _clamp_score(
        1 + 9 * _completion_rate(solo_completed, solo_failed)
    )
    user.collaboration_score = _clamp_score(
        1 + 9 * _completion_rate(team_completed, team_failed)
    )

    type_counter = aggregate_task_types(
        Task.objects.filter(assigned_to=user, status='completed')
    )
    if type_counter:
        user.specialization = type_counter.most_common(1)[0][0]

    _update_type_stats_and_velocity(user)

    user.save(update_fields=[
        'solo_tasks_completed', 'solo_tasks_failed',
        'team_tasks_completed', 'team_tasks_failed',
        'reliability_score', 'collaboration_score', 'specialization',
        'velocity_score', 'type_stats',
    ])


def refresh_team_metrics(team):
    members = list(team.members.filter(role='worker'))
    if members:
        team.cohesion_score = _clamp_score(
            sum(m.collaboration_score for m in members) / len(members)
        )
    else:
        team.cohesion_score = 5.0

    completed = team.tasks.filter(status='completed').count()
    failed = team.tasks.filter(status='failed').count()
    team.tasks_completed_count = completed
    team.tasks_failed_count = failed
    team.synergy_score = _clamp_score(1 + 9 * _completion_rate(completed, failed))

    type_counter = aggregate_task_types(team.tasks.filter(status='completed'))
    team.dominant_task_type = type_counter.most_common(1)[0][0] if type_counter else ''

    team.save(update_fields=[
        'cohesion_score', 'synergy_score', 'dominant_task_type',
        'tasks_completed_count', 'tasks_failed_count',
    ])


def refresh_after_task_outcome(task):
    """Вызывается после завершения задачи."""
    if task.assigned_to_id:
        refresh_worker_metrics(task.assigned_to)
    if task.team_id:
        refresh_team_metrics(task.team)
        for member in task.team.members.filter(role='worker'):
            refresh_worker_metrics(member)


def refresh_all_metrics():
    for user in User.objects.filter(role='worker'):
        refresh_worker_metrics(user)
    for team in Team.objects.defer('manager_notes'):
        refresh_team_metrics(team)
