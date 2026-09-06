from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from timsy.models import Importance, Parent, ToDoItem
from timsy.reports.utils import local_today
from timsy.views.todo_views import _is_past


class LocalTodayTests(SimpleTestCase):
    """Calendar today follows Eastern, not Django TIME_ZONE (UTC)."""

    def test_late_evening_eastern_is_still_that_calendar_date(self):
        # 10 PM EDT on 2026-09-05 is 02:00 UTC on 2026-09-06.
        frozen = datetime(2026, 9, 6, 2, 0, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=frozen):
            self.assertEqual(local_today(), date(2026, 9, 5))

    def test_after_eastern_midnight_is_the_next_calendar_date(self):
        # 12:30 AM EDT on 2026-09-06 is 04:30 UTC on 2026-09-06.
        frozen = datetime(2026, 9, 6, 4, 30, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=frozen):
            self.assertEqual(local_today(), date(2026, 9, 6))


class TodoDailyPastColumnTests(SimpleTestCase):
    """Day columns stay current until Eastern midnight, not UTC midnight."""

    def test_evening_eastern_does_not_grey_out_today(self):
        # 10 PM EDT on 2026-09-05 is 02:00 UTC on 2026-09-06.
        frozen = datetime(2026, 9, 6, 2, 0, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=frozen):
            self.assertFalse(
                _is_past(ToDoItem.Horizon.DAY, date(2026, 9, 5), local_today())
            )

    def test_after_eastern_midnight_greys_out_yesterday(self):
        # 12:30 AM EDT on 2026-09-06 is 04:30 UTC on 2026-09-06.
        frozen = datetime(2026, 9, 6, 4, 30, tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now', return_value=frozen):
            self.assertTrue(
                _is_past(ToDoItem.Horizon.DAY, date(2026, 9, 5), local_today())
            )


class ProgramEditorTodoHorizonTests(TestCase):
    """Program editor edit can change a todo's horizon without leaving the page."""

    def setUp(self):
        self.importance = Importance.objects.create(
            sort_order=1, abbreviation='A', description='High'
        )
        self.parent = Parent.objects.create(
            id='WO',
            sort_order=1,
            description='Work',
            importance=self.importance,
            state=Parent.State.ACTIVE,
        )
        self.editor_url = reverse('program_editor', args=['WO'])
        self.todo = ToDoItem.objects.create(
            parent=self.parent,
            description='Ship horizon edit',
            horizon=ToDoItem.Horizon.YEAR,
            horizon_date=date(2026, 1, 1),
            status=ToDoItem.Status.OPEN,
            sort_order=0,
        )

    def test_view_links_horizon_edit_shows_fields(self):
        yearly = reverse('todo_yearly', args=[2026])
        page = self.client.get(self.editor_url)
        self.assertContains(page, yearly)
        self.assertContains(page, 'Ship horizon edit')
        edit_page = self.client.get(
            self.editor_url, {'todo_edit': str(self.todo.id)}
        )
        self.assertNotContains(edit_page, 'href="%s"' % yearly)
        self.assertContains(
            edit_page, 'form="todo-edit-%s" name="horizon"' % self.todo.id
        )
        self.assertContains(edit_page, 'name="year"')
        self.assertContains(edit_page, 'value="2026"')

    def test_edit_changes_horizon_and_appends_sort_order(self):
        occupant = ToDoItem.objects.create(
            parent=self.parent,
            description='Already in September',
            horizon=ToDoItem.Horizon.MONTH,
            horizon_date=date(2026, 9, 1),
            status=ToDoItem.Status.OPEN,
            sort_order=4,
        )
        response = self.client.post(self.editor_url, {
            'action': 'edit',
            'item_id': str(self.todo.id),
            'parent': self.parent.id,
            'description': 'Ship horizon edit',
            'horizon': 'month',
            'year': '2026',
            'month': '9',
            'next': self.editor_url,
        })
        self.assertRedirects(response, self.editor_url)
        self.todo.refresh_from_db()
        occupant.refresh_from_db()
        self.assertEqual(self.todo.horizon, ToDoItem.Horizon.MONTH)
        self.assertEqual(self.todo.horizon_date, date(2026, 9, 1))
        self.assertEqual(self.todo.sort_order, 5)
        self.assertEqual(occupant.sort_order, 4)

    def test_edit_keeps_sort_order_when_horizon_unchanged(self):
        self.todo.sort_order = 3
        self.todo.save(update_fields=['sort_order'])
        self.client.post(self.editor_url, {
            'action': 'edit',
            'item_id': str(self.todo.id),
            'parent': self.parent.id,
            'description': 'Renamed',
            'horizon': 'year',
            'year': '2026',
            'next': self.editor_url,
        })
        self.todo.refresh_from_db()
        self.assertEqual(self.todo.description, 'Renamed')
        self.assertEqual(self.todo.horizon, ToDoItem.Horizon.YEAR)
        self.assertEqual(self.todo.horizon_date, date(2026, 1, 1))
        self.assertEqual(self.todo.sort_order, 3)
