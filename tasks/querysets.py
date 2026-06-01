from django.db.models import Q


def tasks_q_for_worker(user):
    """Задачи, доступные работнику: личные и всех его команд."""
    q = Q(assigned_to=user)
    team_ids = list(user.teams.values_list('pk', flat=True))
    if team_ids:
        q |= Q(team_id__in=team_ids, assigned_to__isnull=True)
    return q


def tasks_q_for_worker_profile(worker):
    """Задачи для отображения в профиле работника."""
    return tasks_q_for_worker(worker)


def worker_can_access_task(user, task):
    if task.assigned_to_id == user.id:
        return True
    if task.team_id:
        return user.teams.filter(pk=task.team_id).exists()
    return False
