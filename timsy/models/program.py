from django.db import models
from .parent import Parent


class Program(models.Model):
    """
    Represents a planning program associated with a parent category.

    Each parent can have zero or more programs. Edit updates the latest
    program in place. Clone (or New, when none exists) creates a new row
    with the current timestamp and a copied description. The date drop-down
    lists all versions newest first; older versions are viewable and
    cloneable but not editable.

    Attributes:
        parent (Parent): Foreign key to the parent category
        timestamp (datetime): When this program version was created
        description (str): Lengthy free-text description of the program
    """
    parent = models.ForeignKey(Parent, on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['parent', '-timestamp']),
        ]

    def __str__(self):
        """Return a string representation of the program.

        Returns:
            str: Parent description and the program date
        """
        return "%s (%s)" % (self.parent, self.timestamp.date())

    @classmethod
    def get_latest_for_parent(cls, parent):
        """Return the most recent program for a parent, if any.

        Args:
            parent: The parent category

        Returns:
            Program or None: The latest program by timestamp, or None if none exist
        """
        return cls.objects.filter(parent=parent).order_by('-timestamp').first()

    @classmethod
    def get_all_for_parent(cls, parent):
        """Return all programs for a parent, newest first.

        Args:
            parent: The parent category

        Returns:
            QuerySet: Programs for the parent ordered by timestamp descending
        """
        return cls.objects.filter(parent=parent).order_by('-timestamp')
