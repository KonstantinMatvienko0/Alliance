from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.db.models import Avg
from django.utils import timezone

from .ui_text import PRIORITY_LABELS, STATUS_UI_LABELS


def default_task_types():
    return ['BD']


class Task(models.Model):
    TYPE_CHOICES = [
        ('BD', 'BD'),
        ('Front', 'Front'),
        ('Backlog', 'Backlog'),
        ('Canceled', 'Canceled'),
        ('Design', 'Design'),
        ('DB', 'DB'),
        ('Back', 'Back'),
    ]
    STATUS_CHOICES = [
        ('open', 'Открыта'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнена'),
        ('failed', 'Провалена'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    link = models.URLField(max_length=500, blank=True, help_text='Внешняя ссылка (например, репозиторий GitHub)')
    types = models.JSONField(default=default_task_types, blank=True)
    rank = models.IntegerField(default=350, help_text="Изменение рейтинга при выполнении")
    due_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tasks'
    )
    team = models.ForeignKey(
        'Team',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tasks'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_tasks',
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    def is_overdue(self):
        return self.status not in ('completed', 'failed') and timezone.now() > self.due_date

    def priority_label(self):
        if self.rank > 600:
            key = 'High'
        elif self.rank > 300:
            key = 'Medium'
        else:
            key = 'Low'
        return PRIORITY_LABELS[key]

    def status_ui_label(self):
        return STATUS_UI_LABELS.get(self.status, self.status)

    @property
    def task_code(self):
        return f'TASK-{self.pk:04d}'

    @property
    def primary_type(self):
        return self.types[0] if self.types else 'BD'

    def clean(self):
        if self.assigned_to_id and self.team_id:
            raise ValidationError('Назначьте либо работника, либо команду, но не обоих.')
        if not self.assigned_to_id and not self.team_id:
            raise ValidationError('Укажите работника или команду.')
        valid = {code for code, _ in self.TYPE_CHOICES}
        normalized = []
        for code in self.types or []:
            if code not in valid:
                raise ValidationError(f'Неизвестный тип задачи: {code}')
            if code not in normalized:
                normalized.append(code)
        if not normalized:
            raise ValidationError('Укажите хотя бы один тип задачи.')
        self.types = normalized

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    manager_notes = models.TextField(
        blank=True,
        verbose_name='Заметки менеджера',
        help_text='Видны только менеджерам',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='teams',
        blank=True,
        limit_choices_to={'role': 'worker'},
        verbose_name='Участники',
    )
    target_types = models.JSONField(
        default=list,
        blank=True,
        help_text='Типы задач, под которые собрана команда',
    )
    synergy_score = models.FloatField(
        default=5.0,
        help_text='Слаженность команды по завершённым командным задачам (1–10)',
    )
    cohesion_score = models.FloatField(
        default=5.0,
        help_text='Средняя совместимость участников (1–10)',
    )
    dominant_task_type = models.CharField(max_length=20, blank=True)
    tasks_completed_count = models.PositiveIntegerField(default=0)
    tasks_failed_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_teams'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def get_members(self):
        return self.members.filter(role='worker').distinct()

    def total_rating(self):
        return sum(member.rating for member in self.get_members())

    def priority_label(self):
        avg_rank = self.tasks.aggregate(avg=Avg('rank'))['avg'] or 0
        if avg_rank > 600:
            key = 'High'
        elif avg_rank > 300:
            key = 'Medium'
        else:
            key = 'Low'
        return PRIORITY_LABELS[key]

    def __str__(self):
        return self.name