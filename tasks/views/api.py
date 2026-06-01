from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from accounts.models import Skill, User

from ..decorators import manager_required
from ..type_utils import normalize_type_codes
from ..models import Team
from accounts.models import User

from ..services.recommendations import (
    recommend_teams_for_task,
    recommend_workers_for_task,
    recommend_workers_for_team,
    score_worker_for_task,
)
from ..services.team_composition import (
    recommend_workers_for_team_form,
    score_roster_composition,
)
from ..type_utils import normalize_type_codes


@manager_required
def recommend_assignees(request):
    """Рекомендации работников и команд для назначения задачи."""
    task_types = normalize_type_codes(request.GET.getlist('type'))
    task_type = task_types[0] if task_types else request.GET.get('type', 'BD')
    query = request.GET.get('q', '').strip()

    return JsonResponse({
        'workers': recommend_workers_for_task(task_type, query=query, task_types=task_types or None),
        'teams': recommend_teams_for_task(task_type, query=query, task_types=task_types or None),
        'task_types': task_types or [task_type],
    })


def _team_form_recommend_params(request):
    skill_ids = request.GET.getlist('skill_id')
    target_types = normalize_type_codes(request.GET.getlist('type'))
    selected_ids = [
        int(x) for x in request.GET.getlist('selected') if str(x).isdigit()
    ]
    roster = list(User.objects.filter(pk__in=selected_ids, role='worker'))
    return skill_ids, target_types, roster


@manager_required
def recommend_team_members(request, pk):
    """Рекомендации работников для состава команды."""
    team = get_object_or_404(Team, pk=pk)
    query = request.GET.get('q', '').strip()
    skill_ids, target_types, roster = _team_form_recommend_params(request)
    if not target_types and team.target_types:
        target_types = normalize_type_codes(team.target_types)
    workers = recommend_workers_for_team_form(
        team=team,
        skill_ids=skill_ids or None,
        target_types=target_types or None,
        roster=roster,
        query=query,
    )
    roster_score = score_roster_composition(roster, target_types or ['BD']) if roster else None
    return JsonResponse({
        'workers': workers,
        'recommended': [w for w in workers if w.get('recommended')],
        'roster_score': roster_score,
        'target_types': target_types,
        'team': {'id': team.id, 'name': team.name},
    })


@manager_required
def recommend_team_members_new(request):
    """Рекомендации при создании команды (без id)."""
    query = request.GET.get('q', '').strip()
    skill_ids, target_types, roster = _team_form_recommend_params(request)
    workers = recommend_workers_for_team_form(
        team=None,
        skill_ids=skill_ids or None,
        target_types=target_types or None,
        roster=roster,
        query=query,
    )
    roster_score = score_roster_composition(roster, target_types or ['BD']) if roster else None
    return JsonResponse({
        'workers': workers,
        'recommended': [w for w in workers if w.get('recommended')],
        'roster_score': roster_score,
        'target_types': target_types,
    })


@manager_required
def filter_workers_by_skill(request):
    skill_id = request.GET.get('skill_id')
    min_value = request.GET.get('min_value', 0)
    try:
        min_value = int(min_value)
    except ValueError:
        min_value = 0

    workers = User.objects.filter(role='worker')
    if skill_id:
        try:
            skill = Skill.objects.get(id=skill_id)
            workers = workers.filter(skills__skill=skill, skills__value__gte=min_value).distinct()
        except Skill.DoesNotExist:
            pass

    task_type = request.GET.get('type', '')
    rows = []
    for w in workers:
        row = {
            'id': w.id,
            'name': w.full_name or w.username,
            'email': w.email,
            'rating': w.rating,
            'specialization': w.specialization or '',
            'collaboration_score': w.collaboration_score,
            'reliability_score': w.reliability_score,
        }
        if task_type:
            row['score'] = score_worker_for_task(w, task_type)['score']
        rows.append(row)
    if task_type:
        rows.sort(key=lambda x: x.get('score', 0), reverse=True)
    return JsonResponse({'workers': rows})
