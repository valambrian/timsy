from django.db import models

class Place(models.Model):
    """
    Represents different locations where activities can occur.
    
    This model stores information about physical locations where activities
    take place. Each place has a single-character abbreviation used for
    quick reference and a sort order for consistent display.
    
    Attributes:
        abbreviation (str): Single character abbreviation for the place (primary key)
        sort_order (int): Order in which places should be displayed (unique)
        description (str): Detailed description of the place (max 200 chars)
    """
    abbreviation = models.CharField(max_length=1, primary_key=True)
    sort_order = models.IntegerField(unique=True)
    description = models.CharField(max_length=200)
    
    def __str__(self):
        """Return the place's description as its string representation.
        
        Returns:
            str: The place's description
        """
        return self.description

    @classmethod
    def get_abbreviations(cls):
        """Get all place abbreviations in their sort order.
        
        Returns:
            list: List of place abbreviations ordered by sort_order
        """
        return [place.abbreviation for place in Place.objects.all().order_by('sort_order')]
