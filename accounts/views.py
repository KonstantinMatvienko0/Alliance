from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from tasks.decorators import manager_required

from .forms import CustomUserCreationForm, UserProfileForm, UserSkillsForm
from .models import Skill, User, UserSkill


def register(request):
    """Регистрация нового пользователя (роль worker назначается автоматически)."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def edit_profile(request, username):
    """Редактирование профиля работника (сам работник или менеджер)."""
    worker = get_object_or_404(User, username=username, role='worker')
    if request.user != worker and request.user.role != 'manager':
        messages.error(request, 'У вас нет прав для редактирования этого профиля')
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
            messages.success(request, f'Навыки для {worker.username} обновлены')
            return redirect('worker_profile', username=username)
    else:
        form = UserSkillsForm(worker)

    return render(request, 'accounts/edit_skills.html', {'form': form, 'worker': worker})
