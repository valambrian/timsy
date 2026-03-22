from django.db import models
from .activity import Activity
from .place import Place

class Blueprint(models.Model):
    """
    Represents a blueprint for planning activities.
    
    This model stores blueprint that define how a day of a part of it should be structured,
    including which activities should occur, where and when. Blueprints can be marked as
    active or inactive to control which ones are available for use.
    
    Attributes:
        name (str): Name of the blueprint (max 200 chars)
        is_active (bool): Whether the blueprint is currently active and available for use
    """
    name = models.CharField(max_length=200)
    is_active = models.BooleanField()
    
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