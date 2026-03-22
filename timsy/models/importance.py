from django.db import models

class Importance(models.Model):
    """
    Represents the importance level of activities.
    
    This model defines different levels of importance that can be assigned to
    activities. Each importance level has a sort order for consistent display,
    a single-character abbreviation for quick reference, and a detailed description.
    
    Attributes:
        sort_order (int): Order in which importance levels should be displayed (unique)
        abbreviation (str): Single character abbreviation for the importance level
        description (str): Detailed description of the importance level (max 200 chars)
    """
    sort_order = models.IntegerField()
    abbreviation = models.CharField(max_length=1)
    description = models.CharField(max_length=200)
    
    def __str__(self):
        """Return the importance level's description as its string representation.
        
        Returns:
            str: The importance level's description
        """
        return self.description

    @classmethod
    def get_choices(cls):
        """Get all importance levels as a list of tuples for form choices.
        
        Returns:
            list: List of (id, description) tuples for use in form choice fields
        """
        return [(obj.id, obj.description) for obj in cls.objects.all()] 