# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Activity)
admin.site.register(ActivityRecord)
admin.site.register(Importance)
admin.site.register(Parent)
admin.site.register(Place)
admin.site.register(Urgency)
