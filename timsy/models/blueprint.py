from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from .activity import Activity
from .place import Place


class Blueprint(models.Model):
    """
    Represents a blueprint for planning activities.

    This model stores blueprint that define how a day of a part of it should be structured,
    including which activities should occur, where and when. Blueprints can be marked as
    active or inactive to control which ones are available for use.

    Schedule fields decide which dates a blueprint applies to during daily-plan generation.
    weekday_mask is a bit per Python weekday (0=Monday ... 6=Sunday). interval_weeks of 1
    means every week; 2 means every other week, measured as week offset from anchor_date.

    Attributes:
        name (str): Name of the blueprint (max 200 chars)
        is_active (bool): Whether the blueprint is currently active and available for use
        weekday_mask (int): Bitmask of weekdays this blueprint applies to
        interval_weeks (int): 1 = every week, 2 = every other week, and so on
        anchor_date (date): Makes interval_weeks well-defined (week offset from this date)
    """

    WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    WEEKDAY_MASK_ALL = (1 << 7) - 1

    name = models.CharField(max_length=200)
    is_active = models.BooleanField()
    weekday_mask = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(WEEKDAY_MASK_ALL)],
    )
    interval_weeks = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    anchor_date = models.DateField(null=True, blank=True)

    def __str__(self):
        """Return the blueprint's name as its string representation.

        Returns:
            str: The blueprint's name
        """
        return self.name

    def get_entries(self):
        """Return the blueprint's entries as a list.

        Returns:
            list: The blueprint's list of records
        """
        return BlueprintEntry.objects.filter(blueprint=self).order_by('start')

    @classmethod
    def mask_from_weekdays(cls, weekdays):
        """Build a weekday_mask from Python weekday numbers (0=Monday ... 6=Sunday).

        Args:
            weekdays: Iterable of weekday integers

        Returns:
            int: Bitmask with bit N set for each weekday N
        """
        mask = 0
        for weekday in weekdays:
            weekday = int(weekday)
            if 0 <= weekday <= 6:
                mask |= 1 << weekday
        return mask

    def weekdays(self):
        """Return the weekday numbers this blueprint is scheduled for.

        Returns:
            list: Python weekday numbers (0=Monday ... 6=Sunday)
        """
        return [day for day in range(7) if self.weekday_mask & (1 << day)]

    def weekday_names(self):
        """Return weekday labels for the scheduled days.

        Returns:
            list: Names such as Monday, Tuesday
        """
        names = dict(self.WEEKDAY_CHOICES)
        return [names[day] for day in self.weekdays()]

    def schedule_label(self):
        """Return a short description of this blueprint's schedule.

        Returns:
            str: Human-readable schedule, or a note when no weekdays are set
        """
        days = ', '.join(self.weekday_names())
        if not days:
            return 'no weekdays'
        if self.interval_weeks <= 1:
            return days
        if self.anchor_date:
            return '%s every %s weeks from %s' % (
                days,
                self.interval_weeks,
                self.anchor_date.isoformat(),
            )
        return '%s every %s weeks' % (days, self.interval_weeks)

    def matches_date(self, d):
        """Return whether this blueprint's schedule applies on date d.

        Weekday must be in weekday_mask. interval_weeks of 1 matches every such
        weekday. Larger intervals use week offset from anchor_date; without an
        anchor the interval is not well-defined and this returns False.

        Args:
            d: A datetime.date

        Returns:
            bool: True if the schedule matches d
        """
        if not (self.weekday_mask & (1 << d.weekday())):
            return False
        if self.interval_weeks <= 1:
            return True
        if self.anchor_date is None:
            return False
        weeks_offset = (d - self.anchor_date).days // 7
        return weeks_offset % self.interval_weeks == 0

    @classmethod
    def for_date(cls, d, active_only=True):
        """Return blueprints whose schedule matches date d.

        Args:
            d: A datetime.date
            active_only: If True, only active blueprints

        Returns:
            list: Matching blueprints ordered by name
        """
        qs = cls.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return [
            blueprint
            for blueprint in qs.order_by('name')
            if blueprint.matches_date(d)
        ]


class BlueprintEntry(models.Model):
    """
    Represents an entry in a blueprint.

    This model defines a single activity entry within a blueprint, specifying when and where the activity should occur
    and how long it should last.

    Attributes:
        blueprint (Blueprint): Foreign key to the parent blueprint
        activity (Activity): Foreign key to the activity to be performed
        place (Place): Foreign key to where the activity should occur
        start (time): When the activity should start in the day
        duration (time): How long the activity should last
    """
    blueprint = models.ForeignKey(Blueprint, on_delete=models.PROTECT)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.TimeField()
    duration = models.TimeField()

    def __str__(self):
        """Return a string representation of the blueprint entry.

        Returns:
            str: String in format "activity (duration starting start_time) at place"
        """
        return "%s (%s starting %s) at %s" % (self.activity, self.duration, self.start, self.place)
