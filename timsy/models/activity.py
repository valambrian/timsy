from django.db import models
from django.contrib import admin
from .parent import Parent
from .importance import Importance
from .urgency import Urgency

class Activity(models.Model):
    """
    Represents individual tasks or activities to be tracked.
    
    This model stores information about activities including their categorization,
    priority levels, and display order. Activities can be organized under parent
    categories and have associated importance and urgency levels.
    
    Attributes:
        sort_order (int): Order in which activities should be displayed
        abbreviation (str): Short abbreviation for the activity (max 10 chars)
        description (str): Detailed description of the activity (max 200 chars)
        parent (Parent): Foreign key to the parent category
        importance (Importance): Foreign key to the importance level
        urgency (Urgency): Foreign key to the urgency level
    """
    sort_order = models.IntegerField(null=True, blank=True)
    abbreviation = models.CharField(max_length=10, blank=True, db_index=True)
    description = models.CharField(max_length=200)
    parent = models.ForeignKey(Parent, on_delete=models.PROTECT)
    importance = models.ForeignKey(Importance, on_delete=models.PROTECT)
    urgency = models.ForeignKey(Urgency, on_delete=models.PROTECT)

    def __str__(self):
        """Return the activity's description as its string representation.
        
        Returns:
            str: The activity's description
        """
        return self.description
        
    def as_hash(self):
        """Convert activity data to a dictionary format for serialization.
        
        Creates a dictionary containing the activity's description and related
        information from its parent, importance, and urgency relationships.
        
        Returns:
            dict: Dictionary containing:
                - description: Activity description
                - parent: Parent category description
                - importance: Importance level description
                - urgency: Urgency level description
        """
        return {
            "description": self.description,
            "parent": self.parent.description,
            "importance": self.importance.description,
            "urgency": self.urgency.description
        }

    @classmethod
    def find_or_create(cls, abbreviation, description, parent, importance, urgency):
        """Find an existing activity or create a new one if not found.
        
        Searches for an activity by abbreviation first, then by description.
        If no matching activity is found, creates a new one with the provided details.
        
        Args:
            abbreviation (str): The activity's abbreviation
            description (str): The activity's description
            parent (Parent): The parent category
            importance (Importance): The importance level
            urgency (Urgency): The urgency level
            
        Returns:
            Activity: The found or newly created activity
        """
        # find the activity by abbreviation
        if abbreviation:
            activity = cls.objects.all().filter(abbreviation=abbreviation).first()
            if activity:
                return activity

        # no abbreviation entered - search by description
        activity = cls.objects.all().filter(description=description).first()
        if activity:
            return activity

        activity = Activity(sort_order=999,
                            abbreviation=abbreviation,
                            description=description,
                            parent=parent,
                            importance=importance,
                            urgency=urgency)
        activity.save()
        return activity

class ActivityModelAdmin(admin.ModelAdmin):
    """Admin interface configuration for Activity model."""
    autocomplete_fields = ['parent'] 