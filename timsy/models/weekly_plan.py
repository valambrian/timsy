from datetime import date, timedelta, time

from django.db import models

from .activity_record import ActivityRecord
from .daily_plan import DailyPlanEntry
from .parent import Parent


WEEK_SECONDS = 7 * 24 * 3600


def duration_to_seconds(duration: time) -> int:
    """Convert a TimeField duration to seconds.

    Args:
        duration: Hours and minutes stored as a time of day

    Returns:
        int: Duration in seconds
    """
    if duration is None:
        return 0
    return duration.hour * 3600 + duration.minute * 60 + duration.second


def parent_covers(activity_parent_id: str, allocation_parent_id: str) -> bool:
    """Return whether an activity parent counts toward an allocation parent.

    The allocation parent matches itself and any descendant in the id hierarchy
    (activity parent equals the id, or starts with id plus a hyphen).

    Args:
        activity_parent_id: Parent id on the activity
        allocation_parent_id: Parent id on the weekly allocation row

    Returns:
        bool: True when the activity rolls up into that allocation
    """
    if not activity_parent_id or not allocation_parent_id:
        return False
    return (
        activity_parent_id == allocation_parent_id
        or activity_parent_id.startswith(allocation_parent_id + '-')
    )


def most_specific_covering_parent(activity_parent_id, parent_ids):
    """Return the deepest listed parent that covers the activity parent.

    When both an ancestor and a descendant are listed, the descendant wins
    so the same hours are not counted on both rows.

    Args:
        activity_parent_id: Parent id on the activity
        parent_ids: Parent ids that can receive the hours

    Returns:
        str or None: The chosen parent id
    """
    best = None
    for pid in parent_ids:
        if not parent_covers(activity_parent_id, pid):
            continue
        if best is None or (parent_covers(pid, best) and pid != best):
            best = pid
    return best


def seconds_by_parent(items, parent_ids):
    """Sum item durations into the most specific covering parent.

    A parent still receives descendant hours when that descendant is not
    itself listed. If both are listed, only the descendant is charged.

    Args:
        items: Iterable of objects with ``activity.parent_id`` and ``duration``
        parent_ids: Allocation parent ids to total

    Returns:
        dict: parent id to seconds
    """
    result = {pid: 0 for pid in parent_ids}
    for item in items:
        seconds = duration_to_seconds(item.duration)
        if not seconds:
            continue
        target = most_specific_covering_parent(item.activity.parent_id, parent_ids)
        if target is not None:
            result[target] += seconds
    return result


class WeeklyPlan(models.Model):
    """
    Hour budget for one configured week.

    week_start is the Saturday (or TIMSY_WEEK_START_DAY) that begins the week.
    Allocations are hours per parent. note is the week-end written review.

    Attributes:
        week_start (date): First day of the week this plan covers
        note (str): Free-text weekly analysis
    """
    week_start = models.DateField(unique=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-week_start']

    def __str__(self):
        """Return a string representation of the weekly plan.

        Returns:
            str: String in format "Week of date"
        """
        return "Week of %s" % self.week_start

    def week_end(self) -> date:
        """Return the last calendar day of this week.

        Returns:
            date: week_start plus six days
        """
        return self.week_start + timedelta(days=6)

    def get_allocations(self):
        """Return allocations ordered by parent hierarchy.

        Returns:
            list: WeeklyPlanAllocation rows
        """
        allocations = list(
            self.allocations.select_related('parent', 'parent__importance').all()
        )
        order = {parent.id: index for index, parent in enumerate(Parent._in_hierarchy_order())}
        allocations.sort(key=lambda row: (order.get(row.parent_id, 10 ** 9), row.parent_id))
        return allocations

    def clone_allocations_from(self, source):
        """Replace this week's allocations with copies from another week.

        Does not copy the source week's note.

        Args:
            source: WeeklyPlan to copy allocations from
        """
        self.allocations.all().delete()
        for allocation in source.allocations.all():
            WeeklyPlanAllocation.objects.create(
                weekly_plan=self,
                parent=allocation.parent,
                seconds=allocation.seconds,
            )

    def parent_ids_with_scheduled(self):
        """Return parent ids that have non-zero DailyPlanEntry duration this week.

        Uses each activity's own parent, not ancestor rollup.

        Returns:
            set: Parent ids
        """
        ids = set()
        entries = DailyPlanEntry.objects.filter(
            plan__date__gte=self.week_start,
            plan__date__lte=self.week_end(),
        ).select_related('activity')
        for entry in entries:
            if duration_to_seconds(entry.duration):
                ids.add(entry.activity.parent_id)
        return ids

    def previous_week_bounds(self):
        """Return the inclusive start and end dates of the previous week.

        Returns:
            tuple: (start date, end date)
        """
        start = self.week_start - timedelta(days=7)
        return start, start + timedelta(days=6)

    def parent_ids_with_fact(self):
        """Return parent ids that have non-zero ActivityRecord duration last week.

        Uses each activity's own parent, not ancestor rollup.

        Returns:
            set: Parent ids
        """
        previous_start, previous_end = self.previous_week_bounds()
        ids = set()
        records = ActivityRecord.get_records(
            previous_start, previous_end
        ).select_related('activity')
        for record in records:
            if duration_to_seconds(record.duration):
                ids.add(record.activity.parent_id)
        return ids

    def scheduled_seconds(self, parent_ids, exclude_date=None):
        """Sum DailyPlanEntry durations this week for the given parents.

        Args:
            parent_ids: Parent ids to total
            exclude_date: Optional date whose plan entries are omitted

        Returns:
            dict: parent id to scheduled seconds
        """
        entries = DailyPlanEntry.objects.filter(
            plan__date__gte=self.week_start,
            plan__date__lte=self.week_end(),
        ).select_related('activity')
        if exclude_date is not None:
            entries = entries.exclude(plan__date=exclude_date)
        return seconds_by_parent(entries, parent_ids)

    def fact_seconds(self, parent_ids):
        """Sum ActivityRecord durations from the previous week for the given parents.

        Args:
            parent_ids: Parent ids to total

        Returns:
            dict: parent id to fact seconds
        """
        previous_start, previous_end = self.previous_week_bounds()
        records = ActivityRecord.get_records(
            previous_start, previous_end
        ).select_related('activity')
        return seconds_by_parent(records, parent_ids)

    @classmethod
    def for_week_start(cls, week_start: date):
        """Return the weekly plan for week_start, or None.

        Args:
            week_start: First day of the week

        Returns:
            WeeklyPlan or None
        """
        return cls.objects.filter(week_start=week_start).first()

    @classmethod
    def previous_before(cls, week_start: date):
        """Return the nearest earlier weekly plan, if any.

        Args:
            week_start: Week that should come after the result

        Returns:
            WeeklyPlan or None
        """
        return cls.objects.filter(week_start__lt=week_start).order_by('-week_start').first()


class WeeklyPlanAllocation(models.Model):
    """
    Target hours for one parent in one weekly plan.

    Attributes:
        weekly_plan (WeeklyPlan): The week this row belongs to
        parent (Parent): Category receiving the hours
        seconds (int): Budgeted duration in seconds
    """
    weekly_plan = models.ForeignKey(
        WeeklyPlan, on_delete=models.CASCADE, related_name='allocations'
    )
    parent = models.ForeignKey(Parent, on_delete=models.PROTECT)
    seconds = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['weekly_plan', 'parent'],
                name='timsy_weeklyplanallocation_plan_parent_uniq',
            ),
        ]

    def __str__(self):
        """Return a string representation of the allocation.

        Returns:
            str: Parent and seconds
        """
        return "%s: %s" % (self.parent, self.seconds)
