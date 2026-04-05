from django.db import models
from .activity import Activity
from .place import Place
from django.core.exceptions import ValidationError

class DailyPlan(models.Model):
    """
    Represents a daily plan for a specific date.
    
    This model stores plans for specific days. Plans contain individual entries
    that define activities, their timing, and locations.
    
    Attributes:
        date (date): The date for which this plan is created
    """
    date = models.DateField(unique=True)  # Only one plan per date
    
    def __str__(self):
        """Return a string representation of the daily plan.
        
        Returns:
            str: String in format "Plan for date"
        """
        return f"Plan for {self.date}"
    


    def get_entries(self):
        """Return the plan's entries as a list.

        Returns:
            list: The plan's list of entries ordered by start time
        """
        return DailyPlanEntry.objects.filter(plan=self).order_by('start')

class DailyPlanEntry(models.Model):
    """
    Represents an activity in a daily plan.
    
    This model defines a single activity entry within a daily plan,
    specifying when and where the activity should occur and how long it should last.
    Each entry is part of a plan and references a specific activity and place.
    
    Attributes:
        plan (DailyPlan): Foreign key to the parent plan
        activity (Activity): Foreign key to the activity to be performed
        place (Place): Foreign key to where the activity should occur
        start (time): When the activity should start in the day
        duration (time): How long the activity should take
    """
    plan = models.ForeignKey(DailyPlan, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.TimeField()
    duration = models.TimeField()
    
    def __str__(self):
        """Return a string representation of the plan entry.
        
        Returns:
            str: String in format "activity (duration starting start_time) at place"
        """
        return "%s (%s starting %s) at %s" % (self.activity, self.duration, self.start, self.place)
    
    class Meta:
        ordering = ['start'] 