from datetime import date, datetime, time, timedelta
from django.db import models
from django.utils.timezone import make_aware

from .activity import Activity
from .place import Place

class ActivityRecord(models.Model):
    """
    Represents a record of when an activity was performed.

    This model stores information about individual activity sessions, including
    when they occurred, how long they lasted, where they took place, and an
    optional note. Each record is linked to a specific activity and place.

    Attributes:
        activity (Activity): Foreign key to the activity performed
        place (Place): Foreign key to the place where activity occurred
        start (datetime): When the activity started (indexed for efficient querying)
        duration (time): How long the activity lasted
        note (str): Optional free-text note for this session
    """
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.DateTimeField(db_index=True)
    duration = models.TimeField()
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        """Return a string representation of the activity record.
        
        Returns:
            str: String in format "Activity (Duration starting StartTime)"
        """
        return "%s (%s starting %s)" % (self.activity, self.duration, self.start)

    def date(self):
        """Get the date when the activity occurred.
        
        Returns:
            date: The date part of the start time
        """
        return self.start.date()

    def date_string(self):
        """Get a formatted string representation of the activity date.
        
        Returns:
            str: Date in format "Day, Month DD, YYYY"
        """
        return self.start.strftime("%A, %B %d, %Y")

    def update_duration(self, hour, minute):
        """Update the duration of the activity record.
        
        Args:
            hour (int): New hour value for duration
            minute (int): New minute value for duration
        """
        if self.duration.hour == hour and self.duration.minute == minute:
            return

        self.duration = time(hour, minute)
        self.save()

    def update_note(self, note):
        """Update the note of the activity record.

        Empty strings are stored as NULL. The record is saved only if the
        note value changed.

        Args:
            note (str or None): New note text, or empty/None to clear
        """
        if note:
            note = note.strip() or None
        else:
            note = None

        if self.note == note:
            return

        self.note = note
        self.save()

    def save(self, *args, **kwargs):
        """Save the activity record, storing blank notes as NULL."""
        if self.note is not None:
            self.note = self.note.strip() or None
        super().save(*args, **kwargs)

    def as_hash(self):
        """Convert activity record data to a dictionary format for serialization.
        
        Creates a dictionary containing all relevant information about the activity
        record, including its timing, location, and associated activity details.
        
        Returns:
            dict: Dictionary containing:
                - date: Formatted date string
                - start_hour, start_minute: Hour and minute of start time
                - duration_hour, duration_minute: Hour and minute of duration
                - start: Formatted start time (HH:MM)
                - duration: Formatted duration (HH:MM)
                - place: Place abbreviation
                - abbreviation: Activity abbreviation
                - description: Activity description
                - parent: Parent category description
                - importance: Importance level description
                - urgency: Urgency level description
                - note: Optional session note (empty string if none)
        """
        return {
            "date": self.date_string(),
            "start_hour": self.start.hour,
            "start_minute": self.start.minute,
            "duration_hour": self.duration.hour,
            "duration_minute": self.duration.minute,
            "start": ("%s:%s") % (self.start.hour, self.start.minute),
            "duration": ("%s:%s") % (self.duration.hour, self.duration.minute),
            "place": self.place.abbreviation,
            "abbreviation": self.activity.abbreviation,
            "description": self.activity.description,
            "parent": self.activity.parent.description,
            "importance": self.activity.importance.description,
            "urgency": self.activity.urgency.description,
            "note": self.note or ""
        }

    @classmethod
    def get_latest(cls):
        """Get the most recent activity record.
        
        Returns:
            ActivityRecord: The activity record with the latest start time
        """
        return cls.objects.latest('start')

    @classmethod
    def get_records(cls, start_date, end_date):
        """Get all activity records within a date range.
        
        Args:
            start_date (date): Start date of the range (inclusive)
            end_date (date): End date of the range (inclusive)
            
        Returns:
            QuerySet: Activity records ordered by start time
        """
        lower_bound = make_aware(datetime.combine(start_date, time.min))
        upper_bound = make_aware(datetime.combine(end_date, time.min) + timedelta(days=1))
        # lower_bound <= record.start < upper_bound
        return ActivityRecord.objects.filter(start__gte=lower_bound, start__lt=upper_bound).order_by('start')

    @classmethod
    def get_first_activity_record_of_the_day(cls, date):
        """Get the first activity record for a specific date.
        
        Args:
            date (date): The date to find the first activity for
            
        Returns:
            ActivityRecord or None: The first activity record of the day, or None if no records exist
        """
        return cls.objects.filter(date=date).first()