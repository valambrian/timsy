from django.db import models
from .ideal_day_template import IdealDayTemplate
from .activity import Activity
from .place import Place
from django.core.exceptions import ValidationError

class DailyPlan(models.Model):
    """
    Represents a daily plan based on an ideal day template.
    
    This model stores plans for specific days, each linked to an ideal day template
    that serves as a blueprint for the day's activities.
    
    Attributes:
        date (date): The date for which this plan is created
        template (IdealDayTemplate): Foreign key to the ideal day template used for this plan
    """
    date = models.DateField(unique=True)  # Only one plan per date
    template = models.ForeignKey(IdealDayTemplate, on_delete=models.PROTECT)
    
    def __str__(self):
        """Return a string representation of the daily plan.
        
        Returns:
            str: String in format "Plan for date using template_name"
        """
        return f"Plan for {self.date} using {self.template.name}"
    
    @classmethod
    def generate_daily_plan(cls, date, template):
        """Generate a new daily plan from a template.
        
        This method creates a new daily plan for the specified date using the given template.
        It automatically creates all plan entries based on the template's records.
        If a plan already exists for the date, it will be updated with the new template.
        
        Args:
            date (date): The date for which to create the plan
            template (IdealDayTemplate): The template to use for generating the plan
            
        Returns:
            DailyPlan: The newly created or updated daily plan
        """
        # Get or create the plan for this date
        plan, created = cls.objects.get_or_create(
            date=date,
            defaults={'template': template}
        )
        
        if not created:
            # Update existing plan with new template
            plan.template = template
            plan.save()
            # Delete existing entries
            plan.get_entries().delete()
        
        # Get all records from the template
        template_records = template.get_records()
        
        # Create plan entries for each template record
        for record in template_records:
            DailyPlanEntry.objects.create(
                plan=plan,
                activity=record.activity,
                place=record.place,
                start=record.start,
                duration=record.duration
            )
            
        return plan

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
        duration (time): How long the activity should last
    """
    plan = models.ForeignKey(DailyPlan, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.TimeField()
    duration = models.DurationField()
    
    def __str__(self):
        """Return a string representation of the plan entry.
        
        Returns:
            str: String in format "activity (duration starting start_time)"
        """
        return "%s (%s starting %s)" % (self.activity, self.duration, self.start)
    
    class Meta:
        ordering = ['start'] 