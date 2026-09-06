from datetime import date, datetime, time, timezone as dt_timezone
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from timsy.models import (
    Activity,
    ActivityRecord,
    Blueprint,
    BlueprintEntry,
    DailyPlan,
    DailyPlanEntry,
    Importance,
    Parent,
    Place,
    Program,
    ToDoItem,
    Urgency,
    WeeklyPlan,
    WeeklyPlanAllocation,
)
from timsy.models.weekly_plan import seconds_by_parent
from timsy.reports.utils import (
    local_today,
    parse_hhmm_to_seconds,
    seconds_to_hhmm,
)
from timsy.views.todo_views import _is_past
from timsy.views.weekly_plan_views import _build_rows


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


class BlueprintScheduleTests(TestCase):
    """Blueprint weekday mask, interval weeks, and anchor date."""

    def test_mask_from_weekdays(self):
        self.assertEqual(Blueprint.mask_from_weekdays([]), 0)
        self.assertEqual(Blueprint.mask_from_weekdays([0]), 1)
        self.assertEqual(Blueprint.mask_from_weekdays([6]), 1 << 6)
        self.assertEqual(Blueprint.mask_from_weekdays([0, 3]), (1 << 0) | (1 << 3))

    def test_weekdays_and_label(self):
        blueprint = Blueprint.objects.create(
            name='Mon Thu',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([0, 3]),
            interval_weeks=1,
        )
        self.assertEqual(blueprint.weekdays(), [0, 3])
        self.assertEqual(blueprint.weekday_names(), ['Monday', 'Thursday'])
        self.assertEqual(blueprint.schedule_label(), 'Monday, Thursday')

    def test_matches_weekdays_every_week(self):
        blueprint = Blueprint.objects.create(
            name='Mon Thu',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([0, 3]),
            interval_weeks=1,
        )
        monday = date(2026, 9, 7)
        thursday = date(2026, 9, 3)
        tuesday = date(2026, 9, 8)
        self.assertEqual(monday.weekday(), 0)
        self.assertEqual(thursday.weekday(), 3)
        self.assertTrue(blueprint.matches_date(monday))
        self.assertTrue(blueprint.matches_date(thursday))
        self.assertFalse(blueprint.matches_date(tuesday))

    def test_matches_every_other_sunday_from_anchor(self):
        anchor = date(2026, 9, 6)
        self.assertEqual(anchor.weekday(), 6)
        blueprint = Blueprint.objects.create(
            name='Recycle Sunday',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([6]),
            interval_weeks=2,
            anchor_date=anchor,
        )
        self.assertTrue(blueprint.matches_date(anchor))
        self.assertFalse(blueprint.matches_date(date(2026, 9, 13)))
        self.assertTrue(blueprint.matches_date(date(2026, 9, 20)))
        self.assertFalse(blueprint.matches_date(date(2026, 9, 7)))
        self.assertEqual(
            blueprint.schedule_label(),
            'Sunday every 2 weeks from 2026-09-06',
        )

    def test_interval_without_anchor_does_not_match(self):
        blueprint = Blueprint.objects.create(
            name='Unset recycle',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([6]),
            interval_weeks=2,
        )
        self.assertFalse(blueprint.matches_date(date(2026, 9, 6)))

    def test_empty_mask_matches_no_dates(self):
        blueprint = Blueprint.objects.create(name='Unset', is_active=True)
        self.assertEqual(blueprint.weekday_mask, 0)
        self.assertEqual(blueprint.interval_weeks, 1)
        self.assertIsNone(blueprint.anchor_date)
        self.assertFalse(blueprint.matches_date(date(2026, 9, 3)))
        self.assertEqual(blueprint.schedule_label(), 'no weekdays')

    def test_create_saves_schedule(self):
        response = self.client.post(
            reverse('blueprint_create'),
            {
                'name': 'Monday',
                'weekdays': ['0'],
                'interval_weeks': '1',
            },
        )
        blueprint = Blueprint.objects.get(name='Monday')
        self.assertRedirects(response, reverse('blueprint_edit', args=[blueprint.id]))
        self.assertEqual(blueprint.weekday_mask, Blueprint.mask_from_weekdays([0]))
        self.assertEqual(blueprint.interval_weeks, 1)
        self.assertIsNone(blueprint.anchor_date)

    def test_clone_copies_then_overrides_schedule(self):
        source = Blueprint.objects.create(
            name='Sunday',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([6]),
            interval_weeks=1,
        )
        get_response = self.client.get(reverse('blueprint_clone', args=[source.id]))
        self.assertContains(get_response, 'Sunday')
        self.assertContains(get_response, 'value="6"')
        self.assertContains(get_response, 'value="6" checked')

        response = self.client.post(
            reverse('blueprint_clone', args=[source.id]),
            {
                'name': 'Recycle Sunday',
                'weekdays': ['6'],
                'interval_weeks': '2',
                'anchor_date': '2026-09-06',
            },
        )
        clone = Blueprint.objects.get(name='Recycle Sunday')
        self.assertRedirects(response, reverse('blueprint_edit', args=[clone.id]))
        self.assertEqual(clone.weekday_mask, Blueprint.mask_from_weekdays([6]))
        self.assertEqual(clone.interval_weeks, 2)
        self.assertEqual(clone.anchor_date, date(2026, 9, 6))
        source.refresh_from_db()
        self.assertEqual(source.interval_weeks, 1)
        self.assertIsNone(source.anchor_date)

    def test_edit_saves_schedule_without_wiping_when_no_rows(self):
        blueprint = Blueprint.objects.create(name='Weekday', is_active=True)
        response = self.client.post(
            reverse('blueprint_edit', args=[blueprint.id]),
            {
                'weekdays': ['0', '3'],
                'interval_weeks': '1',
                'anchor_date': '',
            },
        )
        self.assertRedirects(response, reverse('blueprint_edit', args=[blueprint.id]))
        blueprint.refresh_from_db()
        self.assertEqual(blueprint.weekday_mask, Blueprint.mask_from_weekdays([0, 3]))
        self.assertEqual(blueprint.interval_weeks, 1)
        self.assertIsNone(blueprint.anchor_date)

    def test_edit_skips_zero_duration_rows(self):
        importance = Importance.objects.create(
            sort_order=1, abbreviation='A', description='High'
        )
        urgency = Urgency.objects.create(
            sort_order=1, abbreviation='A', description='Soon'
        )
        parent = Parent.objects.create(
            id='WO',
            sort_order=1,
            description='Work',
            importance=importance,
            state=Parent.State.ACTIVE,
        )
        place = Place.objects.create(
            abbreviation='H', sort_order=1, description='Home'
        )
        blueprint = Blueprint.objects.create(name='Work day', is_active=True)

        def row(index, duration, abbreviation, description, start=''):
            data = {
                'duration%d' % index: duration,
                'abbreviation%d' % index: abbreviation,
                'description%d' % index: description,
                'parent%d' % index: parent.id,
                'importance%d' % index: str(importance.id),
                'urgency%d' % index: str(urgency.id),
                'place%d' % index: place.abbreviation,
            }
            if start:
                data['start%d' % index] = start
            return data

        post = {
            'weekdays': ['0'],
            'interval_weeks': '1',
            'anchor_date': '',
        }
        post.update(row(0, '1:00', 'wo', 'Work', start='08:00'))
        post.update(row(1, '0:00', 'skip', 'Should be ignored'))
        post.update(row(2, '2:00', 'mt', 'Meeting'))
        post.update(row(3, '', '', ''))

        response = self.client.post(
            reverse('blueprint_edit', args=[blueprint.id]),
            post,
        )
        self.assertRedirects(response, reverse('blueprint_edit', args=[blueprint.id]))
        entries = list(BlueprintEntry.objects.filter(blueprint=blueprint).order_by('start'))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].start, time(8, 0))
        self.assertEqual(entries[0].duration, time(1, 0))
        self.assertEqual(entries[0].activity.abbreviation, 'wo')
        self.assertEqual(entries[1].start, time(9, 0))
        self.assertEqual(entries[1].duration, time(2, 0))
        self.assertEqual(entries[1].activity.abbreviation, 'mt')

    def test_list_and_detail_show_schedule(self):
        blueprint = Blueprint.objects.create(
            name='Work day',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([0]),
        )
        listing = self.client.get(reverse('blueprint_list'))
        self.assertContains(listing, 'Work day')
        self.assertContains(listing, 'Monday')
        detail = self.client.get(reverse('blueprint_detail', args=[blueprint.id]))
        self.assertContains(detail, 'Schedule: Monday')


class DailyPlanBlueprintPanelTests(TestCase):
    """The plan editor lists only blueprints whose schedule matches the plan date."""

    def setUp(self):
        self.plan_date = date(2026, 9, 3)
        self.assertEqual(self.plan_date.weekday(), 3)
        self.plan = DailyPlan.objects.create(date=self.plan_date)
        self.thursday = Blueprint.objects.create(
            name='Thursday template',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([3]),
        )
        Blueprint.objects.create(
            name='Monday template',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([0]),
        )
        Blueprint.objects.create(
            name='Unscheduled template',
            is_active=True,
        )
        Blueprint.objects.create(
            name='Other Thursday template',
            is_active=True,
            weekday_mask=Blueprint.mask_from_weekdays([3]),
            interval_weeks=2,
            anchor_date=date(2026, 9, 10),
        )
        Blueprint.objects.create(
            name='Inactive Thursday template',
            is_active=False,
            weekday_mask=Blueprint.mask_from_weekdays([3]),
        )

    def test_for_date_returns_matching_active_blueprints(self):
        matching = Blueprint.for_date(self.plan_date)
        self.assertEqual([blueprint.name for blueprint in matching], [
            'Thursday template',
        ])

    def test_edit_panel_omits_incompatible_blueprints(self):
        response = self.client.get(
            reverse(
                'daily_plan_edit',
                args=[
                    self.plan_date.year,
                    self.plan_date.month,
                    self.plan_date.day,
                ],
            )
        )
        self.assertContains(response, 'Thursday template')
        self.assertNotContains(response, 'Monday template')
        self.assertNotContains(response, 'Unscheduled template')
        self.assertNotContains(response, 'Other Thursday template')
        self.assertNotContains(response, 'Inactive Thursday template')


def _parent_row(index, parent_id='', existing_id='', sort_order='',
                description='', importance='', state=''):
    """Build POST fields for one parent editor row."""
    return {
        'parent_id%d' % index: parent_id,
        'existing_id%d' % index: existing_id,
        'sort_order%d' % index: sort_order,
        'description%d' % index: description,
        'importance%d' % index: str(importance) if importance != '' else '',
        'state%d' % index: state,
    }


class ParentEditorTests(TestCase):
    """Create and update parents on the Activity hierarchy pages."""

    def setUp(self):
        self.importance = Importance.objects.create(
            sort_order=1, abbreviation='A', description='High'
        )
        self.other_importance = Importance.objects.create(
            sort_order=2, abbreviation='B', description='Low'
        )
        self.parent = Parent.objects.create(
            id='RT',
            sort_order=1,
            description='Routine',
            importance=self.importance,
            state=Parent.State.ACTIVE,
        )
        self.top_url = reverse('top_parents_list')
        self.editor_url = reverse('activity_editor', args=['RT'])
        self.child_save_url = reverse('save_child_parents', args=['RT'])

    def test_create_top_level_parent(self):
        response = self.client.post(self.top_url, {
            **_parent_row(
                0, parent_id='WO', sort_order='2', description='Work',
                importance=self.importance.id, state='active',
            ),
        })
        self.assertRedirects(response, self.top_url)
        created = Parent.objects.get(id='WO')
        self.assertEqual(created.description, 'Work')
        self.assertEqual(created.sort_order, 2)
        self.assertEqual(created.importance, self.importance)
        self.assertEqual(created.state, Parent.State.ACTIVE)

    def test_update_top_level_parent(self):
        response = self.client.post(self.top_url, {
            **_parent_row(
                0, parent_id='RT', existing_id='RT', sort_order='5',
                description='Updated routine', importance=self.other_importance.id,
                state='paused',
            ),
            **_parent_row(1),
        })
        self.assertRedirects(response, self.top_url)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.description, 'Updated routine')
        self.assertEqual(self.parent.sort_order, 5)
        self.assertEqual(self.parent.importance, self.other_importance)
        self.assertEqual(self.parent.state, Parent.State.PAUSED)

    def test_create_child_parent(self):
        response = self.client.post(self.child_save_url, {
            **_parent_row(
                0, parent_id='RT-AB', sort_order='1', description='Sub',
                importance=self.importance.id, state='active',
            ),
        })
        self.assertRedirects(response, self.editor_url)
        created = Parent.objects.get(id='RT-AB')
        self.assertEqual(created.description, 'Sub')
        self.assertEqual(created.sort_order, 1)

    def test_reject_wrong_shape_top_level_id(self):
        response = self.client.post(self.top_url, {
            **_parent_row(
                0, parent_id='TOOLONG', description='Bad',
                importance=self.importance.id, state='active',
            ),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ID must be exactly 2 characters')
        self.assertFalse(Parent.objects.filter(id='TOOLONG').exists())

    def test_reject_wrong_shape_child_ids(self):
        for bad_id in ('RT', 'XX-AB'):
            response = self.client.post(self.child_save_url, {
                **_parent_row(
                    0, parent_id=bad_id, description='Bad',
                    importance=self.importance.id, state='active',
                ),
            })
            self.assertEqual(response.status_code, 200, bad_id)
            self.assertContains(response, 'ID must be RT- followed by 2 characters')
        self.assertFalse(Parent.objects.filter(id='XX-AB').exists())
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.description, 'Routine')
        self.assertEqual(Parent.objects.count(), 1)

    def test_reject_duplicate_id(self):
        response = self.client.post(self.top_url, {
            **_parent_row(
                0, parent_id='RT', existing_id='RT', sort_order='1',
                description='Routine', importance=self.importance.id,
                state='active',
            ),
            **_parent_row(
                1, parent_id='RT', description='Copy',
                importance=self.importance.id, state='active',
            ),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertEqual(Parent.objects.filter(id='RT').count(), 1)

    def test_skip_empty_rows(self):
        response = self.client.post(self.top_url, {
            **_parent_row(
                0, parent_id='RT', existing_id='RT', sort_order='1',
                description='Routine', importance=self.importance.id,
                state='active',
            ),
            **_parent_row(1),
        })
        self.assertRedirects(response, self.top_url)
        self.assertEqual(Parent.objects.count(), 1)

    def test_subcategories_form_when_no_children(self):
        response = self.client.get(self.editor_url)
        self.assertContains(response, 'Subcategories')
        self.assertContains(response, 'name="parent_id0"')
        self.assertContains(response, 'action="%s"' % self.child_save_url)

    def test_save_child_parents_get_redirects_to_editor(self):
        response = self.client.get(self.child_save_url)
        self.assertRedirects(response, self.editor_url)

    def test_valid_row_saves_when_another_row_fails(self):
        response = self.client.post(self.top_url, {
            **_parent_row(
                0, parent_id='RT', existing_id='RT', sort_order='1',
                description='Routine', importance=self.importance.id,
                state='active',
            ),
            **_parent_row(
                1, parent_id='WO', sort_order='2', description='Work',
                importance=self.importance.id, state='active',
            ),
            **_parent_row(
                2, parent_id='TOOLONG', description='Bad',
                importance=self.importance.id, state='active',
            ),
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Parent.objects.filter(id='WO', description='Work').exists())
        self.assertFalse(Parent.objects.filter(id='TOOLONG').exists())
        self.assertContains(response, 'ID must be exactly 2 characters')


class WeeklyPlanTests(TestCase):
    """Weekly hour budget, clone, remaining hours, and analysis notes."""

    def setUp(self):
        self.importance = Importance.objects.create(
            sort_order=1, abbreviation='A', description='High'
        )
        self.urgency = Urgency.objects.create(
            sort_order=1, abbreviation='A', description='Soon'
        )
        self.work = Parent.objects.create(
            id='WO',
            sort_order=1,
            description='Work',
            importance=self.importance,
            state=Parent.State.ACTIVE,
        )
        self.sleep = Parent.objects.create(
            id='SL',
            sort_order=2,
            description='Sleep',
            importance=self.importance,
            state=Parent.State.ACTIVE,
        )
        self.paused = Parent.objects.create(
            id='XX',
            sort_order=3,
            description='Paused',
            importance=self.importance,
            state=Parent.State.PAUSED,
        )
        self.child = Parent.objects.create(
            id='WO-GP',
            sort_order=1,
            description='Portfolio',
            importance=self.importance,
            state=Parent.State.ACTIVE,
        )
        self.place = Place.objects.create(
            abbreviation='H', sort_order=1, description='Home'
        )
        self.work_activity = Activity.objects.create(
            sort_order=1,
            abbreviation='wo',
            description='Work',
            parent=self.work,
            importance=self.importance,
            urgency=self.urgency,
        )
        self.child_activity = Activity.objects.create(
            sort_order=2,
            abbreviation='gp',
            description='Portfolio work',
            parent=self.child,
            importance=self.importance,
            urgency=self.urgency,
        )
        self.week_start = date(2026, 8, 29)
        self.next_week = date(2026, 9, 5)
        self.edit_url = reverse(
            'weekly_plan_edit',
            args=[self.week_start.year, self.week_start.month, self.week_start.day],
        )
        self.next_url = reverse(
            'weekly_plan_edit',
            args=[self.next_week.year, self.next_week.month, self.next_week.day],
        )

    def test_week_start_snaps_without_empty_parent_rows(self):
        wednesday = date(2026, 9, 2)
        url = reverse(
            'weekly_plan_edit',
            args=[wednesday.year, wednesday.month, wednesday.day],
        )
        response = self.client.get(url)
        self.assertRedirects(response, self.edit_url)
        page = self.client.get(self.edit_url)
        self.assertNotContains(page, '<input type="hidden" name="parent')
        self.assertContains(page, '168:00')
        html = page.content.decode()
        self.assertTrue(
            html.find('<th>Parent</th>')
            < html.find('<th>Importance</th>')
            < html.find('<th>Program</th>')
        )

    def test_includes_parents_with_budget_or_scheduled(self):
        weekly = WeeklyPlan.objects.create(week_start=self.week_start)
        WeeklyPlanAllocation.objects.create(
            weekly_plan=weekly, parent=self.work, seconds=10 * 3600
        )
        WeeklyPlanAllocation.objects.create(
            weekly_plan=weekly, parent=self.sleep, seconds=0
        )
        plan = DailyPlan.objects.create(date=self.week_start)
        DailyPlanEntry.objects.create(
            plan=plan,
            activity=self.child_activity,
            place=self.place,
            start=time(8, 0),
            duration=time(3, 0),
        )
        page = self.client.get(self.edit_url)
        html = page.content.decode()
        self.assertIn('<input type="hidden" name="parent0" value="WO">', html)
        self.assertIn('<input type="hidden" name="parent1" value="WO-GP">', html)
        self.assertNotIn('<input type="hidden" name="parent2" value="SL">', html)
        self.assertNotIn('<input type="hidden" name="parent2" value="XX">', html)

    def test_scheduled_parent_appears_without_weekly_plan(self):
        plan = DailyPlan.objects.create(date=self.week_start)
        DailyPlanEntry.objects.create(
            plan=plan,
            activity=self.work_activity,
            place=self.place,
            start=time(9, 0),
            duration=time(1, 0),
        )
        page = self.client.get(self.edit_url)
        html = page.content.decode()
        self.assertIn('<input type="hidden" name="parent0" value="WO">', html)
        self.assertNotIn('<input type="hidden" name="parent1" value="SL">', html)

    def test_includes_parents_with_nonzero_fact(self):
        weekly = WeeklyPlan.objects.create(week_start=self.week_start)
        WeeklyPlanAllocation.objects.create(
            weekly_plan=weekly, parent=self.work, seconds=10 * 3600
        )
        ActivityRecord.objects.create(
            activity=self.work_activity,
            place=self.place,
            start=datetime(2026, 8, 29, 8, 0, tzinfo=dt_timezone.utc),
            duration=time(4, 0),
        )
        ActivityRecord.objects.create(
            activity=self.child_activity,
            place=self.place,
            start=datetime(2026, 8, 22, 8, 0, tzinfo=dt_timezone.utc),
            duration=time(2, 30),
        )
        rows, totals = _build_rows(self.week_start, weekly)
        by_id = {row['parent_id']: row for row in rows if row['parent']}
        self.assertEqual(by_id['WO']['budget'], '10:00')
        self.assertEqual(by_id['WO']['fact'], '00:00')
        self.assertEqual(by_id['WO-GP']['budget'], '')
        self.assertEqual(by_id['WO-GP']['scheduled'], '00:00')
        self.assertEqual(by_id['WO-GP']['fact'], '02:30')
        self.assertNotIn('SL', by_id)
        self.assertEqual(totals['fact'], '02:30')

    def test_save_hours_over_24_and_child_parent_row(self):
        response = self.client.post(self.edit_url, {
            'action': 'save',
            'parent0': 'WO',
            'hours0': '40:00',
            'parent1': 'SL',
            'hours1': '56:00',
            'parent2': 'WO-GP',
            'hours2': '10:00',
            'note': '',
        })
        self.assertRedirects(response, self.edit_url)
        plan = WeeklyPlan.objects.get(week_start=self.week_start)
        allocations = {
            row.parent_id: row.seconds for row in plan.allocations.all()
        }
        self.assertEqual(allocations['WO'], 40 * 3600)
        self.assertEqual(allocations['SL'], 56 * 3600)
        self.assertEqual(allocations['WO-GP'], 10 * 3600)
        self.assertEqual(parse_hhmm_to_seconds('40:00'), 40 * 3600)
        self.assertEqual(seconds_to_hhmm(40 * 3600), '40:00')

    def test_clone_copies_allocations_not_note(self):
        source = WeeklyPlan.objects.create(
            week_start=self.week_start, note='Last week went well'
        )
        WeeklyPlanAllocation.objects.create(
            weekly_plan=source, parent=self.work, seconds=40 * 3600
        )
        response = self.client.post(self.next_url, {'action': 'clone'})
        self.assertRedirects(response, self.next_url)
        cloned = WeeklyPlan.objects.get(week_start=self.next_week)
        self.assertEqual(cloned.note, '')
        self.assertEqual(cloned.allocations.get().parent, self.work)
        self.assertEqual(cloned.allocations.get().seconds, 40 * 3600)

    def test_seconds_by_parent_uses_most_specific_row(self):
        item = type('Item', (), {})()
        item.activity = type('Activity', (), {'parent_id': 'WO-GP'})()
        item.duration = time(3, 0)
        self.assertEqual(seconds_by_parent([item], ['WO']), {'WO': 3 * 3600})
        self.assertEqual(
            seconds_by_parent([item], ['WO', 'WO-GP']),
            {'WO': 0, 'WO-GP': 3 * 3600},
        )

    def test_scheduled_fact_remaining_include_descendants(self):
        weekly = WeeklyPlan.objects.create(week_start=self.week_start)
        WeeklyPlanAllocation.objects.create(
            weekly_plan=weekly, parent=self.work, seconds=10 * 3600
        )
        plan = DailyPlan.objects.create(date=self.week_start)
        DailyPlanEntry.objects.create(
            plan=plan,
            activity=self.child_activity,
            place=self.place,
            start=time(8, 0),
            duration=time(3, 0),
        )
        ActivityRecord.objects.create(
            activity=self.child_activity,
            place=self.place,
            start=datetime(2026, 8, 22, 8, 0, tzinfo=dt_timezone.utc),
            duration=time(2, 30),
        )
        ActivityRecord.objects.create(
            activity=self.child_activity,
            place=self.place,
            start=datetime(2026, 8, 29, 8, 0, tzinfo=dt_timezone.utc),
            duration=time(4, 0),
        )
        rows, totals = _build_rows(self.week_start, weekly)
        by_id = {row['parent_id']: row for row in rows if row['parent']}
        self.assertEqual(by_id['WO']['budget'], '10:00')
        self.assertEqual(by_id['WO']['scheduled'], '00:00')
        self.assertEqual(by_id['WO']['remaining'], '10:00')
        self.assertEqual(by_id['WO']['fact'], '00:00')
        self.assertEqual(by_id['WO-GP']['scheduled'], '03:00')
        self.assertEqual(by_id['WO-GP']['fact'], '02:30')
        self.assertEqual(totals['scheduled'], '03:00')
        self.assertEqual(totals['fact'], '02:30')

    def test_program_link_on_editor(self):
        Program.objects.create(parent=self.work, description='Ship weekly plans')
        weekly = WeeklyPlan.objects.create(week_start=self.week_start)
        WeeklyPlanAllocation.objects.create(
            weekly_plan=weekly,
            parent=self.work,
            seconds=8 * 3600,
        )
        page = self.client.get(self.edit_url)
        self.assertContains(page, reverse('program_editor', args=['WO']))
        html = page.content.decode()
        parent_index = html.find('<th>Parent</th>')
        importance_index = html.find('<th>Importance</th>')
        program_index = html.find('<th>Program</th>')
        self.assertTrue(0 <= parent_index < importance_index < program_index)
        self.assertContains(page, 'High')

    def test_remaining_hours_on_daily_plan_edit(self):
        weekly = WeeklyPlan.objects.create(week_start=self.week_start)
        WeeklyPlanAllocation.objects.create(
            weekly_plan=weekly, parent=self.work, seconds=8 * 3600
        )
        DailyPlan.objects.create(date=self.week_start)
        edit_url = reverse(
            'daily_plan_edit',
            args=[self.week_start.year, self.week_start.month, self.week_start.day],
        )
        page = self.client.get(edit_url)
        self.assertContains(page, "This week's remaining hours")
        self.assertContains(page, 'Work')
        self.assertContains(page, '08:00')

        other_week = date(2026, 9, 5)
        DailyPlan.objects.create(date=other_week)
        other_edit = reverse(
            'daily_plan_edit',
            args=[other_week.year, other_week.month, other_week.day],
        )
        hidden = self.client.get(other_edit)
        self.assertNotContains(hidden, "This week's remaining hours")

    def test_daily_plan_vs_fact_saves_note(self):
        report_url = '/timsy/reports/plan-vs-fact/daily/ALL/2026/8/29/'
        response = self.client.post(report_url, {
            'action': 'save_note',
            'note': 'What went right: logging.\nWhat went wrong: late start.',
        })
        self.assertRedirects(response, report_url)
        plan = DailyPlan.objects.get(date=self.week_start)
        self.assertIn('late start', plan.note)
        page = self.client.get(report_url)
        self.assertContains(page, 'late start')

    def test_weekly_plan_and_report_share_note(self):
        self.client.post(self.edit_url, {
            'action': 'save',
            'parent0': 'WO',
            'hours0': '08:00',
            'note': 'Week was noisy.',
        })
        plan = WeeklyPlan.objects.get(week_start=self.week_start)
        self.assertEqual(plan.note, 'Week was noisy.')
        report_url = '/timsy/reports/plan-vs-fact/weekly/ALL/2026/8/29/'
        page = self.client.get(report_url)
        self.assertContains(page, 'Week was noisy.')
        self.client.post(report_url, {
            'action': 'save_note',
            'note': 'Updated weekly analysis.',
        })
        plan.refresh_from_db()
        self.assertEqual(plan.note, 'Updated weekly analysis.')

    def test_index_and_latest_link_to_weekly_plans(self):
        index = self.client.get(reverse('index'))
        self.assertContains(index, reverse('weekly_plan_latest'))
        list_page = self.client.get(reverse('weekly_plan_list'))
        self.assertContains(list_page, 'This week')
        with patch('timsy.views.weekly_plan_views.local_today', return_value=self.week_start):
            latest = self.client.get(reverse('weekly_plan_latest'))
        self.assertRedirects(latest, self.edit_url)
