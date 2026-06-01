"""
Подбор состава команды: совместимость, покрытие навыков, опыт по типам задач.
"""

from django.db.models import Q

from accounts.models import User, UserSkill
from tasks.models import Task, Team
from tasks.services.recommendations import (
    _task_type_from_skill_ids,
    _worker_skill_profile,
    _workload_penalty,
    score_worker_for_task,
    score_worker_for_task_types,
)
from tasks.type_utils import normalize_type_codes

RECOMMENDED_THRESHOLD = 62
STRONG_SKILL_LEVEL = 6


def _clamp_0_10(value):
    return max(0.0, min(10.0, float(value)))


def _type_track_record_score(user, task_types):
    """Успешность работника по выбранным типам задач (0–10)."""
    stats = user.type_stats or {}
    rates = []
    for code in task_types:
        bucket = stats.get(code, {})
        completed = bucket.get('completed', 0)
        failed = bucket.get('failed', 0)
        total = completed + failed
        if total:
            rates.append(completed / total)
    if not rates:
        return 5.0
    return _clamp_0_10(sum(rates) / len(rates) * 10)


def get_pairwise_affinity(user_a, user_b):
    """Насколько хорошо двое работали вместе в командных задачах (0–10)."""
    if user_a.pk == user_b.pk:
        return 10.0

    shared_team_ids = Team.objects.filter(members=user_a).filter(
        members=user_b,
    ).values_list('pk', flat=True)

    if not shared_team_ids:
        collab_gap = abs(float(user_a.collaboration_score) - float(user_b.collaboration_score))
        return _clamp_0_10(10 - collab_gap * 0.8)

    tasks = Task.objects.filter(
        team_id__in=shared_team_ids,
        assigned_to__isnull=True,
        status__in=('completed', 'failed'),
    )
    completed = tasks.filter(status='completed').count()
    failed = tasks.filter(status='failed').count()
    total = completed + failed
    if total == 0:
        return 5.5

    base = 1 + 9 * (completed / total)
    if total >= 3:
        base = min(10.0, base + 0.5)
    return _clamp_0_10(base)


def _avg_pairwise_synergy(worker, roster):
    if not roster:
        return 7.0
    others = [m for m in roster if m.pk != worker.pk]
    if not others:
        return 10.0
    return sum(get_pairwise_affinity(worker, o) for o in others) / len(others)


def _skill_coverage_gain(worker, roster, skill_ids):
    """Насколько кандидат закрывает пробелы в навыках относительно текущего состава."""
    skill_ids = [int(x) for x in (skill_ids or []) if str(x).isdigit()]
    if not skill_ids:
        hard, _ = _worker_skill_profile(worker)
        if not hard:
            return 5.0
        roster_hard = {}
        for m in roster:
            mh, _ = _worker_skill_profile(m)
            for us in mh:
                roster_hard[us.skill_id] = max(roster_hard.get(us.skill_id, 0), us.value)
        gaps = 0
        for us in hard:
            if us.value >= STRONG_SKILL_LEVEL and roster_hard.get(us.skill_id, 0) < STRONG_SKILL_LEVEL - 1:
                gaps += 1
        return _clamp_0_10(4 + min(6, gaps * 1.5))

    matched = list(
        UserSkill.objects.filter(user=worker, skill_id__in=skill_ids).select_related('skill')
    )
    if not matched:
        return 0.0

    roster_levels = {}
    for m in roster:
        for us in UserSkill.objects.filter(user=m, skill_id__in=skill_ids):
            roster_levels[us.skill_id] = max(roster_levels.get(us.skill_id, 0), us.value)

    gain = 0.0
    for us in matched:
        roster_val = roster_levels.get(us.skill_id, 0)
        if us.value > roster_val:
            gain += (us.value - roster_val) / 10.0

    coverage = len({us.skill_id for us in matched}) / len(skill_ids)
    return _clamp_0_10(coverage * 5 + gain * 2)


def _redundancy_penalty(worker, roster):
    if not roster:
        return 0.0
    penalty = 0.0
    worker_spec = worker.specialization or ''
    spec_overlap = sum(
        1 for m in roster
        if m.specialization and m.specialization == worker_spec
    )
    penalty += min(4.0, spec_overlap * 2.0)

    whard, _ = _worker_skill_profile(worker)
    top_worker = {us.skill_id for us in whard if us.value >= 8}
    for m in roster:
        mh, _ = _worker_skill_profile(m)
        overlap = sum(1 for us in mh if us.skill_id in top_worker and us.value >= 7)
        penalty += min(2.0, overlap * 0.8)

    return min(10.0, penalty)


def _roster_task_fit(roster, task_types):
    """Средняя готовность состава к типам задач (0–10)."""
    if not roster:
        return 5.0
    per_member = [
        score_worker_for_task_types(m, task_types)['score'] / 10.0
        for m in roster
    ]
    avg = sum(per_member) / len(per_member)
    specs = {m.specialization for m in roster if m.specialization}
    diversity = min(2.0, len(specs) * 0.5)
    return _clamp_0_10(avg * 8 + diversity)


def score_roster_composition(roster, task_types):
    """Оценка уже выбранного состава (0–100)."""
    task_types = normalize_type_codes(task_types) or ['BD']
    if len(roster) < 2:
        if len(roster) == 1:
            return score_worker_for_team_composition(
                roster[0], [], task_types, skill_ids=None,
            )['score']
        return 0

    fit = _roster_task_fit(roster, task_types)
    synergy_scores = []
    for i, a in enumerate(roster):
        for b in roster[i + 1:]:
            synergy_scores.append(get_pairwise_affinity(a, b))
    synergy = sum(synergy_scores) / len(synergy_scores) if synergy_scores else 5.0

    velocity = sum(float(m.velocity_score) for m in roster) / len(roster)
    reliability = sum(float(m.reliability_score) for m in roster) / len(roster)

    raw = fit * 4.5 + synergy * 2.5 + velocity * 1.5 + reliability * 1.5
    return max(0, min(100, round(raw)))


def score_worker_for_team_composition(
    worker,
    roster,
    task_types=None,
    skill_ids=None,
    team=None,
):
    """
    Оценка кандидата для добавления в состав (0–100) с объяснениями.
    roster — уже выбранные участники (без кандидата).
    """
    task_types = normalize_type_codes(task_types)
    if not task_types:
        if team and team.target_types:
            task_types = normalize_type_codes(team.target_types)
        elif team and team.dominant_task_type:
            task_types = [team.dominant_task_type]
        else:
            task_types = ['BD']

    roster = list(roster)
    prospective = roster + [worker]

    individual = score_worker_for_task_types(worker, task_types)['score'] / 10.0
    track = _type_track_record_score(worker, task_types) / 10.0
    complement = _skill_coverage_gain(worker, roster, skill_ids) / 10.0
    pairwise = _avg_pairwise_synergy(worker, roster) / 10.0
    roster_before = _roster_task_fit(roster, task_types)
    roster_after = _roster_task_fit(prospective, task_types)
    roster_delta = _clamp_0_10(roster_after - roster_before) / 10.0
    reliability = float(worker.reliability_score) / 10.0
    velocity = float(getattr(worker, 'velocity_score', 5.0)) / 10.0
    collaboration = float(worker.collaboration_score) / 10.0
    workload = 1.0 - _workload_penalty(worker) / 20.0
    redundancy = _redundancy_penalty(worker, roster) / 10.0

    raw_10 = (
        individual * 2.4
        + track * 1.6
        + complement * 2.0
        + pairwise * 1.8
        + roster_delta * 1.2
        + reliability * 0.9
        + velocity * 0.9
        + collaboration * 0.7
        + workload * 0.5
        - redundancy * 0.8
    )
    score = max(0, min(100, round(raw_10 * 10)))

    reasons = []
    if track >= 0.75:
        reasons.append('Сильный опыт по типу задач')
    if complement >= 0.7:
        reasons.append('Закрывает пробелы в навыках')
    if pairwise >= 0.75:
        reasons.append('Хорошая совместимость с составом')
    if roster_delta >= 0.35:
        reasons.append('Усиливает команду под задачи')
    if velocity >= 0.75:
        reasons.append('Укладывается в сроки')
    if reliability >= 0.75:
        reasons.append('Надёжно выполняет задачи')
    if collaboration >= 0.75:
        reasons.append('Эффективен в команде')
    if redundancy >= 0.5:
        reasons.append('Дублирует навыки состава')
    if _workload_penalty(worker) >= 12:
        reasons.append('Высокая текущая нагрузка')

    if not reasons:
        if individual >= 0.6:
            reasons.append('Подходит под профиль задач')
        else:
            reasons.append('Среднее соответствие')

    return {
        'score': score,
        'reasons': reasons[:4],
        'blocked': False,
        'recommended': score >= RECOMMENDED_THRESHOLD,
        'breakdown': {
            'individual': round(individual * 10, 1),
            'experience': round(track * 10, 1),
            'skills': round(complement * 10, 1),
            'synergy': round(pairwise * 10, 1),
            'roster_gain': round(roster_delta * 10, 1),
            'velocity': round(velocity * 10, 1),
        },
    }


def recommend_workers_for_team_form(
    team=None,
    skill_ids=None,
    target_types=None,
    roster=None,
    query='',
    limit=50,
):
    """Кандидаты для формы команды с учётом состава и целей команды."""
    skill_ids = [int(x) for x in (skill_ids or []) if str(x).isdigit()]
    roster = list(roster or [])
    target_types = normalize_type_codes(target_types)
    if not target_types:
        if team and team.target_types:
            target_types = normalize_type_codes(team.target_types)
        elif team and team.dominant_task_type:
            target_types = [team.dominant_task_type]
        elif skill_ids:
            target_types = [_task_type_from_skill_ids(skill_ids)]
        else:
            target_types = ['BD']

    workers = User.objects.filter(role='worker')
    if team:
        workers = workers.distinct()

    if query:
        workers = workers.filter(
            Q(username__icontains=query) | Q(full_name__icontains=query)
        )

    if skill_ids:
        workers = workers.filter(skills__skill_id__in=skill_ids).distinct()

    results = []
    for w in workers:
        data = score_worker_for_team_composition(
            w,
            roster=roster,
            task_types=target_types,
            skill_ids=skill_ids,
            team=team,
        )
        row = {
            'id': w.id,
            'label': w.full_name or w.username,
            'username': w.username,
            'rating': w.rating,
            'velocity': round(float(getattr(w, 'velocity_score', 5.0)), 1),
            'specialization': w.specialization or '',
            **data,
        }
        if team:
            row['already_member'] = team.members.filter(pk=w.pk).exists()
        teams_count = w.teams.count()
        if teams_count:
            row['teams_count'] = teams_count
            row['teams_label'] = w.team_names_display()
        results.append(row)

    results.sort(key=lambda x: (-x['score'], -x['rating']))
    return results[:limit]
