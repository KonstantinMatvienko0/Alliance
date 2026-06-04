from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from tasks.decorators import manager_required

from .forms import CustomUserCreationForm, UserProfileForm, UserSkillsForm
from .models import Skill, User, UserSkill


def register(request):
    """Регистрация: работник по умолчанию; менеджер — с кодом MANAGER_REGISTRATION_CODE."""
    manager_signup_enabled = bool(getattr(settings, 'MANAGER_REGISTRATION_CODE', ''))
    if request.method == 'POST':
        form = CustomUserCreationForm(
            request.POST,
            manager_signup_enabled=manager_signup_enabled,
        )
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm(manager_signup_enabled=manager_signup_enabled)
    show_manager_code_hint = manager_signup_enabled and settings.DEBUG
    return render(request, 'accounts/register.html', {
        'form': form,
        'manager_signup_enabled': manager_signup_enabled,
        'show_manager_code_hint': show_manager_code_hint,
        'manager_invite_hint': settings.MANAGER_REGISTRATION_CODE if show_manager_code_hint else '',
    })


@login_required
def edit_profile(request, username):
    """Редактирование профиля работника (сам работник или менеджер)."""
    worker = get_object_or_404(User, username=username, role='worker')
    if request.user != worker and request.user.role != 'manager':
        return redirect('worker_profile', username=username)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=worker)
        if form.is_valid():
            form.save()
            return redirect('worker_profile', username=username)
    else:
        form = UserProfileForm(instance=worker)

    return render(request, 'accounts/edit_profile.html', {'form': form, 'worker': worker})


@manager_required
def edit_skills(request, username):
    """Редактирование навыков работника (только менеджер)."""
    worker = get_object_or_404(User, username=username, role='worker')

    if request.method == 'POST':
        form = UserSkillsForm(worker, request.POST)
        if form.is_valid():
            for skill in Skill.objects.all():
                value = form.cleaned_data[f'skill_{skill.id}']
                user_skill, _created = UserSkill.objects.get_or_create(user=worker, skill=skill)
                user_skill.value = value
                user_skill.save()
            return redirect('worker_profile', username=username)
    else:
        form = UserSkillsForm(worker)

    return render(request, 'accounts/edit_skills.html', {'form': form, 'worker': worker})
