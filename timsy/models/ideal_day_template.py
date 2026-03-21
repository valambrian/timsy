from django.db import models
from .activity import Activity
from .place import Place


class IdealDayTemplate(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField()

    def __str__(self):
        return self.name

    @classmethod
    def get_choices(cls):
        return [(obj.id, obj.name) for obj in cls.objects.all()]


class IdealDayTemplateRecord(models.Model):
    template = models.ForeignKey(IdealDayTemplate, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.TimeField()
    duration = models.TimeField()

    def __str__(self):
        return "%s (%s starting %s)" % (self.activity, self.duration, self.start)
