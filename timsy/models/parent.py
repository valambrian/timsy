from django.db import models
from django.contrib import admin
from .importance import Importance


class Parent(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    sort_order = models.IntegerField()
    abbreviation = models.CharField(max_length=5)
    description = models.CharField(max_length=200)
    importance = models.ForeignKey(Importance, on_delete=models.PROTECT)
    discretionary = models.BooleanField()
    target_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.description

    @classmethod
    def get_choices(cls):
        return [(obj.id, obj.description) for obj in cls.objects.all()]

    @classmethod
    def get_active_choices(cls):
        return [(obj.id, obj.description) for obj in cls.objects.filter(active=True)]


class ParentModelAdmin(admin.ModelAdmin):
    search_fields = ['id']
