from django.urls import path

from . import views
from . import work_timer_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/<str:username>/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/skills/', views.edit_skills, name='edit_skills'),
    path('work-timer/status/', work_timer_views.work_timer_status, name='work_timer_status'),
    path('work-timer/start/', work_timer_views.work_timer_start, name='work_timer_start'),
    path('work-timer/stop/', work_timer_views.work_timer_stop, name='work_timer_stop'),
    path('work-timer/toggle/', work_timer_views.work_timer_toggle, name='work_timer_toggle'),
]