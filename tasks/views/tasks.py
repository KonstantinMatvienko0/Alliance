from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User

from ..decorators import manager_required
from ..forms import TaskForm
from ..models import Task, Team
from ..querysets import worker_can_access_task
from ..services.task_completion import apply_task_outcome

from ..task_detail import tasks_detail_map_from_page

from .helpers import manager_tasks_queryset, save_task_from_form, task_editable


@login_required
def manager_tasks(request):
    if request.user.role != 'manager':
        return redirect('dashboard')

    show_create_modal = False
    show_edit_modal = False
    form = TaskForm()
    edit_form = None
    edit_task = None
    prefill_worker = None
    prefill_team = None

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'create')
        if form_type == 'edit':
            edit_task = get_object_or_404(Task, pk=request.POST.get('task_id'))
            if not task_editable(edit_task):
                return redirect('manager_tasks')
            edit_form = TaskForm(request.POST, instance=edit_task)
            if edit_form.is_valid():
                save_task_from_form(edit_form, request.user, is_create=False)
                return redirect('manager_tasks')
            show_edit_modal = True
            form = TaskForm()
        else:
            form = TaskForm(request.POST)
            if form.is_valid():
                save_task_from_form(form, request.user)
                return redirect('manager_tasks')
            show_create_modal = True
    else:
        form_initial = {}
        prefill_worker = None
        prefill_team = None
        if request.GET.get('create') or request.GET.get('assign_worker') or request.GET.get('assign_team'):
            show_create_modal = True
        if request.GET.get('assign_worker'):
            prefill_worker = get_object_or_404(
                User, pk=request.GET.get('assign_worker'), role='worker',
            )
            form_initial['assigned_to'] = prefill_worker
        elif request.GET.get('assign_team'):
            prefill_team = get_object_or_404(Team, pk=request.GET.get('assign_team'))
            form_initial['team'] = prefill_team
        if form_initial or show_create_modal:
            form = TaskForm(initial=form_initial)
        edit_id = request.GET.get('edit')
        if edit_id:
            edit_task = get_object_or_404(Task, pk=edit_id)
            if task_editable(edit_task):
                edit_form = TaskForm(instance=edit_task)
                show_edit_modal = True

    ctx = manager_tasks_queryset(request)
    ctx.update({
        'form': form,
        'edit_form': edit_form,
        'edit_task': edit_task,
        'show_create_modal': show_create_modal,
        'show_edit_modal': show_edit_modal,
        'type_choices': Task.TYPE_CHOICES,
        'prefill_worker': prefill_worker,
        'prefill_team': prefill_team,
        'tasks_detail_map': tasks_detail_map_from_page(ctx['page_obj'], request),
    })
    return render(request, 'tasks/manager_tasks.html', ctx)


@login_required
@require_POST
def start_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not worker_can_access_task(request.user, task):
        messages.error(request, 'Вы не можете взять эту задачу')
        return redirect('dashboard')
    if task.status != 'open':
        messages.error(request, 'Задачу можно взять в работу только из статуса «Открыта»')
        return redirect('dashboard')
    task.status = 'in_progress'
    task.save(update_fields=['status'])
    messages.success(request, f'Задача «{task.title}» в работе')
    return redirect('dashboard')


@login_required
@require_POST
def complete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not worker_can_access_task(request.user, task):
        messages.error(request, 'Вы не можете завершить эту задачу')
        return redirect('dashboard')
    if task.status in ('completed', 'failed'):
        return redirect('dashboard')

    success = not task.is_overdue()
    apply_task_outcome(task, success, completed_by=request.user)
    return redirect('dashboard')


@require_POST
@manager_required
def manager_complete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if task.status in ('completed', 'failed'):
        return redirect('manager_tasks')

    success = request.POST.get('success', 'true').lower() == 'true'
    if task.is_overdue():
        success = False
    apply_task_outcome(task, success, completed_by=request.user)
    return redirect('manager_tasks')


@require_POST
@manager_required
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.delete()
    if request.user.role == 'manager':
        return redirect('manager_tasks')
    return redirect('dashboard')
