# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Importance)
admin.site.register(Place)
admin.site.register(Urgency)
admin.site.register(Parent, ParentModelAdmin)
admin.site.register(Activity, ActivityModelAdmin)
admin.site.register(ActivityRecord)
admin.site.register(IdealDayTemplate)
admin.site.register(IdealDayTemplateRecord)
