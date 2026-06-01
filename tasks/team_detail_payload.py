"""Сериализация команды для модального окна деталей (только менеджер)."""

from django.db.models import Avg
from django.middleware.csrf import get_token
from django.urls import reverse

from accounts.services.work_timer import get_workers_work_summary

from .type_utils import aggregate_task_types, type_labels


def _priority_class(priority):
    if priority == 'High':
        return 'high'
    if priority == 'Medium':
        return 'medium'
    return 'low'


def build_team_detail_payload(team, request=None, *, list_item=None):
    if list_item:
        members_count = list_item['members_count']
        tasks_total = list_item['tasks_total']
        tasks_open = list_item['tasks_open']
        task_types = list_item['task_types']
        priority = list_item['priority']
        total_rating = list_item['total_rating']
        description = list_item['description'] or ''
    else:
        members_count = team.get_members().count()
        task_qs = team.tasks.all()
        tasks_total = task_qs.count()
        tasks_open = task_qs.filter(status__in=['open', 'in_progress']).count()
        type_counter = aggregate_task_types(task_qs)
        task_types = type_labels([code for code, _ in type_counter.most_common(4)])
        priority = team.priority_label()
        total_rating = team.total_rating()
        description = team.description or ''

    task_qs = team.tasks.all()
    tasks_done = task_qs.filter(status='completed').count()
    tasks_failed = task_qs.filter(status='failed').count()
    avg_rank = round(task_qs.aggregate(avg=Avg('rank'))['avg'] or 0)

    work_map = {row['worker'].id: row for row in get_workers_work_summary()}
    members = []
    for member in team.get_members().order_by('-rating', 'username'):
        work = work_map.get(member.id, {})
        members.append({
            'id': member.pk,
            'name': member.full_name or member.username,
            'username': member.username,
            'rating': member.rating,
            'profile_url': reverse('worker_profile', args=[member.username]),
            'is_working': work.get('is_working', False),
            'today_display': work.get('today_display', '00:00:00'),
        })

    target_types = type_labels(team.target_types or [])

    payload = {
        'id': team.pk,
        'name': team.name,
        'description': description or 'Описание пока не добавлено.',
        'priority': priority,
        'priority_class': _priority_class(priority),
        'members_count': members_count,
        'total_rating': total_rating,
        'synergy_score': round(team.synergy_score, 1),
        'cohesion_score': round(team.cohesion_score, 1),
        'tasks_total': tasks_total,
        'tasks_open': tasks_open,
        'tasks_done': tasks_done,
        'tasks_failed': tasks_failed,
        'tasks_completed_count': team.tasks_completed_count,
        'tasks_failed_count': team.tasks_failed_count,
        'avg_rank': avg_rank,
        'task_types': task_types,
        'target_types': target_types,
        'dominant_task_type': team.dominant_task_type or '',
        'members': members,
        'manager_notes': team.manager_notes or '',
    }

    if request is not None:
        payload['csrf'] = get_token(request)
        payload['notes_url'] = reverse('team_save_notes', args=[team.pk])
        payload['edit_url'] = reverse('team_edit', args=[team.pk])
        payload['detail_url'] = reverse('team_detail', args=[team.pk])
        payload['create_task_url'] = (
            reverse('manager_tasks') + f'?create=1&assign_team={team.pk}'
        )

    return payload


def teams_detail_map_from_list(teams_data, request=None):
    return {
        str(item['team'].pk): build_team_detail_payload(
            item['team'], request, list_item=item,
        )
        for item in teams_data
    }
