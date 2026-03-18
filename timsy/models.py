from django.db import models
from django.contrib import admin

import datetime


# Create your models here.
class Importance(models.Model):
    sort_order = models.IntegerField()
    abbreviation = models.CharField(max_length=1)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.description


class Urgency(models.Model):
    sort_order = models.IntegerField()
    abbreviation = models.CharField(max_length=1)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.description


class Place(models.Model):
    abbreviation = models.CharField(max_length=1, primary_key=True)
    sort_order = models.IntegerField(unique=True)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.description


class Parent(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    sort_order = models.IntegerField()
    abbreviation = models.CharField(max_length=5)
    description = models.CharField(max_length=200)
    importance = models.ForeignKey(Importance, on_delete=models.PROTECT)
    discretionary = models.BooleanField()
    target_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.description


class ParentModelAdmin(admin.ModelAdmin):
    search_fields = ['id']  # Adjust this to the fields you want searchable


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


class ActivityModelAdmin(admin.ModelAdmin):
    autocomplete_fields = ['parent']


class ActivityRecord(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.DateTimeField()
    duration = models.TimeField()

    def __str__(self):
        return "%s (%s starting %s)" % (self.activity, self.duration, self.start)


class IdealDayTemplate(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField()

    def __str__(self):
        return self.name


class IdealDayTemplateRecord(models.Model):
    template = models.ForeignKey(IdealDayTemplate, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    place = models.ForeignKey(Place, on_delete=models.PROTECT)
    start = models.TimeField()
    duration = models.TimeField()

    def __str__(self):
        return "%s (%s starting %s)" % (self.activity, self.duration, self.start)
