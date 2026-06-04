import json

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Skill, User, UserSkill
from accounts.services.work_timer import get_workers_work_summary

from ..decorators import manager_required
from ..models import Task, Team
from ..querysets import tasks_q_for_worker_profile
from ..type_utils import aggregate_task_types, tasks_with_type
from ..services.recommendations import score_worker_for_task
from ..ui_text import PROJECT_STATUS_LABELS, ROLE_TITLES

from .helpers import can_view_worker_profile, member_badge, worker_tasks_q


@login_required
def worker_profile(request, username):
    worker = get_object_or_404(User, username=username, role='worker')
    if not can_view_worker_profile(request.user, worker):
        return redirect('dashboard')

    tasks = Task.objects.filter(tasks_q_for_worker_profile(worker))
    user_skills = {
        us.skill_id: us.value
        for us in UserSkill.objects.filter(user=worker).select_related('skill')
    }

    soft_skills_data = [
        {'name': s.name, 'value': user_skills.get(s.id, 5)}
        for s in Skill.objects.filter(skill_type='soft')
    ]
    hard_skills_data = [
        {'name': s.name, 'value': user_skills.get(s.id, 5)}
        for s in Skill.objects.filter(skill_type='hard')
    ]

    type_stats = []
    for type_code, type_label in Task.TYPE_CHOICES:
        type_tasks = tasks_with_type(tasks, type_code)
        total = type_tasks.count()
        if total == 0:
            continue
        completed_count = type_tasks.filter(status='completed').count()
        type_stats.append({
            'label': type_label,
            'total': total,
            'completed': completed_count,
            'rate': round((completed_count / total) * 100, 1),
        })

    project_status_map = list(PROJECT_STATUS_LABELS.items())
    project_status = []
    for type_code, display_name in project_status_map:
        type_tasks = tasks_with_type(tasks, type_code)
        total = type_tasks.count()
        if total:
            completed_count = type_tasks.filter(status='completed').count()
            rate = round((completed_count / total) * 100, 1)
        else:
            rate = 0
        project_status.append({'label': display_name, 'rate': rate})

    worker_teams = list(worker.teams.all())
    team_members_rows = []
    seen_ids = set()
    for team in worker_teams:
        for member in team.get_members().order_by('username'):
            if member.pk in seen_ids or member.pk == worker.pk:
                continue
            seen_ids.add(member.pk)
            team_members_rows.append({
                'member': member,
                'badge': member_badge(member, team, request.user),
                'team_name': team.name,
            })

    team_rank = 0
    if worker_teams:
        team_rank = (
            Task.objects.filter(
                team__in=worker_teams,
                status='completed',
            ).aggregate(s=Sum('rank'))['s']
            or 0
        )

    role_display = ROLE_TITLES
    type_counter = aggregate_task_types(tasks)
    top_type = type_counter.most_common(1)[0][0] if type_counter else None
    role_title = role_display.get(top_type, 'FullStack-разработчик') if top_type else 'FullStack-разработчик'

    addr = (worker.address or '').strip()
    profile_location = addr if addr and '@' not in addr else ''

    shared_team = None
    if request.user.shares_team_with(worker):
        shared_team = request.user.teams.filter(
            pk__in=worker.teams.values('pk'),
        ).first()

    is_manager_view = request.user.role == 'manager'
    is_own_profile = request.user.pk == worker.pk
    is_viewing_other = not is_own_profile and not is_manager_view

    return render(request, 'tasks/worker_profile.html', {
        'worker': worker,
        'profile_user': request.user,
        'shared_team': shared_team,
        'completed': tasks.filter(status='completed').count(),
        'failed': tasks.filter(status='failed').count(),
        'in_progress': tasks.filter(status='in_progress').count(),
        'solo_rank': worker.rating,
        'team_rank': team_rank,
        'worker_teams': worker_teams,
        'team_members_rows': team_members_rows,
        'recent_tasks': tasks.select_related('team', 'completed_by').order_by('-due_date')[:5],
        'type_stats': type_stats,
        'project_status': project_status,
        'profile_location': profile_location,
        'soft_skills_data': soft_skills_data,
        'hard_skills_data': hard_skills_data,
        'soft_skills_json': json.dumps(soft_skills_data),
        'role_title': role_title,
        'can_edit_profile': is_own_profile or is_manager_view,
        'can_edit_skills': is_manager_view,
        'is_manager_view': is_manager_view,
        'is_own_profile': is_own_profile,
        'is_viewing_other': is_viewing_other,
    })


@manager_required
def manager_workers(request):
    workers = User.objects.filter(role='worker').prefetch_related('teams')
    query = request.GET.get('q', '').strip()
    skill_id = request.GET.get('skill_id', '')
    team_filter = request.GET.get('team', '')
    task_type = request.GET.get('type', '')
    unassigned_only = request.GET.get('unassigned') == '1'

    try:
        min_value = int(request.GET.get('min_value', 0))
    except ValueError:
        min_value = 0

    if query:
        workers = workers.filter(
            Q(username__icontains=query)
            | Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(specialization__icontains=query)
        )
    if skill_id:
        try:
            workers = workers.filter(
                skills__skill_id=int(skill_id),
                skills__value__gte=min_value,
            ).distinct()
        except (ValueError, Skill.DoesNotExist):
            pass
    if team_filter == 'none':
        workers = workers.filter(teams__isnull=True).distinct()
    elif team_filter:
        try:
            workers = workers.filter(teams__pk=int(team_filter)).distinct()
        except ValueError:
            pass
    if unassigned_only:
        workers = workers.filter(teams__isnull=True).distinct()

    work_map = {row['worker'].id: row for row in get_workers_work_summary()}
    worker_rows = []
    for worker in workers.order_by('-rating', 'username'):
        task_q = worker_tasks_q(worker)
        task_agg = Task.objects.filter(task_q).aggregate(
            open=Count('id', filter=Q(status__in=['open', 'in_progress'])),
            done=Count('id', filter=Q(status='completed')),
        )
        top_skills = list(
            worker.skills.select_related('skill')
            .order_by('-value')[:3]
            .values_list('skill__name', 'value')
        )
        match_score = None
        if task_type:
            match_score = score_worker_for_task(worker, task_type)['score']
        work = work_map.get(worker.id, {})
        worker_rows.append({
            'worker': worker,
            'open_tasks': task_agg['open'] or 0,
            'done_tasks': task_agg['done'] or 0,
            'top_skills': top_skills,
            'match_score': match_score,
            'is_working': work.get('is_working', False),
            'today_display': work.get('today_display', '00:00:00'),
        })

    if task_type:
        worker_rows.sort(
            key=lambda r: (r['match_score'] if r['match_score'] is not None else 0),
            reverse=True,
        )

    all_workers = User.objects.filter(role='worker')
    stats = {
        'total': all_workers.count(),
        'avg_rating': round(all_workers.aggregate(avg=Avg('rating'))['avg'] or 0),
        'working_now': sum(1 for row in get_workers_work_summary() if row['is_working']),
        'unassigned': all_workers.filter(teams__isnull=True).count(),
    }
    top_worker = all_workers.order_by('-rating').first()

    return render(request, 'tasks/manager_workers.html', {
        'worker_rows': worker_rows,
        'stats': stats,
        'top_worker': top_worker,
        'skills': Skill.objects.all(),
        'teams': Team.objects.all(),
        'type_choices': Task.TYPE_CHOICES,
        'query': query,
        'skill_id': skill_id,
        'min_value': min_value,
        'team_filter': team_filter,
        'type_filter': task_type,
        'unassigned_only': unassigned_only,
    })
