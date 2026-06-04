from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Skill, User, UserSkill
from tasks.models import Task, Team
from tasks.services.performance_metrics import refresh_all_metrics
from tasks.services.recommendations import (
    recommend_workers_for_task,
    score_worker_for_task,
)
from tasks.services.task_completion import apply_task_outcome, submit_task_for_review


class RecommendationTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username='mgr', password='pass', role='manager',
        )
        self.worker = User.objects.create_user(
            username='front_dev', password='pass', role='worker', rating=80,
        )
        self.worker.specialization = 'Front'
        self.worker.save(update_fields=['specialization'])
        skill = Skill.objects.create(name='React UI', skill_type='hard', related_task_types='Front')
        UserSkill.objects.create(user=self.worker, skill=skill, value=9)

    def test_score_worker_specialization_boost(self):
        data = score_worker_for_task(self.worker, 'Front')
        self.assertGreaterEqual(data['score'], 40)

    def test_recommend_api(self):
        self.client.login(username='mgr', password='pass')
        response = self.client.get(
            reverse('recommend_assignees'),
            {'type': 'Front', 'rank': 350},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('workers', payload)
        self.assertTrue(any(w['id'] == self.worker.id for w in payload['workers']))

    def test_metrics_refresh_after_completion(self):
        task = Task.objects.create(
            title='T',
            description='D',
            types=['Front'],
            rank=10,
            due_date=timezone.now() + timedelta(days=1),
            assigned_to=self.worker,
            created_by=self.manager,
        )
        task.status = 'in_progress'
        task.save(update_fields=['status'])
        submit_task_for_review(task, self.worker)
        apply_task_outcome(task, success=True, completed_by=self.manager)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.solo_tasks_completed, 1)
        self.assertGreaterEqual(self.worker.reliability_score, 5)
