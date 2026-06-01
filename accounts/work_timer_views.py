import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .services.work_timer import (
    format_duration,
    session_status_payload,
    start_session,
    stop_session,
)


def _worker_only(user):
    return user.is_authenticated and user.role == 'worker'


@login_required
@require_GET
def work_timer_status(request):
    if not _worker_only(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    payload = session_status_payload(request.user)
    payload['display'] = format_duration(payload['elapsed_seconds'])
    return JsonResponse(payload)


@login_required
@require_POST
def work_timer_start(request):
    if not _worker_only(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    session, created = start_session(request.user)
    payload = session_status_payload(request.user)
    payload['display'] = format_duration(payload['elapsed_seconds'])
    payload['created'] = created
    return JsonResponse(payload)


@login_required
@require_POST
def work_timer_stop(request):
    if not _worker_only(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    session, stopped = stop_session(request.user)
    duration = session.duration_seconds() if session else 0
    return JsonResponse({
        'active': False,
        'stopped': stopped,
        'duration_seconds': duration,
        'display': format_duration(duration),
    })


@login_required
@require_POST
def work_timer_toggle(request):
    """Один endpoint для переключателя: старт или стоп."""
    if not _worker_only(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    from .services.work_timer import get_active_session

    if get_active_session(request.user):
        session, stopped = stop_session(request.user)
        duration = session.duration_seconds() if session else 0
        return JsonResponse({
            'active': False,
            'stopped': stopped,
            'duration_seconds': duration,
            'display': format_duration(duration),
        })

    session, created = start_session(request.user)
    payload = session_status_payload(request.user)
    payload['display'] = format_duration(payload['elapsed_seconds'])
    payload['created'] = created
    return JsonResponse(payload)
