from django.db import models
from django.contrib import admin
from .importance import Importance

class Parent(models.Model):
    """
    Represents high-level categories or projects that activities belong to.

    This model stores information about parent categories that group related activities.
    Each parent category has an importance level and a lifecycle state.
    The ID field uses a custom format to support hierarchical categorization.

    Attributes:
        id (str): Unique identifier for the parent category (max 50 chars)
        sort_order (int): Order in which parent categories should be displayed
        description (str): Detailed description of the parent category (max 200 chars)
        importance (Importance): Foreign key to the importance level
        state (str): pending, active, paused, completed, or cancelled
    """

    class State(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.CharField(max_length=50, primary_key=True)
    sort_order = models.IntegerField()
    description = models.CharField(max_length=200)
    importance = models.ForeignKey(Importance, on_delete=models.PROTECT)
    state = models.CharField(
        max_length=9,
        choices=State.choices,
        default=State.ACTIVE,
    )

    def __str__(self):
        """Return the parent category's description as its string representation.
        
        Returns:
            str: The parent category's description
        """
        return self.description

    @classmethod
    def _in_hierarchy_order(cls):
        """Yield parents depth-first: top-level first, then each level's children.

        Sibling groups follow ``sort_order`` via ``get_direct_children``.

        Yields:
            Parent: The next parent in hierarchy order
        """
        def walk(parent_id):
            for child in cls.get_direct_children(parent_id):
                yield child
                yield from walk(child.id)

        yield from walk("ALL")

    @classmethod
    def get_choices(cls):
        """Get all parent categories as a list of tuples for form choices.

        Order is the parent hierarchy: top-level by sort_order, then each
        parent's subparents by sort_order, and so on.

        Returns:
            list: List of (id, description) tuples for all parent categories
        """
        return [(obj.id, obj.description) for obj in cls._in_hierarchy_order()]

    @classmethod
    def get_active_choices(cls):
        """Get all active parent categories as a list of tuples for form choices.

        Same hierarchy order as ``get_choices``, limited to active parents.

        Returns:
            list: List of (id, description) tuples for active parent categories only
        """
        return [
            (obj.id, obj.description)
            for obj in cls._in_hierarchy_order()
            if obj.state == cls.State.ACTIVE
        ]

    @classmethod
    def get_direct_children(cls, parent: str):
        """Get direct children of a parent category based on id hierarchy.
        
        Args:
            parent: Parent id ('ALL' for top-level, or specific parent like 'RT')
            
        Returns:
            QuerySet: Parent objects that are direct children of the specified parent
        """
        if parent == "ALL":
            # Return top-level parents (2-character ids)
            return cls.objects.filter(id__regex=r'^.{2}$').order_by('sort_order')
        else:
            # Return children with pattern: parent + '-' + 2 characters
            pattern = f"^{parent}-.{{2}}$"
            return cls.objects.filter(id__regex=pattern).order_by('sort_order')

class ParentModelAdmin(admin.ModelAdmin):
    """Admin interface configuration for Parent model."""
    search_fields = ['id'] 