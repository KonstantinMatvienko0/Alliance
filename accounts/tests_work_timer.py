from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User, WorkSession
from accounts.services.work_timer import get_active_session, start_session, stop_session


class WorkTimerServiceTests(TestCase):
    def setUp(self):
        self.worker = User.objects.create_user(username='wrk', password='pass', role='worker')

    def test_start_and_stop_session(self):
        session, created = start_session(self.worker)
        self.assertTrue(created)
        self.assertIsNone(session.ended_at)

        active, stopped = stop_session(self.worker)
        self.assertTrue(stopped)
        self.assertIsNotNone(active.ended_at)
        self.assertIsNone(get_active_session(self.worker))

    def test_start_twice_returns_same_session(self):
        first, _ = start_session(self.worker)
        second, created = start_session(self.worker)
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)


class WorkTimerViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.worker = User.objects.create_user(username='wrk', password='pass', role='worker')
        self.manager = User.objects.create_user(username='mgr', password='pass', role='manager')

    def test_worker_can_start_timer(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.post(reverse('work_timer_toggle'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['active'])
        self.assertEqual(WorkSession.objects.filter(user=self.worker, ended_at__isnull=True).count(), 1)

    def test_stop_on_logout(self):
        start_session(self.worker)
        self.client.login(username='wrk', password='pass')
        self.client.post(reverse('logout'))
        self.assertIsNone(get_active_session(self.worker))

    def test_manager_dashboard_shows_work_summary(self):
        start_session(self.worker)
        self.client.login(username='mgr', password='pass')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Рабочее время сотрудников')
        self.assertContains(response, 'работаю')
