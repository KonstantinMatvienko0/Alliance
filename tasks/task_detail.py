"""Сериализация задачи для модального окна деталей."""

from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils import timezone

from .templatetags.task_ui import PRIORITY_ICONS, STATUS_ICONS, TYPE_ICONS


def _fmt_dt(dt):
    if not dt:
        return ''
    return timezone.localtime(dt).strftime('%d.%m.%Y %H:%M')


def build_task_detail_payload(task, request=None, *, worker_rating_change=None, task_rank_signed=None):
    types = [
        {'code': code, 'icon': TYPE_ICONS.get(code, 'fa-tag')}
        for code in (task.types or [])
    ]
    priority = task.priority_label()
    payload = {
        'id': task.pk,
        'code': task.task_code,
        'title': task.title,
        'description': task.description or '',
        'link': task.link or '',
        'types': types,
        'status': task.status,
        'status_label': task.status_ui_label(),
        'status_icon': STATUS_ICONS.get(task.status, 'fa-regular fa-circle'),
        'rank': task.rank,
        'priority': priority,
        'priority_icon': PRIORITY_ICONS.get(priority, 'fa-arrow-right'),
        'due_date': _fmt_dt(task.due_date),
        'completed_at': _fmt_dt(task.completed_at),
        'created_at': _fmt_dt(task.created_at),
        'team': task.team.name if task.team_id else '',
        'assigned_to': (
            (task.assigned_to.full_name or task.assigned_to.username)
            if task.assigned_to_id else ''
        ),
        'completed_by': (
            (task.completed_by.full_name or task.completed_by.username)
            if task.completed_by_id else ''
        ),
        'submitted_by': (
            (task.submitted_by.full_name or task.submitted_by.username)
            if task.submitted_by_id else ''
        ),
        'submitted_at': _fmt_dt(task.submitted_at),
        'is_overdue': task.is_overdue(),
    }
    if worker_rating_change is not None:
        payload['worker_rating_change'] = worker_rating_change
    if task_rank_signed is not None:
        payload['task_rank_signed'] = task_rank_signed
    if request is not None:
        payload['csrf'] = get_token(request)
        is_manager = getattr(request.user, 'role', None) == 'manager'
        payload['is_manager'] = is_manager
        if is_manager:
            if task.status in ('open', 'in_progress'):
                payload['edit_url'] = reverse('manager_tasks') + f'?edit={task.pk}'
            if task.status == 'pending_review':
                review_url = reverse('review_task', args=[task.pk])
                payload['can_review'] = True
                payload['review_approve_url'] = review_url
                payload['review_reject_url'] = review_url
            if not task.is_terminal():
                payload['delete_url'] = reverse('delete_task', args=[task.pk])
        else:
            if task.status == 'open':
                payload['start_url'] = reverse('start_task', args=[task.pk])
            if task.status == 'in_progress':
                payload['complete_url'] = reverse('complete_task', args=[task.pk])
    return payload


def tasks_detail_map_from_page(page_obj, request=None, *, row_key='task'):
    result = {}
    for item in page_obj:
        task = item[row_key] if isinstance(item, dict) else item
        extra = {}
        if isinstance(item, dict):
            if 'worker_rating_change' in item:
                extra['worker_rating_change'] = item['worker_rating_change']
            if 'task_rank_signed' in item:
                extra['task_rank_signed'] = item['task_rank_signed']
        result[str(task.pk)] = build_task_detail_payload(task, request, **extra)
    return result
