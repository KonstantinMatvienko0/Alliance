from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from tasks.models import Task
from tasks.services.task_completion import apply_task_outcome, format_outcome_message


class Command(BaseCommand):
    help = 'Помечает просроченные задачи как проваленные и обновляет рейтинг'

    def handle(self, *args, **options):
        overdue = Task.objects.filter(
            status__in=['open', 'in_progress'],
            due_date__lt=timezone.now(),
        ).filter(Q(assigned_to__isnull=False) | Q(team__isnull=False))

        count = 0
        for task in overdue:
            result = apply_task_outcome(task, success=False)
            if result:
                count += 1
                self.stdout.write(format_outcome_message(result))

        self.stdout.write(self.style.SUCCESS(f'Обработано просроченных задач: {count}'))
