from django.core.paginator import Paginator
from django.db.models import Count, Q

from accounts.services.work_timer import get_workers_work_summary

from ..models import Task, Team
from ..type_utils import aggregate_task_types, filter_tasks_by_types, parse_type_filters, type_labels
from ..ui_text import MEMBER_BADGES


def task_editable(task):
    return task.status in ('open', 'in_progress')


def save_task_from_form(form, user, *, is_create=True):
    task = form.save(commit=False)
    if task.team_id:
        task.assigned_to = None
    if is_create:
        task.created_by = user
    task.save()
    return task


def manager_tasks_queryset(request):
    tasks = (
        Task.objects.select_related('assigned_to', 'team', 'created_by')
        .order_by('-created_at', '-pk')
    )
    query = request.GET.get('q', '').strip()
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))
    type_filters = parse_type_filters(request)
    tasks = filter_tasks_by_types(tasks, type_filters)

    try:
        per_page = int(request.GET.get('per_page', 10))
    except ValueError:
        per_page = 10
    if per_page not in (10, 20, 50):
        per_page = 10

    page_obj = Paginator(tasks, per_page).get_page(request.GET.get('page'))
    qs = request.GET.copy()
    qs.pop('page', None)
    qs.pop('edit', None)
    qs.pop('create', None)
    return {
        'page_obj': page_obj,
        'query': query,
        'type_filters': type_filters,
        'per_page': per_page,
        'query_string': qs.urlencode(),
    }


def worker_tasks_q(worker):
    q = Q(assigned_to=worker)
    team_ids = list(worker.teams.values_list('pk', flat=True))
    if team_ids:
        q |= Q(team_id__in=team_ids, assigned_to__isnull=True)
    return q


def can_view_worker_profile(viewer, worker):
    if viewer.role == 'manager':
        return True
    if viewer.pk == worker.pk:
        return True
    if viewer.role == 'worker':
        return viewer.shares_team_with(worker)
    return False


def member_badge(member, team, viewer):
    if member.pk == team.created_by_id:
        return MEMBER_BADGES['owner']
    if member.pk == viewer.pk:
        return MEMBER_BADGES['you']
    return MEMBER_BADGES['member']


def team_list_item(team):
    type_counter = aggregate_task_types(team.tasks.all())
    skill_stats = type_counter.most_common(4)
    return {
        'team': team,
        'members_count': team.get_members().count(),
        'tasks_total': team.tasks.count(),
        'tasks_open': team.tasks.filter(status__in=['open', 'in_progress']).count(),
        'task_types': type_labels([code for code, _ in skill_stats]),
        'priority': team.priority_label(),
        'description': team.description,
        'total_rating': team.total_rating(),
    }


def worker_team_member_rows(team, viewer, query=''):
    work_map = {row['worker'].id: row for row in get_workers_work_summary()}
    members = team.get_members().order_by('-rating', 'username')
    if query:
        members = members.filter(
            Q(username__icontains=query) | Q(full_name__icontains=query)
        )

    rows = []
    for member in members:
        task_q = worker_tasks_q(member)
        task_agg = Task.objects.filter(task_q).aggregate(
            open=Count('id', filter=Q(status__in=['open', 'in_progress'])),
            done=Count('id', filter=Q(status='completed')),
        )
        work = work_map.get(member.id, {})
        rows.append({
            'member': member,
            'badge': member_badge(member, team, viewer),
            'is_self': member.pk == viewer.pk,
            'open_tasks': task_agg['open'] or 0,
            'done_tasks': task_agg['done'] or 0,
            'is_working': work.get('is_working', False),
            'today_display': work.get('today_display', '00:00:00'),
        })
    rows.sort(key=lambda r: (not r['is_self'], r['member'].username))
    return rows
