from django.db import transaction
from django.utils import timezone

from tasks.models import Task
from tasks.services.performance_metrics import refresh_after_task_outcome


def get_rating_recipients(task):
    """Пользователи, которым начисляется или снимается рейтинг."""
    if task.assigned_to_id:
        return [task.assigned_to]
    if task.team_id:
        return list(task.team.members.filter(role='worker'))
    return []


@transaction.atomic
def apply_task_outcome(task, success, completed_by=None):
    """
    Завершает задачу и меняет рейтинг исполнителям.
    Возвращает dict с деталями или None, если задача уже закрыта.
    """
    task = Task.objects.select_for_update().get(pk=task.pk)

    if task.status in ('completed', 'failed'):
        return None

    recipients = get_rating_recipients(task)
    amount = abs(task.rank)
    sign = 1 if success else -1

    if recipients:
        quotient, remainder = divmod(amount, len(recipients))
        for index, user in enumerate(recipients):
            change = sign * (quotient + (remainder if index == 0 else 0))
            user.rating = max(0, user.rating + change)
            user.save(update_fields=['rating'])

    task.status = 'completed' if success else 'failed'
    task.completed_by = completed_by
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_by', 'completed_at'])
    refresh_after_task_outcome(task)

    return {
        'task': task,
        'success': success,
        'recipients': recipients,
        'amount': amount,
        'completed_by': completed_by,
    }


def format_outcome_message(result):
    task = result['task']
    recipients = result['recipients']
    amount = result['amount']
    closer = result.get('completed_by')

    closer_note = ''
    if closer and len(recipients) > 1:
        closer_note = f' Закрыл: {closer.username}.'

    if result['success']:
        if len(recipients) == 1:
            user = recipients[0]
            return (
                f'✅ Задача «{task.title}» выполнена! '
                f'Рейтинг {user.username} изменён на +{amount}.{closer_note}'
            )
        if recipients:
            names = ', '.join(u.username for u in recipients)
            per_user, _ = divmod(amount, len(recipients))
            return (
                f'✅ Задача «{task.title}» выполнена! '
                f'Рейтинг команды ({names}): +{per_user} каждому.{closer_note}'
            )
        return f'✅ Задача «{task.title}» выполнена (исполнители не назначены).'

    if len(recipients) == 1:
        user = recipients[0]
        return (
            f'❌ Задача «{task.title}» провалена! '
            f'Рейтинг {user.username} снижен на {amount}.{closer_note}'
        )
    if recipients:
        names = ', '.join(u.username for u in recipients)
        per_user, _ = divmod(amount, len(recipients))
        return (
            f'❌ Задача «{task.title}» провалена! '
            f'Рейтинг команды ({names}): −{per_user} каждому.{closer_note}'
        )
    return f'❌ Задача «{task.title}» провалена (исполнители не назначены).'
