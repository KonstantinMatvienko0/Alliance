from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from tasks.models import Task, Team
from tasks.querysets import tasks_q_for_worker
from tasks.services.task_completion import apply_task_outcome, submit_task_for_review


class TaskCompletionTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username='mgr', password='pass', role='manager',
        )
        self.worker = User.objects.create_user(
            username='wrk', password='pass', role='worker', rating=100,
        )
        self.worker2 = User.objects.create_user(
            username='wrk2', password='pass', role='worker', rating=100,
        )
        self.team = Team.objects.create(name='Alpha', created_by=self.manager)
        self.team.members.add(self.worker, self.worker2)

    def _task(self, **kwargs):
        defaults = {
            'title': 'Test',
            'description': 'Desc',
            'due_date': timezone.now() + timedelta(days=1),
            'created_by': self.manager,
        }
        defaults.update(kwargs)
        return Task.objects.create(**defaults)

    def test_solo_task_success_updates_rating(self):
        task = self._task(assigned_to=self.worker, rank=50)
        task.status = 'in_progress'
        task.save(update_fields=['status'])
        submit_task_for_review(task, self.worker)
        apply_task_outcome(task, success=True, completed_by=self.manager)
        self.worker.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(self.worker.rating, 150)
        self.assertEqual(task.status, 'completed')
        self.assertEqual(task.completed_by, self.manager)

    def test_team_task_splits_rating(self):
        task = self._task(team=self.team, rank=101)
        task.status = 'in_progress'
        task.save(update_fields=['status'])
        submit_task_for_review(task, self.worker)
        apply_task_outcome(task, success=True, completed_by=self.manager)
        self.worker.refresh_from_db()
        self.worker2.refresh_from_db()
        self.assertEqual(self.worker.rating, 151)
        self.assertEqual(self.worker2.rating, 150)

    def test_rating_does_not_go_below_zero(self):
        task = self._task(assigned_to=self.worker, rank=500)
        task.status = 'in_progress'
        task.save(update_fields=['status'])
        self.worker.rating = 10
        self.worker.save(update_fields=['rating'])
        submit_task_for_review(task, self.worker)
        apply_task_outcome(task, success=False, completed_by=self.manager)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.rating, 0)

    def test_already_completed_returns_none(self):
        task = self._task(assigned_to=self.worker, status='completed')
        self.assertIsNone(apply_task_outcome(task, success=True))

    def test_submit_does_not_change_rating(self):
        task = self._task(assigned_to=self.worker, rank=50)
        task.status = 'in_progress'
        task.save(update_fields=['status'])
        submit_task_for_review(task, self.worker)
        self.worker.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(self.worker.rating, 100)
        self.assertEqual(task.status, 'pending_review')
        self.assertEqual(task.submitted_by, self.worker)


class WorkerTaskFilterTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='mgr', password='pass', role='manager')
        self.worker_a = User.objects.create_user(username='a', password='pass', role='worker')
        self.worker_b = User.objects.create_user(username='b', password='pass', role='worker')
        self.team = Team.objects.create(name='T', created_by=self.manager)
        self.team.members.add(self.worker_b)

        due = timezone.now() + timedelta(days=1)
        self.task_a = Task.objects.create(
            title='A solo', description='d', assigned_to=self.worker_a,
            rank=10, due_date=due, created_by=self.manager,
        )
        self.task_b = Task.objects.create(
            title='B team', description='d', team=self.team,
            rank=10, due_date=due, created_by=self.manager,
        )

    def test_worker_without_team_sees_only_own_tasks(self):
        visible = Task.objects.filter(tasks_q_for_worker(self.worker_a))
        self.assertEqual(list(visible), [self.task_a])

    def test_worker_with_team_sees_team_tasks(self):
        visible = Task.objects.filter(tasks_q_for_worker(self.worker_b))
        self.assertEqual(set(visible), {self.task_b})


class TaskViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username='mgr', password='pass', role='manager',
        )
        self.worker = User.objects.create_user(
            username='wrk', password='pass', role='worker',
        )
        self.other = User.objects.create_user(
            username='other', password='pass', role='worker',
        )
        self.task = Task.objects.create(
            title='Solo',
            description='D',
            assigned_to=self.worker,
            rank=10,
            due_date=timezone.now() + timedelta(days=1),
            created_by=self.manager,
        )

    def test_complete_task_requires_post(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('complete_task', args=[self.task.pk]))
        self.assertEqual(response.status_code, 405)

    def test_worker_cannot_complete_others_task(self):
        self.client.login(username='other', password='pass')
        response = self.client.post(reverse('complete_task', args=[self.task.pk]))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'open')

    def test_start_task_sets_in_progress(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.post(reverse('start_task', args=[self.task.pk]))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'in_progress')

    def test_worker_submit_then_manager_approves_rating(self):
        self.client.login(username='wrk', password='pass')
        self.client.post(reverse('start_task', args=[self.task.pk]))
        self.client.post(reverse('complete_task', args=[self.task.pk]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'pending_review')
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.rating, 0)

        self.client.login(username='mgr', password='pass')
        self.client.post(reverse('review_task', args=[self.task.pk]), {'action': 'approve'})
        self.task.refresh_from_db()
        self.worker.refresh_from_db()
        self.assertEqual(self.task.status, 'completed')
        self.assertEqual(self.worker.rating, 10)

    def test_start_task_no_flash_banner_on_dashboard(self):
        self.client.login(username='wrk', password='pass')
        self.client.post(reverse('start_task', args=[self.task.pk]))
        home = self.client.get(reverse('dashboard'))
        self.assertNotContains(home, 'wa-messages')
        self.assertNotContains(home, 'Задача «Solo» в работе')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'in_progress')

    def test_delete_task_requires_post(self):
        self.client.login(username='mgr', password='pass')
        response = self.client.get(reverse('delete_task', args=[self.task.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())


class RegistrationTests(TestCase):
    def test_register_page_uses_auth_layout(self):
        response = Client().get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'auth-shell')
        self.assertContains(response, 'auth-card')
        self.assertNotContains(response, 'form.as_p')

    @override_settings(MANAGER_REGISTRATION_CODE='')
    def test_register_creates_worker_by_default(self):
        response = Client().post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newuser')
        self.assertEqual(user.role, 'worker')

    @override_settings(MANAGER_REGISTRATION_CODE='invite-mgr-42')
    def test_register_manager_requires_valid_code(self):
        bad = Client().post(reverse('register'), {
            'username': 'badmgr',
            'email': 'bad@test.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'role': 'manager',
            'manager_invite_code': 'wrong',
        })
        self.assertEqual(bad.status_code, 200)
        self.assertFalse(User.objects.filter(username='badmgr').exists())

        ok = Client().post(reverse('register'), {
            'username': 'goodmgr',
            'email': 'mgr@test.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'role': 'manager',
            'manager_invite_code': 'invite-mgr-42',
        })
        self.assertEqual(ok.status_code, 302)
        self.assertEqual(User.objects.get(username='goodmgr').role, 'manager')


class ProfileAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username='mgr', password='pass', role='manager',
        )
        self.worker = User.objects.create_user(
            username='wrk', password='pass', role='worker',
        )
        self.other = User.objects.create_user(
            username='other', password='pass', role='worker',
        )
        self.teammate = User.objects.create_user(
            username='mate', password='pass', role='worker',
        )
        self.team = Team.objects.create(name='Squad', created_by=self.manager)
        self.team.members.add(self.worker, self.teammate)

    def test_worker_cannot_view_other_profile(self):
        self.client.login(username='other', password='pass')
        response = self.client.get(reverse('worker_profile', args=['wrk']))
        self.assertEqual(response.status_code, 302)

    def test_worker_can_view_teammate_profile(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('worker_profile', args=['mate']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'mg-back-btn')
        self.assertContains(response, 'ch-name">mate')
        self.assertContains(response, 'href="/profile/wrk/"')
        self.assertNotContains(response, 'Редактировать профиль')

    def test_manager_views_worker_profile_in_manager_shell(self):
        self.client.login(username='mgr', password='pass')
        response = self.client.get(reverse('worker_profile', args=['wrk']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'worker-app--manager')
        self.assertContains(response, 'mg-back-btn')
        self.assertContains(response, 'Назад')
        self.assertNotContains(response, 'Профиль сотрудника')
        self.assertNotContains(response, 'Просмотр как менеджер')
        self.assertNotContains(response, 'wa-subnav__link--active">Характеристики')

    def test_worker_cannot_edit_skills(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('edit_skills', args=['other']))
        self.assertEqual(response.status_code, 302)

    def test_manager_can_edit_worker_skills(self):
        self.client.login(username='mgr', password='pass')
        response = self.client.get(reverse('edit_skills', args=['wrk']))
        self.assertEqual(response.status_code, 200)


class WorkerHomeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(username='mgr', password='pass', role='manager')
        self.worker = User.objects.create_user(
            username='wrk', password='pass', role='worker', rating=120,
        )
        due = timezone.now() + timedelta(hours=5)
        Task.objects.create(
            title='Today task',
            description='d',
            assigned_to=self.worker,
            types=['Front'],
            rank=40,
            due_date=due,
            created_by=self.manager,
        )

    def test_worker_home_page(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Фокус на сегодня')
        self.assertContains(response, 'Today task')

    def test_today_focus_shows_new_task_with_future_deadline(self):
        due = timezone.now() + timedelta(days=2)
        Task.objects.create(
            title='New future task',
            description='d',
            assigned_to=self.worker,
            types=['Front'],
            rank=40,
            due_date=due,
            created_by=self.manager,
        )
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'New future task')

    def test_worker_tasks_list_route(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('worker_tasks'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TASK-')


class WorkerTeamPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username='mgr', password='pass', role='manager',
        )
        self.worker = User.objects.create_user(
            username='wrk', password='pass', role='worker', rating=50,
        )
        self.teammate = User.objects.create_user(
            username='mate', password='pass', role='worker', rating=75,
        )
        self.team = Team.objects.create(
            name='Alpha',
            description='Test squad',
            created_by=self.manager,
        )
        self.team.members.add(self.worker, self.teammate)

    def test_worker_team_shows_team_card(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('worker_team'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha')
        self.assertContains(response, 'Смотреть участников')
        self.assertNotContains(response, 'Поиск участников')

    def test_worker_team_detail_lists_teammates(self):
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('worker_team_detail', args=[self.team.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'mate')
        self.assertContains(response, 'Поиск участников')
        self.assertContains(response, 'Профиль')
        self.assertContains(response, 'Показатели отряда')
        self.assertContains(response, 'Задачи команды')

    def test_worker_cannot_open_other_team_detail(self):
        other_team = Team.objects.create(name='Other', created_by=self.manager)
        self.client.login(username='wrk', password='pass')
        response = self.client.get(reverse('worker_team_detail', args=[other_team.pk]))
        self.assertRedirects(response, reverse('worker_team'))

    def test_worker_without_team_sees_empty_state(self):
        lone = User.objects.create_user(username='lone', password='pass', role='worker')
        self.client.login(username='lone', password='pass')
        response = self.client.get(reverse('worker_team'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Команды не назначены')

    def test_manager_redirected_from_worker_team(self):
        self.client.login(username='mgr', password='pass')
        response = self.client.get(reverse('worker_team'))
        self.assertRedirects(response, reverse('team_list'))


class ManagerTeamModalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username='mgr', password='pass', role='manager',
        )
        self.team = Team.objects.create(
            name='Squad',
            description='Desc',
            created_by=self.manager,
        )

    def test_team_list_includes_detail_modal(self):
        self.client.login(username='mgr', password='pass')
        response = self.client.get(reverse('team_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'mg-team-detail-modal')
        self.assertContains(response, 'mg-teams-detail-data')
        self.assertContains(response, 'data-team-id="%d"' % self.team.pk)

    def test_manager_can_save_team_notes(self):
        self.client.login(username='mgr', password='pass')
        response = self.client.post(
            reverse('team_save_notes', args=[self.team.pk]),
            {'manager_notes': 'Важная заметка'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'ok': True})
        self.team.refresh_from_db()
        self.assertEqual(self.team.manager_notes, 'Важная заметка')
