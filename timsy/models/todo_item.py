from django.db import models
from .parent import Parent
from .activity import Activity


class ToDoItem(models.Model):
    """
    A live work-queue item owned by a parent category, not a Program version.

    Horizon says how specifically the item is scheduled (year / month / week / day).
    horizon_date is the year (Jan 1), month (the 1st), week start, or calendar day.

    Attributes:
        parent (Parent): Owner. Same parent as the program page.
        description (str): The work item (max 200 chars)
        activity (Activity): Optional catalog link
        horizon (str): year, month, week, or day
        horizon_date (date): Period being targeted
        status (str): open or done
        sort_order (int): Order within a period column
        program_order (int): Order on program pages
        note (str): Optional extra text
    """

    class Horizon(models.TextChoices):
        YEAR = 'year', 'Year'
        MONTH = 'month', 'Month'
        WEEK = 'week', 'Week'
        DAY = 'day', 'Day'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        DONE = 'done', 'Done'

    parent = models.ForeignKey(Parent, on_delete=models.PROTECT)
    description = models.CharField(max_length=200)
    activity = models.ForeignKey(
        Activity, on_delete=models.SET_NULL, null=True, blank=True
    )
    horizon = models.CharField(max_length=5, choices=Horizon.choices)
    horizon_date = models.DateField()
    status = models.CharField(
        max_length=4, choices=Status.choices, default=Status.OPEN
    )
    sort_order = models.IntegerField(default=0)
    program_order = models.IntegerField(default=0)
    note = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['horizon', 'horizon_date', 'status']),
            models.Index(fields=['parent', 'status', 'sort_order']),
        ]
        ordering = ['sort_order', 'id']

    def __str__(self):
        """Return the work item text.

        Returns:
            str: The todo description
        """
        return self.description
