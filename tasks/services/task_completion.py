from django.db import transaction
from django.utils import timezone

from tasks.models import Task
from tasks.services.performance_metrics import refresh_after_task_outcome
from tasks.services.rating import get_rating_recipients, split_rating_shares


@transaction.atomic
def submit_task_for_review(task, submitted_by):
    """
    Работник отправляет задачу на проверку менеджеру. Рейтинг не меняется.
    """
    task = Task.objects.select_for_update().get(pk=task.pk)
    if task.status != 'in_progress':
        return None
    task.status = 'pending_review'
    task.submitted_by = submitted_by
    task.submitted_at = timezone.now()
    task.save(update_fields=['status', 'submitted_by', 'submitted_at'])
    return task


@transaction.atomic
def apply_task_outcome(task, success, completed_by=None):
    """
    Менеджер принимает или отклоняет выполнение. Рейтинг начисляется здесь.
    Задача должна быть в статусе «На проверке».
    """
    task = Task.objects.select_for_update().get(pk=task.pk)

    if task.status != 'pending_review':
        return None

    recipients = get_rating_recipients(task)
    amount = abs(task.rank)
    sign = 1 if success else -1

    if recipients:
        shares = split_rating_shares(amount, len(recipients))
        for user, share in zip(recipients, shares):
            user.rating = max(0, user.rating + sign * share)
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
    if closer:
        closer_note = f' Проверил: {closer.username}.'

    if result['success']:
        if len(recipients) == 1:
            user = recipients[0]
            return (
                f'Задача «{task.title}» принята. '
                f'Рейтинг {user.username}: +{amount}.{closer_note}'
            )
        if recipients:
            names = ', '.join(u.username for u in recipients)
            per_user, _ = divmod(amount, len(recipients))
            return (
                f'Задача «{task.title}» принята. '
                f'Рейтинг команды ({names}): +{per_user} каждому.{closer_note}'
            )
        return f'Задача «{task.title}» принята (исполнители не назначены).'

    if len(recipients) == 1:
        user = recipients[0]
        return (
            f'Задача «{task.title}» отклонена. '
            f'Рейтинг {user.username}: −{amount}.{closer_note}'
        )
    if recipients:
        names = ', '.join(u.username for u in recipients)
        per_user, _ = divmod(amount, len(recipients))
        return (
            f'Задача «{task.title}» отклонена. '
            f'Рейтинг команды ({names}): −{per_user} каждому.{closer_note}'
        )
    return f'Задача «{task.title}» отклонена (исполнители не назначены).'
