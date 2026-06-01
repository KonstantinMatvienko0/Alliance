"""HTTP views for the tasks app."""

from .api import (
    filter_workers_by_skill,
    recommend_assignees,
    recommend_team_members,
    recommend_team_members_new,
)
from .dashboard import dashboard, manager_dashboard, ranked_statistic, worker_home, worker_tasks
from .tasks import (
    complete_task,
    delete_task,
    manager_complete_task,
    manager_tasks,
    start_task,
)
from .teams import (
    team_create,
    team_delete,
    team_detail,
    team_edit,
    team_list,
    worker_team,
    worker_team_detail,
)
from .workers import manager_workers, worker_profile

__all__ = [
    'dashboard',
    'manager_dashboard',
    'worker_home',
    'worker_tasks',
    'ranked_statistic',
    'manager_tasks',
    'start_task',
    'complete_task',
    'manager_complete_task',
    'delete_task',
    'worker_team',
    'worker_team_detail',
    'worker_profile',
    'manager_workers',
    'team_list',
    'team_create',
    'team_edit',
    'team_delete',
    'team_detail',
    'recommend_assignees',
    'recommend_team_members',
    'recommend_team_members_new',
    'filter_workers_by_skill',
]
