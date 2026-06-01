from django.core.management.base import BaseCommand

from tasks.services.performance_metrics import refresh_all_metrics


class Command(BaseCommand):
    help = 'Recalculate worker and team performance characteristics from task history.'

    def handle(self, *args, **options):
        refresh_all_metrics()
        self.stdout.write(self.style.SUCCESS('Performance metrics updated.'))
