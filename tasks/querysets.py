from django.db.models import Case, IntegerField, Q, Value, When


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


def worker_today_focus_tasks(active_qs, *, now, start_of_day, end_of_day, limit=8):
    """
    Задачи для блока «Фокус на сегодня»:
    просроченные и с дедлайном сегодня, плюс новые назначения (созданы сегодня).
    """
    return (
        active_qs.filter(
            Q(due_date__lt=end_of_day) | Q(created_at__gte=start_of_day),
        )
        .annotate(
            focus_priority=Case(
                When(due_date__lt=now, then=0),
                When(
                    due_date__gte=start_of_day,
                    due_date__lt=end_of_day,
                    then=1,
                ),
                default=2,
                output_field=IntegerField(),
            ),
        )
        .order_by('focus_priority', 'due_date', '-created_at')[:limit]
    )


def worker_can_access_task(user, task):
    if task.assigned_to_id == user.id:
        return True
    if task.team_id:
        return user.teams.filter(pk=task.team_id).exists()
    return False
