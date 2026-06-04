from django.urls import path

from .views import api
from .views.dashboard import dashboard, ranked_statistic, worker_home, worker_tasks
from .views.tasks import (
    complete_task,
    delete_task,
    manager_complete_task,
    manager_tasks,
    review_task,
    start_task,
)
from .views.teams import (
    team_create,
    team_delete,
    team_detail,
    team_edit,
    team_list,
    team_save_notes,
    worker_team,
    worker_team_detail,
)
from .views.workers import manager_workers, worker_profile

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('tasks/', worker_tasks, name='worker_tasks'),
    path('ranked/', ranked_statistic, name='ranked_statistic'),
    path('my-team/', worker_team, name='worker_team'),
    path('my-team/<int:pk>/', worker_team_detail, name='worker_team_detail'),
    path('manager/tasks/', manager_tasks, name='manager_tasks'),
    path('manager/workers/', manager_workers, name='manager_workers'),
    path('task/<int:pk>/start/', start_task, name='start_task'),
    path('task/<int:pk>/complete/', complete_task, name='complete_task'),
    path('task/<int:pk>/review/', review_task, name='review_task'),
    path('task/<int:pk>/manager-complete/', manager_complete_task, name='manager_complete_task'),
    path('task/<int:pk>/delete/', delete_task, name='delete_task'),
    path('profile/<str:username>/', worker_profile, name='worker_profile'),
    path('teams/', team_list, name='team_list'),
    path('teams/create/', team_create, name='team_create'),
    path('teams/<int:pk>/', team_detail, name='team_detail'),
    path('teams/<int:pk>/edit/', team_edit, name='team_edit'),
    path('teams/<int:pk>/notes/', team_save_notes, name='team_save_notes'),
    path('teams/<int:pk>/delete/', team_delete, name='team_delete'),
    path('filter-workers/', api.filter_workers_by_skill, name='filter_workers'),
    path('recommend-assignees/', api.recommend_assignees, name='recommend_assignees'),
    path('teams/<int:pk>/recommend-members/', api.recommend_team_members, name='recommend_team_members'),
    path('recommend-members/', api.recommend_team_members_new, name='recommend_team_members_new'),
]
