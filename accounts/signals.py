from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

from .services.work_timer import stop_session


@receiver(user_logged_out)
def stop_work_timer_on_logout(sender, request, user, **kwargs):
    if user and getattr(user, 'role', None) == 'worker':
        stop_session(user)
