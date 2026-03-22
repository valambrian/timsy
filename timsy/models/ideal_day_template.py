from django.db import models
from .activity import Activity
from .place import Place

class IdealDayTemplate(models.Model):
    """
    Represents a template for planning an ideal day's schedule.
    
    This model stores templates that define how an ideal day should be structured,
    including which activities should occur and when. Templates can be marked as
    active or inactive to control which ones are available for use.
    
    Attributes:
        name (str): Name of the template (max 200 chars)
        is_active (bool): Whether the template is currently active and available for use
    """
    name = models.CharField(max_length=200)
    is_active = models.BooleanField()
    
    def __str__(self):
        """Return the template's name as its string representation.
        
        Returns:
            str: The template's name
        """
        return self.name

    def get_records(self):
        """Return the template's records as a list.

        Returns:
            list: The template's list of records
        """
        return IdealDayTemplateRecord.objects.filter(template=self).order_by('start')

    @classmethod
    def get_choices(cls):
        """Get all ideal day templates as a list of tuples for form choices.
        
        Returns:
            list: List of (id, name) tuples for use in form choice fields
        """
        return [(obj.id, obj.name) for obj in cls.objects.all()]

class IdealDayTemplateRecord(models.Model):
    """
    Represents an activity in an ideal day template.
    
    This model defines a single activity entry within an ideal day template,
    specifying when and where the activity should occur and how long it should last.
    Each record is part of a template and references a specific activity and place.
    
    Attributes:
        template (IdealDayTemplate): Foreign key to the parent template
        activity (Activity): Foreign key to the activity to be performed
        place (Place): Foreign key to where the activity should occur
        start (time): When the activity should start in the day
        duration (time): How long the activity should last
    """
    template = models.ForeignKey(IdealDayTemplate, on_delete=models.PROTECT)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.TimeField()
    duration = models.DurationField()
    
    def __str__(self):
        """Return a string representation of the template record.
        
        Returns:
            str: String in format "activity (duration starting start_time)"
        """
        return "%s (%s starting %s)" % (self.activity, self.duration, self.start) 