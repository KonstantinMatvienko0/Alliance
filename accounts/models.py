from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('manager', 'Менеджер'),
        ('worker', 'Работник'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='worker')
    rating = models.IntegerField(default=0)

    # Личные данные
    full_name = models.CharField(max_length=100, blank=True, verbose_name='Полное имя')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    address = models.CharField(max_length=200, blank=True, verbose_name='Адрес')
    website = models.URLField(blank=True, verbose_name='Сайт')
    github = models.CharField(max_length=100, blank=True, verbose_name='GitHub')
    twitter = models.CharField(max_length=100, blank=True, verbose_name='Twitter')
    telegram = models.CharField(max_length=100, blank=True, verbose_name='Telegram')

    # Характеристики для рекомендаций (обновляются по статистике задач)
    specialization = models.CharField(
        max_length=20,
        blank=True,
        help_text='Основная специализация (код типа задачи: Front, Back, …)',
    )
    collaboration_score = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Насколько эффективен в команде (1–10)',
    )
    reliability_score = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Надёжность по solo-задачам (1–10)',
    )
    solo_tasks_completed = models.PositiveIntegerField(default=0)
    solo_tasks_failed = models.PositiveIntegerField(default=0)
    team_tasks_completed = models.PositiveIntegerField(default=0)
    team_tasks_failed = models.PositiveIntegerField(default=0)
    velocity_score = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Скорость и соблюдение сроков (1–10)',
    )
    type_stats = models.JSONField(
        default=dict,
        blank=True,
        help_text='Статистика по типам задач: completed, failed, on_time',
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def team_names_display(self, limit=3):
        """Названия команд для UI."""
        names = list(self.teams.values_list('name', flat=True)[:limit])
        if not names:
            return ''
        extra = self.teams.count() - len(names)
        text = ', '.join(names)
        if extra > 0:
            text += f' +{extra}'
        return text

    def shares_team_with(self, other):
        if not other or not other.pk:
            return False
        return self.teams.filter(pk__in=other.teams.values('pk')).exists()


class Skill(models.Model):
    SKILL_TYPES = (
        ('soft', 'Мягкий навык'),
        ('hard', 'Технический навык'),
    )
    name = models.CharField(max_length=100, unique=True)
    skill_type = models.CharField(max_length=10, choices=SKILL_TYPES)
    related_task_types = models.CharField(
        max_length=120,
        blank=True,
        help_text='Типы задач через запятую: Front,Back,Design',
    )
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome класс, например 'fa-users'")

    def __str__(self):
        return f"{self.name} ({self.get_skill_type_display()})"


class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    value = models.PositiveSmallIntegerField(
        default=5,
        help_text='Оценка от 1 до 10',
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )

    class Meta:
        unique_together = ('user', 'skill')

    def __str__(self):
        return f"{self.user.username} - {self.skill.name}: {self.value}"


class WorkSession(models.Model):
    """Сессия рабочего времени: работник включает при работе, выключает при уходе."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='work_sessions',
        limit_choices_to={'role': 'worker'},
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Рабочая сессия'
        verbose_name_plural = 'Рабочие сессии'

    @property
    def is_active(self):
        return self.ended_at is None

    def duration_seconds(self):
        end = self.ended_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds()))

    def __str__(self):
        status = 'active' if self.is_active else 'done'
        return f'{self.user.username} {status} ({self.started_at:%d.%m %H:%M})'