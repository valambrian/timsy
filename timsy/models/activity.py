from django.db import models
from django.contrib import admin
from .parent import Parent
from .importance import Importance
from .urgency import Urgency


class Activity(models.Model):
    sort_order = models.IntegerField(null=True, blank=True)
    abbreviation = models.CharField(max_length=10, blank=True)
    description = models.CharField(max_length=200)
    parent = models.ForeignKey(Parent, on_delete=models.PROTECT)
    importance = models.ForeignKey(Importance, on_delete=models.PROTECT)
    urgency = models.ForeignKey(Urgency, on_delete=models.PROTECT)
    can_start_today = models.BooleanField()

    def __str__(self):
        return self.description

    def as_hash(self):
        return {
            "description": self.description,
            "parent": self.parent.description,
            "importance": self.importance.description,
            "urgency": self.urgency.description
        }


class ActivityModelAdmin(admin.ModelAdmin):
    autocomplete_fields = ['parent']
