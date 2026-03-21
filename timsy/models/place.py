from django.db import models


class Place(models.Model):
    abbreviation = models.CharField(max_length=1, primary_key=True)
    sort_order = models.IntegerField(unique=True)
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.description
