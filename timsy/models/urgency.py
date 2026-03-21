from django.db import models


class Urgency(models.Model):
    sort_order = models.IntegerField()
    abbreviation = models.CharField(max_length=1)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.description

    @classmethod
    def get_choices(cls):
        return [(obj.id, obj.description) for obj in cls.objects.all()]
