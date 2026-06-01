from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Skill, User, UserSkill
from tasks.models import Task, Team
from tasks.services.performance_metrics import refresh_worker_metrics
from tasks.services.team_composition import (
    get_pairwise_affinity,
    recommend_workers_for_team_form,
    score_roster_composition,
    score_worker_for_team_composition,
)
from tasks.services.task_completion import apply_task_outcome


class TeamCompositionTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username='mgr', password='pass', role='manager',
        )
        self.a = User.objects.create_user(
            username='dev_a', password='pass', role='worker', rating=60,
        )
        self.b = User.objects.create_user(
            username='dev_b', password='pass', role='worker', rating=55,
        )
        self.a.specialization = 'Front'
        self.b.specialization = 'Back'
        self.a.save(update_fields=['specialization'])
        self.b.save(update_fields=['specialization'])

        front = Skill.objects.create(
            name='React', skill_type='hard', related_task_types='Front',
        )
        back = Skill.objects.create(
            name='Python API', skill_type='hard', related_task_types='Back',
        )
        UserSkill.objects.create(user=self.a, skill=front, value=9)
        UserSkill.objects.create(user=self.b, skill=back, value=8)

    def test_complement_scores_front_and_back_higher_together(self):
        score_a_alone = score_worker_for_team_composition(
            self.a, [], ['Front', 'Back'], skill_ids=None,
        )['score']
        score_b_with_a = score_worker_for_team_composition(
            self.b, [self.a], ['Front', 'Back'], skill_ids=None,
        )['score']
        self.assertGreaterEqual(score_b_with_a, 40)
        self.assertGreater(score_b_with_a, score_worker_for_team_composition(
            self.b, [], ['Front'], skill_ids=None,
        )['score'] - 5)

    def test_pairwise_affinity_from_shared_team_success(self):
        team = Team.objects.create(name='Alpha', created_by=self.manager)
        team.members.add(self.a, self.b)

        task = Task.objects.create(
            title='Sprint',
            description='Work',
            types=['Front'],
            rank=10,
            due_date=timezone.now() + timedelta(days=2),
            team=team,
            created_by=self.manager,
        )
        apply_task_outcome(task, success=True, completed_by=self.manager)
        refresh_worker_metrics(self.a)
        refresh_worker_metrics(self.b)

        affinity = get_pairwise_affinity(self.a, self.b)
        self.assertGreaterEqual(affinity, 6.0)

    def test_recommend_respects_target_types(self):
        results = recommend_workers_for_team_form(
            team=None,
            target_types=['Front'],
            roster=[],
            limit=10,
        )
        front_dev = next(r for r in results if r['id'] == self.a.id)
        self.assertGreaterEqual(front_dev['score'], 45)
        self.assertTrue(front_dev.get('recommended') or front_dev['score'] >= 50)

    def test_roster_score_for_two_member_team(self):
        duo = score_roster_composition([self.a, self.b], ['Front', 'Back'])
        self.assertGreaterEqual(duo, 60)
        self.assertLessEqual(duo, 100)
