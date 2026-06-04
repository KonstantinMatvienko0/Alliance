from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Skill, User
from accounts.services.work_timer import get_workers_work_summary

from ..decorators import manager_required
from ..forms import TeamForm
from ..models import Task, Team
from ..type_utils import aggregate_task_types, type_labels

from ..team_detail_payload import teams_detail_map_from_list

from .helpers import team_list_item, worker_team_member_rows


@login_required
def worker_team(request):
    user = request.user
    if user.role == 'manager':
        return redirect('team_list')
    if user.role != 'worker':
        return redirect('dashboard')

    team_items = [team_list_item(t) for t in user.teams.all().order_by('name')]
    return render(request, 'tasks/worker_team.html', {
        'has_team': bool(team_items),
        'team_items': team_items,
        'profile_user': user,
    })


@login_required
def worker_team_detail(request, pk):
    user = request.user
    if user.role == 'manager':
        return redirect('team_detail', pk=pk)
    if user.role != 'worker':
        return redirect('dashboard')

    team = get_object_or_404(Team, pk=pk)
    if not user.teams.filter(pk=team.pk).exists():
        return redirect('worker_team')

    query = request.GET.get('q', '').strip()
    member_rows = worker_team_member_rows(team, user, query=query)
    task_qs = Task.objects.filter(team=team).select_related('assigned_to')
    members = list(team.get_members())
    type_counter = aggregate_task_types(task_qs)
    skill_stats = type_counter.most_common(6)

    working_now = sum(1 for row in member_rows if row['is_working'])
    collab_avg = (
        sum(m.collaboration_score for m in members) / len(members) if members else 0
    )
    reliability_avg = (
        sum(m.reliability_score for m in members) / len(members) if members else 0
    )

    return render(request, 'tasks/worker_team_detail.html', {
        'profile_user': user,
        'team': team,
        'team_item': team_list_item(team),
        'member_rows': member_rows,
        'query': query,
        'priority': team.priority_label(),
        'tasks_open': task_qs.filter(status='open').count(),
        'tasks_in_progress': task_qs.filter(status='in_progress').count(),
        'tasks_done': task_qs.filter(status='completed').count(),
        'tasks_failed': task_qs.filter(status='failed').count(),
        'tasks_total': task_qs.count(),
        'avg_rank': round(task_qs.aggregate(avg=Avg('rank'))['avg'] or 0),
        'working_now': working_now,
        'avg_collaboration': round(collab_avg, 1),
        'avg_reliability': round(reliability_avg, 1),
        'task_types': [
            {'label': type_labels([code])[0], 'code': code, 'count': count}
            for code, count in skill_stats
        ],
        'recent_tasks': task_qs.exclude(status='failed').order_by('-created_at')[:5],
        'dominant_type': team.dominant_task_type,
        'synergy_percent': min(100, max(0, int(team.synergy_score * 10))),
        'cohesion_percent': min(100, max(0, int(team.cohesion_score * 10))),
    })


@manager_required
def team_list(request):
    query = request.GET.get('q', '').strip()
    teams = Team.objects.annotate(
        members_count=Count('members', distinct=True),
        tasks_total=Count('tasks', distinct=True),
        tasks_open=Count(
            'tasks',
            filter=Q(tasks__status__in=['open', 'in_progress']),
            distinct=True,
        ),
    ).order_by('-members_count', 'name')

    if query:
        teams = teams.filter(Q(name__icontains=query) | Q(description__icontains=query))

    teams_data = []
    for team in teams:
        type_counter = aggregate_task_types(team.tasks.all())
        skill_stats = type_counter.most_common(4)
        teams_data.append({
            'team': team,
            'members_count': team.members_count,
            'tasks_total': team.tasks_total,
            'tasks_open': team.tasks_open,
            'task_types': type_labels([code for code, _ in skill_stats]),
            'priority': team.priority_label(),
            'description': team.description,
            'total_rating': team.total_rating(),
        })

    all_teams = Team.objects.all()
    stats = {
        'total': all_teams.count(),
        'members': User.objects.filter(
            role='worker', teams__isnull=False,
        ).distinct().count(),
        'open_tasks': Task.objects.filter(
            team__isnull=False,
            status__in=['open', 'in_progress'],
        ).count(),
    }

    return render(request, 'tasks/team_list.html', {
        'teams_data': teams_data,
        'teams_detail_map': teams_detail_map_from_list(teams_data, request),
        'stats': stats,
        'query': query,
    })


@require_POST
@manager_required
def team_save_notes(request, pk):
    team = get_object_or_404(Team, pk=pk)
    notes = request.POST.get('manager_notes', '')
    if len(notes) > 5000:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Слишком длинная заметка'}, status=400)
        return redirect('team_detail', pk=pk)
    team.manager_notes = notes.strip()
    team.save(update_fields=['manager_notes'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('team_detail', pk=pk)


@manager_required
def team_create(request):
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.created_by = request.user
            team.save()
            form.save_m2m()
            return redirect('team_detail', pk=team.pk)
    else:
        form = TeamForm()
    return render(request, 'tasks/team_form.html', {
        'form': form,
        'title': 'Создать команду',
        'all_skills': Skill.objects.all(),
        'initial_member_ids': [],
    })


@manager_required
def team_edit(request, pk):
    team = get_object_or_404(Team, pk=pk)
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            return redirect('team_detail', pk=team.pk)
    else:
        form = TeamForm(instance=team)
    return render(request, 'tasks/team_form.html', {
        'form': form,
        'title': 'Редактировать команду',
        'team': team,
        'all_skills': Skill.objects.all(),
        'initial_member_ids': list(team.get_members().values_list('pk', flat=True)),
    })


@require_POST
@manager_required
def team_delete(request, pk):
    team = get_object_or_404(Team, pk=pk)
    team.delete()
    return redirect('team_list')


@manager_required
def team_detail(request, pk):
    team = get_object_or_404(Team, pk=pk)
    task_qs = team.tasks.select_related('assigned_to')
    type_counter = aggregate_task_types(task_qs)
    skill_stats = type_counter.most_common(5)
    work_map = {row['worker'].id: row for row in get_workers_work_summary()}
    member_rows = []
    for member in team.get_members().order_by('-rating'):
        work = work_map.get(member.id, {})
        member_rows.append({
            'member': member,
            'is_working': work.get('is_working', False),
            'today_display': work.get('today_display', '00:00:00'),
        })
    return render(request, 'tasks/team_detail.html', {
        'team': team,
        'member_rows': member_rows,
        'members_count': len(member_rows),
        'task_types': [
            {'label': type_labels([code])[0], 'count': count}
            for code, count in skill_stats
        ],
        'priority': team.priority_label(),
        'avg_rank': round(task_qs.aggregate(avg=Avg('rank'))['avg'] or 0),
        'tasks_open': task_qs.filter(status__in=['open', 'in_progress']).count(),
        'tasks_done': task_qs.filter(status='completed').count(),
        'tasks_failed': task_qs.filter(status='failed').count(),
        'recent_tasks': task_qs.order_by('-created_at')[:8],
        'total_rating': team.total_rating(),
    })
