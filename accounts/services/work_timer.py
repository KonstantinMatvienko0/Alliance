from datetime import timedelta

from django.utils import timezone

from accounts.models import User, WorkSession


def get_active_session(user):
    return WorkSession.objects.filter(user=user, ended_at__isnull=True).first()


def start_session(user):
    """Запускает новую сессию; закрывает зависшую активную, если есть."""
    active = get_active_session(user)
    if active:
        return active, False
    session = WorkSession.objects.create(user=user)
    return session, True


def stop_session(user):
    """Останавливает активную сессию. Возвращает (session, stopped)."""
    active = get_active_session(user)
    if not active:
        return None, False
    active.ended_at = timezone.now()
    active.save(update_fields=['ended_at'])
    return active, True


def session_status_payload(user):
    active = get_active_session(user)
    if not active:
        return {'active': False, 'elapsed_seconds': 0, 'started_at': None}
    return {
        'active': True,
        'started_at': active.started_at.isoformat(),
        'elapsed_seconds': active.duration_seconds(),
        'session_id': active.pk,
    }


def format_duration(total_seconds):
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def get_workers_work_summary():
    """Сводка для менеджера: кто работает сейчас и сколько отработал сегодня."""
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    workers = User.objects.filter(role='worker').prefetch_related('teams').order_by('username')
    summary = []

    for worker in workers:
        active = get_active_session(worker)
        sessions_today = WorkSession.objects.filter(user=worker, started_at__gte=today_start)
        today_seconds = sum(s.duration_seconds() for s in sessions_today)

        week_start = today_start - timedelta(days=today_start.weekday())
        sessions_week = WorkSession.objects.filter(user=worker, started_at__gte=week_start)
        week_seconds = sum(s.duration_seconds() for s in sessions_week)

        summary.append({
            'worker': worker,
            'is_working': active is not None,
            'active_elapsed': active.duration_seconds() if active else 0,
            'active_started_at': active.started_at if active else None,
            'today_seconds': today_seconds,
            'week_seconds': week_seconds,
            'today_display': format_duration(today_seconds),
            'week_display': format_duration(week_seconds),
            'active_display': format_duration(active.duration_seconds()) if active else '—',
        })

    return summary
