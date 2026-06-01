from tasks.models import Task


def split_rating_shares(amount, recipient_count):
    """
    Делит amount между recipient_count участниками.
    Остаток от деления получает первый участник (стабильный порядок по pk в get_rating_recipients).
    """
    if recipient_count <= 0:
        return []
    quotient, remainder = divmod(amount, recipient_count)
    return [quotient + (remainder if index == 0 else 0) for index in range(recipient_count)]


def get_rating_recipients(task):
    """Пользователи, которым начисляется или снимается рейтинг."""
    if task.assigned_to_id:
        return [task.assigned_to]
    if task.team_id:
        return list(task.team.members.filter(role='worker').order_by('pk'))
    return []


def rating_sign(success):
    return 1 if success else -1


def rating_change_for_user(task, user):
    """Изменение рейтинга для пользователя по уже завершённой задаче."""
    if task.status not in ('completed', 'failed'):
        return 0

    recipients = get_rating_recipients(task)
    if not recipients:
        return 0

    recipient_ids = [recipient.id for recipient in recipients]
    if user.id not in recipient_ids:
        return 0

    sign = rating_sign(task.status == 'completed')
    amount = abs(task.rank)
    shares = split_rating_shares(amount, len(recipients))
    index = recipient_ids.index(user.id)
    return sign * shares[index]
