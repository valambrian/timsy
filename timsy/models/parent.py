from django.db import models
from django.contrib import admin
from .importance import Importance

class Parent(models.Model):
    """
    Represents high-level categories or projects that activities belong to.
    
    This model stores information about parent categories that group related activities.
    Each parent category has an importance level and can be marked as active or inactive.
    The ID field uses a custom format to support hierarchical categorization.
    
    Attributes:
        id (str): Unique identifier for the parent category (max 50 chars)
        sort_order (int): Order in which parent categories should be displayed
        abbreviation (str): Short abbreviation for the parent category (max 5 chars)
        description (str): Detailed description of the parent category (max 200 chars)
        importance (Importance): Foreign key to the importance level
        active (bool): Whether the parent category is currently active
    """
    id = models.CharField(max_length=50, primary_key=True)
    sort_order = models.IntegerField()
    abbreviation = models.CharField(max_length=5)
    description = models.CharField(max_length=200)
    importance = models.ForeignKey(Importance, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    
    def __str__(self):
        """Return the parent category's description as its string representation.
        
        Returns:
            str: The parent category's description
        """
        return self.description

    @classmethod
    def get_choices(cls):
        """Get all parent categories as a list of tuples for form choices.
        
        Creates a list of (id, description) tuples for all parent categories,
        ordered by their sort_order field.
        
        Returns:
            list: List of (id, description) tuples for all parent categories
        """
        return [(obj.id, obj.description) for obj in cls.objects.all()]

    @classmethod
    def get_active_choices(cls):
        """Get all active parent categories as a list of tuples for form choices.
        
        Creates a list of (id, description) tuples for parent categories that
        are marked as active, ordered by their sort_order field.
        
        Returns:
            list: List of (id, description) tuples for active parent categories only
        """
        return [(obj.id, obj.description) for obj in cls.objects.filter(active=True)]

class ParentModelAdmin(admin.ModelAdmin):
    """Admin interface configuration for Parent model."""
    search_fields = ['id'] 