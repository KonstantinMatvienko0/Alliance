from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import User
from accounts.services.work_timer import get_workers_work_summary

from ..models import Task, Team
from ..querysets import tasks_q_for_worker, worker_today_focus_tasks
from ..services.rating import rating_change_for_user
from ..task_detail import tasks_detail_map_from_page
from ..type_utils import _type_match_q, aggregate_task_types, filter_tasks_by_types, parse_type_filters
from ..ui_text import (
    MONTH_NAMES,
    PRIORITY_FILTER_CHOICES,
    RESULT_FILTER_CHOICES,
    ROLE_TITLES,
    WEEKDAY_NAMES,
    greeting_for_hour,
)


@login_required
def dashboard(request):
    if request.user.role == 'manager':
        return manager_dashboard(request)
    return worker_home(request)


@login_required
def manager_dashboard(request):
    if request.user.role != 'manager':
        return redirect('dashboard')

    total_rank = User.objects.aggregate(total=Sum('rating'))['total'] or 0
    status_counts = dict(
        Task.objects.values('status').annotate(c=Count('id')).values_list('status', 'c')
    )
    pending_review_count = status_counts.get('pending_review', 0)
    now = timezone.localtime()
    display_name = request.user.full_name or request.user.username

    return render(request, 'tasks/manager_dashboard.html', {
        'greeting': greeting_for_hour(now.hour),
        'display_name': display_name,
        'today_label': f'{now.day} {MONTH_NAMES[now.month]}, {WEEKDAY_NAMES[now.weekday()]}',
        'total_tasks': Task.objects.count(),
        'tasks_open': status_counts.get('open', 0),
        'tasks_in_progress': status_counts.get('in_progress', 0),
        'tasks_completed': status_counts.get('completed', 0),
        'tasks_failed': status_counts.get('failed', 0),
        'workers_count': User.objects.filter(role='worker').count(),
        'teams_count': Team.objects.count(),
        'total_rank': total_rank,
        'workers_work': get_workers_work_summary(),
        'pending_review_count': pending_review_count,
    })


@login_required
def worker_home(request):
    if request.user.role != 'worker':
        return redirect('dashboard')

    user = request.user
    now = timezone.localtime()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    week_ago = now - timedelta(days=7)

    base_q = tasks_q_for_worker(user)
    all_tasks = Task.objects.filter(base_q).select_related('team')
    active = all_tasks.filter(status__in=['open', 'in_progress', 'pending_review'])

    today_focus = worker_today_focus_tasks(
        active,
        now=now,
        start_of_day=start_of_day,
        end_of_day=end_of_day,
    )

    in_progress_tasks = active.filter(status='in_progress').order_by('due_date')[:5]
    open_tasks = active.filter(status='open').order_by('due_date')[:5]

    overdue_count = active.filter(due_date__lt=now).count()
    due_today_count = active.filter(
        due_date__gte=now,
        due_date__lt=end_of_day,
    ).count()

    type_counter = aggregate_task_types(all_tasks)
    top_type = type_counter.most_common(1)[0][0] if type_counter else None
    role_title = ROLE_TITLES.get(top_type, 'Разработчик') if top_type else 'Разработчик'

    return render(request, 'tasks/worker_home.html', {
        'greeting': greeting_for_hour(now.hour),
        'display_name': user.full_name or user.username,
        'today_label': f'{now.day} {MONTH_NAMES[now.month]}, {WEEKDAY_NAMES[now.weekday()]}',
        'role_title': role_title,
        'rating': user.rating,
        'teams': user.teams.all(),
        'team': user.teams.first(),
        'open_count': active.filter(status='open').count(),
        'in_progress_count': active.filter(status='in_progress').count(),
        'pending_review_count': active.filter(status='pending_review').count(),
        'overdue_count': overdue_count,
        'due_today_count': due_today_count,
        'completed_week': all_tasks.filter(
            status='completed',
            completed_at__gte=week_ago,
        ).count(),
        'today_tasks': today_focus,
        'in_progress_tasks': in_progress_tasks,
        'open_tasks': open_tasks,
    })


@login_required
def worker_tasks(request):
    if request.user.role != 'worker':
        return redirect('dashboard')

    user = request.user
    base_q = tasks_q_for_worker(user)
    tasks = (
        Task.objects.filter(base_q)
        .exclude(status='failed')
        .select_related('team')
    )

    query = request.GET.get('q', '').strip()
    if query:
        type_q = Q()
        q_lower = query.lower()
        for code, label in Task.TYPE_CHOICES:
            if q_lower in code.lower() or q_lower in label.lower():
                type_q |= _type_match_q(code)
        tasks = tasks.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | type_q
            | Q(team__name__icontains=query)
        )

    status_filter = request.GET.get('status', '')
    if status_filter in dict(Task.STATUS_CHOICES):
        tasks = tasks.filter(status=status_filter)

    priority_filter = request.GET.get('priority', '')
    if priority_filter == 'High':
        tasks = tasks.filter(rank__gt=600)
    elif priority_filter == 'Medium':
        tasks = tasks.filter(rank__gt=300, rank__lte=600)
    elif priority_filter == 'Low':
        tasks = tasks.filter(rank__lte=300)

    type_filters = parse_type_filters(request)
    tasks = filter_tasks_by_types(tasks, type_filters)

    overdue_count = Task.objects.filter(
        base_q,
        status__in=['open', 'in_progress'],
        due_date__lt=timezone.now(),
    ).count()

    try:
        per_page = int(request.GET.get('per_page', 10))
    except ValueError:
        per_page = 10
    per_page = per_page if per_page in (10, 20, 50) else 10

    page_obj = Paginator(tasks.order_by('-created_at'), per_page).get_page(request.GET.get('page'))
    total_count = tasks.count()
    in_progress_count = tasks.filter(status='in_progress').count()

    return render(request, 'tasks/worker_dashboard.html', {
        'page_obj': page_obj,
        'tasks_detail_map': tasks_detail_map_from_page(page_obj, request),
        'query': query,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'type_filters': type_filters,
        'per_page': per_page,
        'total_count': total_count,
        'overdue_count': overdue_count,
        'in_progress_count': in_progress_count,
        'status_choices': Task.STATUS_CHOICES,
        'type_choices': Task.TYPE_CHOICES,
        'priority_filter_choices': PRIORITY_FILTER_CHOICES,
    })


@login_required
def ranked_statistic(request):
    if request.user.role != 'worker':
        return redirect('dashboard')

    user = request.user
    base_q = tasks_q_for_worker(user)
    tasks = (
        Task.objects.filter(base_q, status__in=['completed', 'failed'])
        .select_related('team', 'completed_by')
        .order_by('-completed_at', '-pk')
    )

    query = request.GET.get('q', '').strip()
    if query:
        type_q = Q()
        q_lower = query.lower()
        for code, label in Task.TYPE_CHOICES:
            if q_lower in code.lower() or q_lower in label.lower():
                type_q |= _type_match_q(code)
        tasks = tasks.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | type_q
        )

    type_filters = parse_type_filters(request)
    tasks = filter_tasks_by_types(tasks, type_filters)

    result_filter = request.GET.get('result', '')
    if result_filter == 'completed':
        tasks = tasks.filter(status='completed')
    elif result_filter == 'failed':
        tasks = tasks.filter(status='failed')

    try:
        per_page = int(request.GET.get('per_page', 10))
    except ValueError:
        per_page = 10
    per_page = per_page if per_page in (10, 20, 50) else 10

    ranked_rows = []
    for task in tasks:
        delta = rating_change_for_user(task, user)
        task_rank_signed = task.rank if task.status == 'completed' else -task.rank
        ranked_rows.append({
            'task': task,
            'task_rank': task.rank,
            'task_rank_signed': task_rank_signed,
            'worker_rating_change': delta,
        })

    page_obj = Paginator(ranked_rows, per_page).get_page(request.GET.get('page'))

    return render(request, 'tasks/ranked_statistic.html', {
        'page_obj': page_obj,
        'tasks_detail_map': tasks_detail_map_from_page(page_obj, request),
        'worker': user,
        'worker_rating': user.rating,
        'query': query,
        'type_filters': type_filters,
        'result_filter': result_filter,
        'per_page': per_page,
        'type_choices': Task.TYPE_CHOICES,
        'result_choices': RESULT_FILTER_CHOICES,
    })
