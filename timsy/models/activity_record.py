from django.db import models
from .activity import Activity
from .place import Place


class ActivityRecord(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.DateTimeField()
    duration = models.TimeField()

    def __str__(self):
        return "%s (%s starting %s)" % (self.activity, self.duration, self.start)

    def as_hash(self):
        return {
            "date": self.start.strftime("%A, %B %d, %Y"),
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
            "urgency": self.activity.urgency.description
        }
