from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def manager_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'manager':
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper
