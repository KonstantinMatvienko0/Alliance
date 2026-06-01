"""Рекомендации работников и команд для задач и состава команд."""

from django.db.models import Count, Q

from accounts.models import Skill, User, UserSkill
from tasks.models import Task, Team
from tasks.type_utils import normalize_type_codes

# Соответствие типа задачи и ключевых слов в названии навыка
TASK_TYPE_SKILL_HINTS = {
    'Front': ('front', 'react', 'ui', 'mobile', 'template', 'javascript', 'верст'),
    'Back': ('back', 'api', 'server', 'python', 'backend', 'sql'),
    'Design': ('design', 'figma', 'ui', 'web design', 'дизайн'),
    'DB': ('db', 'sql', 'database', 'база'),
    'BD': ('bd', 'business', 'product', 'аналит'),
    'Backlog': ('backlog', 'plan', 'product'),
    'Canceled': (),
}


def _skill_matches_task_type(skill_name, task_type):
    hints = TASK_TYPE_SKILL_HINTS.get(task_type, ())
    name_lower = skill_name.lower()
    if any(h in name_lower for h in hints):
        return True
    return False


def _worker_skill_profile(user):
    hard = []
    soft = []
    for us in UserSkill.objects.filter(user=user).select_related('skill'):
        if us.skill.skill_type == 'hard':
            hard.append(us)
        else:
            soft.append(us)
    return hard, soft


def _hard_skill_fit(hard_skills, task_type):
    if not hard_skills:
        return 5.0
    matched = [us for us in hard_skills if _skill_matches_task_type(us.skill.name, task_type)]
    if matched:
        return sum(us.value for us in matched) / len(matched)
    related = [
        us for us in hard_skills
        if task_type in (us.skill.related_task_types or '')
    ]
    if related:
        return sum(us.value for us in related) / len(related)
    return sum(us.value for us in hard_skills) / len(hard_skills) * 0.6


def _soft_skill_avg(soft_skills):
    if not soft_skills:
        return 5.0
    return sum(us.value for us in soft_skills) / len(soft_skills)


def _workload_penalty(user):
    active = Task.objects.filter(
        Q(assigned_to=user) | Q(team__members=user),
        status__in=['open', 'in_progress'],
    ).distinct().count()
    return min(active * 4, 20)


def score_worker_for_task(user, task_type, task_rank=350):
    hard, soft = _worker_skill_profile(user)
    spec_bonus = 15 if user.specialization == task_type else (
        8 if user.specialization and user.specialization[:2] == task_type[:2] else 0
    )
    hard_fit = _hard_skill_fit(hard, task_type)
    soft_avg = _soft_skill_avg(soft)
    reliability = float(user.reliability_score)
    collaboration = float(user.collaboration_score)
    rating_bonus = min(user.rating / 50, 15)
    load = _workload_penalty(user)

    raw = (
        spec_bonus
        + hard_fit * 4
        + soft_avg * 2
        + reliability * 2.5
        + collaboration * 1.5
        + rating_bonus
        - load
    )
    score = max(0, min(100, round(raw)))

    reasons = []
    if spec_bonus >= 8:
        reasons.append('Совпадение специализации')
    if hard_fit >= 7:
        reasons.append('Сильные hard skills')
    if reliability >= 7:
        reasons.append('Надёжная история выполнения')
    if collaboration >= 7:
        reasons.append('Хорош в команде')
    if load >= 8:
        reasons.append('Высокая текущая нагрузка')

    return {
        'score': score,
        'reasons': reasons[:3],
        'hard_fit': round(hard_fit, 1),
        'soft_avg': round(soft_avg, 1),
        'reliability': reliability,
        'collaboration': collaboration,
        'specialization': user.specialization or '',
    }


def score_team_for_task(team, task_type, task_rank=350):
    members = list(team.members.filter(role='worker'))
    if not members:
        member_fit = 5.0
    else:
        fits = [score_worker_for_task(m, task_type, task_rank)['score'] for m in members]
        member_fit = sum(fits) / len(fits) / 10

    type_bonus = 12 if team.dominant_task_type == task_type else 0
    synergy = float(team.synergy_score)
    cohesion = float(team.cohesion_score)
    completed = team.tasks_completed_count
    failed = team.tasks_failed_count
    total = completed + failed
    success_rate = (completed / total) if total else 0.5

    raw = (
        type_bonus
        + member_fit * 35
        + synergy * 3
        + cohesion * 2
        + success_rate * 15
    )
    score = max(0, min(100, round(raw)))

    reasons = []
    if type_bonus:
        reasons.append('Фокус команды совпадает с типом задачи')
    if synergy >= 7:
        reasons.append('Высокая синергия команды')
    if member_fit >= 6:
        reasons.append('Участники подходят для задачи')

    return {
        'score': score,
        'reasons': reasons[:3],
        'synergy': synergy,
        'cohesion': cohesion,
        'members_count': len(members),
        'dominant_type': team.dominant_task_type or '',
    }


def score_worker_for_task_types(user, task_types, task_rank=350):
    selected = normalize_type_codes(task_types)
    if not selected:
        return score_worker_for_task(user, 'BD', task_rank)
    scores = [score_worker_for_task(user, task_type, task_rank) for task_type in selected]
    return max(scores, key=lambda item: item['score'])


def score_team_for_task_types(team, task_types, task_rank=350):
    selected = normalize_type_codes(task_types)
    if not selected:
        return score_team_for_task(team, 'BD', task_rank)
    scores = [score_team_for_task(team, task_type, task_rank) for task_type in selected]
    return max(scores, key=lambda item: item['score'])


def recommend_workers_for_task(task_type, query='', limit=20, task_types=None):
    workers = User.objects.filter(role='worker').prefetch_related('teams')
    if query:
        workers = workers.filter(
            Q(username__icontains=query)
            | Q(full_name__icontains=query)
            | Q(email__icontains=query)
        )

    results = []
    for w in workers:
        data = score_worker_for_task_types(w, task_types or [task_type], task_rank=350)
        results.append({
            'id': w.id,
            'label': w.full_name or w.username,
            'username': w.username,
            'rating': w.rating,
            'team_name': w.team_names_display(),
            'in_team': w.teams.exists(),
            'teams_count': w.teams.count(),
            **data,
        })
    results.sort(key=lambda x: (-x['score'], -x['rating']))
    return results[:limit]


def recommend_teams_for_task(task_type, query='', limit=10, task_types=None):
    teams = Team.objects.all().prefetch_related('members')
    if query:
        teams = teams.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    results = []
    for team in teams:
        data = score_team_for_task_types(team, task_types or [task_type], task_rank=350)
        results.append({
            'id': team.id,
            'label': team.name,
            'description': team.description[:80] if team.description else '',
            **data,
        })
    results.sort(key=lambda x: -x['score'])
    return results[:limit]


def score_worker_for_team(worker, team):
    """Насколько работник подходит для данной команды."""
    members = list(team.get_members().exclude(pk=worker.pk))
    task_type = team.dominant_task_type or 'BD'
    task_fit = score_worker_for_task(worker, task_type)

    if not members:
        complement = 8.0
    else:
        hard, soft = _worker_skill_profile(worker)
        gaps = []
        for m in members:
            mh, _ = _worker_skill_profile(m)
            for us in hard:
                if us.value >= 7 and not any(
                    abs(us.value - o.value) <= 1
                    for o in mh
                    if o.skill_id == us.skill_id
                ):
                    gaps.append(us.skill.name)
        complement = min(10, 5 + len(set(gaps)))

    collab = float(worker.collaboration_score)
    synergy_gap = abs(collab - float(team.cohesion_score))
    synergy_fit = max(0, 10 - synergy_gap)

    raw = (
        task_fit['score'] * 0.35
        + complement * 4
        + collab * 2
        + synergy_fit * 2
    )
    score = max(0, min(100, round(raw)))

    reasons = []
    if complement >= 7:
        reasons.append('Дополняет навыки команды')
    if collab >= 7:
        reasons.append('Хорошо работает в команде')
    if task_fit['score'] >= 60:
        reasons.append('Подходит под профиль задач команды')

    return {
        'score': score,
        'reasons': reasons[:3],
        'blocked': False,
        'task_fit': task_fit['score'],
        'complement': round(complement, 1),
    }


def _task_type_from_skill_ids(skill_ids):
    """Выбирает тип задач для оценки по выбранным навыкам."""
    if not skill_ids:
        return 'BD'
    for skill in Skill.objects.filter(id__in=skill_ids):
        for task_type in ('BD', 'Back', 'Front', 'Design', 'DB'):
            if _skill_matches_task_type(skill.name, task_type):
                return task_type
    return 'BD'


def recommend_workers_for_team(team_id, query='', limit=20):
    team = Team.objects.get(pk=team_id)
    workers = User.objects.filter(role='worker')

    if query:
        workers = workers.filter(
            Q(username__icontains=query)
            | Q(full_name__icontains=query)
        )

    results = []
    for w in workers:
        data = score_worker_for_team(w, team)
        results.append({
            'id': w.id,
            'label': w.full_name or w.username,
            'username': w.username,
            'rating': w.rating,
            'already_member': team.members.filter(pk=w.pk).exists(),
            'teams_label': w.team_names_display(),
            **data,
        })
    results.sort(key=lambda x: (-x['score'], -x['rating']))
    return results[:limit]
