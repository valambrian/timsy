# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, time, timedelta
from django.utils.timezone import make_aware
import json

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django import forms

from .models import Activity, ActivityRecord, Importance, Parent, Place, Urgency, IdealDayTemplate

# common functionality	
def get_last_activity_record(request):
    if request.method == 'GET':
        record = ActivityRecord.objects.all().order_by('-start')[0]
        return HttpResponse(json.dumps(record.as_hash()))

def get_activity(request, abbreviation):
    if request.method == 'GET':
        record = Activity.objects.filter(abbreviation=abbreviation).first()
        response_dict = record.as_hash() if record else {}
        return HttpResponse(json.dumps(response_dict))

def urgencies():
    return [(obj.id, obj.description) for obj in Urgency.objects.all()]

def importances():
    return [(obj.id, obj.description) for obj in Importance.objects.all()]

def parents():
    return [(obj.id, obj.description) for obj in Parent.objects.all()]

def ideal_day_templates():
    return [(obj.id, obj.name) for obj in IdealDayTemplate.objects.all()]

def get_first_record_of(date):
    start_of_day = make_aware(datetime.combine(date, datetime.min.time()))
    end_of_day = make_aware(datetime.combine(date, datetime.max.time()))

    return ActivityRecord.objects.filter(
        start__range=(start_of_day, end_of_day)
    ).order_by('start').first()

def get_first_record_in_range(start_date, end_date):
    start_of_period = make_aware(datetime.combine(start_date, datetime.min.time()))
    end_of_period = make_aware(datetime.combine(end_date, datetime.min.time()))

    return ActivityRecord.objects.filter(
        start__range=(start_of_period, end_of_period)
    ).order_by('start').first()

def timestamp_string(seconds):
	if not seconds:
		return "----"
	minutes = int(seconds / 60)
	hours = int(minutes / 60)
	minutes -= 60 * hours
	return "%d:%02d" % (hours, minutes)

# top level page
def index(request):
	template = loader.get_template('timsy.html')
	return HttpResponse(template.render({}, request))

# daily time use log view
def daily_log(request, year, month, day):
    """Create daily time use log report"""
    report_date = date(year=int(year), month=int(month), day=int(day))
    previous = get_first_record_of(report_date - timedelta(days=1))
    next = get_first_record_of(report_date + timedelta(days=1))
    records = ActivityRecord.objects.filter(start__year=year,
                                            start__month=month,
                                            start__day=day).order_by('start')
    template = loader.get_template('daily_log.html')
    context = {'records': records,
                'previous': previous,
                'next': next}
    return HttpResponse(template.render(context, request))

def latest_log(request):
    """Create the latest daily time use log report"""
    latest_record = ActivityRecord.objects.all().order_by('-start').first()
    year = latest_record.start.year
    month = latest_record.start.month
    day = latest_record.start.day
    return daily_log(request, year, month, day)

# daily / weekly / monthly / custom period summary report
class SummaryRecord():
    def __init__(self, id, description, places_lookup):
        self.id = id
        self.description = description
        self.places_lookup = places_lookup
        self.seconds = [0] * len(places_lookup)
    def add(self, place, seconds):
        index = self.places_lookup[place]
        self.seconds[index] += seconds
    def get_times(self):
        results = []
        total = 0
        for index in range(len(self.seconds)):
            current = self.seconds[index] 
            total += current
            results.append(timestamp_string(current))
        results.append(timestamp_string(total))
        return results

def summary(request, parent="ALL", frequency="custom",
            to_year=None, to_month=None, to_day=None,
            from_year=None, from_month=None, from_day=None):
    """Create summary time use report"""

    # the default end_date is the last activity's start date 
    if to_year is None or to_month is None or to_day is None:
        end_date_supplied = False
        end_date = ActivityRecord.objects.all().order_by('-start')[0].start
    else:
        end_date_supplied = True
        end_date = date(year=int(to_year), month=int(to_month), day=int(to_day))

    # the default start_date is the first activity's start date 
    if from_year is None or from_month is None or from_day is None:
        start_date_supplied = False
        start_date = ActivityRecord.objects.all().order_by('start')[0].start
    else:
        start_date_supplied = True
        start_date = date(year=int(from_year), month=int(from_month), day=int(from_day))

    # set some parameters based on report's frequency
    if frequency == "daily":
        # no data range for daily reports
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date
        else:
            # only start date is supplied
            end_date = start_date
        previous_date = get_first_record_of(start_date - timedelta(days=1))
        next_date = get_first_record_of(end_date + timedelta(days=1))
        if previous_date:
            previous = "/timsy/reports/summary/daily/%s/%d/%d/%d" % \
                        (parent,
                         previous_date.start.year,
                         previous_date.start.month,
                         previous_date.start.day)
        else:
            previous = None
        if next_date:
            next = "/timsy/reports/summary/daily/%s/%d/%d/%d" % \
                    (parent,
                     next_date.start.year,
                     next_date.start.month,
                     next_date.start.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/daily/"
        suffix = "/%d/%d/%d" % (end_date.year, end_date.month, end_date.day)
        title = "Daily Report For %s" % (end_date.strftime("%A, %B %d, %Y"), )
    elif frequency == "weekly":
        # weekly reports are Monday to Sunday
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date - timedelta(days=end_date.weekday())
            end_date = start_date + timedelta(days=6)
        else:
            # only start date is supplied
            end_date = start_date + timedelta(days=6-start_date.weekday())
            start_date = start_date - timedelta(days=start_date.weekday())
        previous_date = get_first_record_of(start_date - timedelta(days=7))
        next_date = get_first_record_of(start_date + timedelta(days=7))
        if previous_date:
            previous = "/timsy/reports/summary/weekly/%s/%d/%d/%d" % \
                        (parent,
                         previous_date.start.year,
                         previous_date.start.month,
                         previous_date.start.day)
        else:
            previous = None
        if next_date:
            next = "/timsy/reports/summary/weekly/%s/%d/%d/%d" % \
                    (parent,
                     next_date.start.year,
                     next_date.start.month,
                     next_date.start.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/weekly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        title = "Report For The Week of %s" % (start_date.strftime("%B %d, %Y"), )
    elif frequency == "my_weekly":
        # my weekly reports are Saturday to Friday
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date - timedelta(days=(end_date.weekday()+2)%7)
            end_date = start_date + timedelta(days=6)
        else:
            # only start date is supplied
            end_date = start_date + timedelta(days=6)
            start_date = start_date - timedelta(days=5-start_date.weekday())
        previous_date = get_first_record_of(start_date - timedelta(days=7))
        next_date = get_first_record_of(start_date + timedelta(days=7))
        if previous_date:
            previous = "/timsy/reports/summary/my_weekly/%s/%d/%d/%d" % \
                        (parent,
                         previous_date.start.year,
                         previous_date.start.month,
                         previous_date.start.day)
        else:
            previous = None
        if next_date:
            next = "/timsy/reports/summary/my_weekly/%s/%d/%d/%d" % \
                    (parent,
                     next_date.start.year,
                     next_date.start.month,
                     next_date.start.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/my_weekly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        title = "Report For The Week of %s" % (start_date.strftime("%B %d, %Y"), )
    elif frequency == "monthly":
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date.replace(day=1)
            if start_date.month < 12:
                end_date = start_date.replace(month=start_date.month+1) - timedelta(days=1)
            else:
                end_date = start_date.replace(day=31)
        else:
            # only start date is supplied
            start_date = start_date.replace(day=1)
            if start_date.month < 12:
                end_date = start_date.replace(month=start_date.month+1) - timedelta(days=1)
            else:
                end_date = start_date.replace(day=31)
        if start_date.month == 1:
            previous_start = date(year=start_date.year-1, month=12, day=1)
        else:
            previous_start = start_date.replace(month=start_date.month-1)
        previous_period_first_record = get_first_record_in_range(previous_start, start_date)
        next_period_first_record = get_first_record_of(end_date + timedelta(days=1))
        if previous_period_first_record:
            previous = "/timsy/reports/summary/monthly/%s/%d/%d/%d" % \
                        (parent,
                         previous_period_first_record.start.year,
                         previous_period_first_record.start.month,
                         previous_period_first_record.start.day)
        else:
            previous = None
        if next_period_first_record:
            next = "/timsy/reports/summary/monthly/%s/%d/%d/%d" % \
                    (parent,
                     next_period_first_record.start.year,
                     next_period_first_record.start.month,
                     next_period_first_record.start.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/monthly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        title = "Report For The Month of %s" % (start_date.strftime("%B %Y"), )

    else: # the default frequency is 'custom'
        delta = 1 + (end_date - start_date).days
        previous_start = get_first_record_in_range(start_date - timedelta(days=delta),
                                                  start_date)
        previous_end = end_date - timedelta(days=delta)
        next_start = get_first_record_of(start_date + timedelta(days=delta))
        next_end = end_date + timedelta(days=delta)
        if previous_start:
            previous = "/timsy/reports/summary/%s/%d/%d/%d/%d/%d/%d" % \
                        (parent,
                         previous_end.year,
                         previous_end.month,
                         previous_end.day,
                         previous_start.year,
                         previous_start.month,
                         previous_start.day)
        else:
            previous = None
        if next_start:
            next = "/timsy/reports/summary/%s/%d/%d/%d/%d/%d/%d" % \
                    (parent,
                     next_end.year,
                     next_end.month,
                     next_end.day,
                     next_start.year,
                     next_start.month,
                     next_start.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/"
        suffix = "/%d/%d/%d/%d/%d/%d" % (end_date.year,
                                         end_date.month,
                                         end_date.day,
                                         start_date.year,
                                         start_date.month,
                                         start_date.day)
        title = "Reporting Period: %s to %s" % \
                (start_date.strftime("%A, %B %d, %Y"),
                 end_date.strftime("%A, %B %d, %Y"))
    
    # retrieving time use records
    from django.db import connection, transaction
    cursor = connection.cursor()
    if parent == "ALL":
        parent_pattern = "__"
    else:
        parent_pattern = "%s-__" % (parent, )
    start_date_pattern = start_date.strftime("%Y-%m-%d")
    end_date_pattern = end_date.strftime("%Y-%m-%d")
    places = [place.abbreviation for place in Place.objects.all().order_by('sort_order')]
    places_lookup = {}
    for i in range(len(places)):
        places_lookup[places[i]] = i
    query = """select p.sort_order parent_order,
                      NULL activity_order,
                      p.id,
                      p.description,
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_parent p,
                      timsy_activity a,
                      timsy_activityrecord r
                where p.id like '%s' 
                  and a.parent_id like CONCAT(p.id, '%%%%')
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by p.sort_order,
                      p.id,
                      p.description,
                      r.place_id
                union
               select NULL parent_order,
                      a.sort_order activity_order,
                      '',
                      a.description,
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_activityrecord r,
                      timsy_activity a
                where a.parent_id = '%s'
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by a.sort_order,
                      a.description,
                      r.place_id
             order by activity_order,
                      parent_order""" % (parent_pattern,
                                         start_date_pattern,
                                         end_date_pattern,
                                         parent,
                                         start_date_pattern,
                                         end_date_pattern)
    cursor.execute(query)
    rows = cursor.fetchall()
    records = []
    records_lookup = {}
    total_record = SummaryRecord(id="", description="Total", places_lookup=places_lookup)
    for row in rows:
        id = row[2]
        description = row[3]
        place = row[4]
        seconds = row[5]
        if not description in records_lookup:
            records_lookup[description] = len(records)
            records.append(SummaryRecord(id=id, description=description, places_lookup=places_lookup))
        record = records[records_lookup[description]]
        record.add(place, seconds)    
        total_record.add(place, seconds)
    records.append(total_record)
    template = loader.get_template('summary_report.html')
    context = {'records': records,
               'places': places,
               'title': title,
               'prefix': prefix,
               'suffix': suffix,
               'previous': previous,
               'next': next}
    return HttpResponse(template.render(context, request))

def daily_summary(request, parent, year, month, day):
    """Create daily summary time use report"""
    return summary(request=request, frequency="daily", parent=parent,
                   to_year=year, to_month=month, to_day=day)

def latest_daily_summary(request):
    """Create the latest daily summary time use report"""
    return summary(request=request, frequency="daily")

def weekly_summary(request, parent, year, month, day):
    """Create weekly summary time use report"""
    return summary(request=request, frequency="weekly", parent=parent,
                   from_year=year, from_month=month, from_day=day)

def latest_weekly_summary(request):
    """Create the latest weekly summary time use report"""
    return summary(request=request, frequency="weekly")

def my_weekly_summary(request, parent, year, month, day):
    """Create summary time use report for a week starting on Saturday"""
    return summary(request=request, frequency="my_weekly", parent=parent,
                   from_year=year, from_month=month, from_day=day)

def latest_my_weekly_summary(request):
    """Create the latest summary time use report for a week starting on Saturday"""
    return summary(request=request, frequency="my_weekly")

def monthly_summary(request, parent, year, month, day):
    """Create monthly summary time use report"""
    return summary(request=request, frequency="monthly", parent=parent,
                   from_year=year, from_month=month, from_day=day)

def latest_monthly_summary(request):
    """Create the latest monthly summary time use report"""
    return summary(request=request, frequency="monthly")

def custom_summary(request, parent, to_year, to_month, to_day,
                   from_year, from_month, from_day):
    return summary(request=request, parent=parent,
                   to_year=to_year, to_month=to_month, to_day=to_day,
                   from_year=from_year, from_month=from_month, from_day=from_day)

# weekly-daily report
class DailyBreakdownSummaryRecord():
    def __init__(self, id, description, dates_lookup, places_lookup):
        self.id = id
        self.description = description
        self.dates_lookup = dates_lookup
        self.places_lookup = places_lookup
        self.seconds_per_date = [0] * len(dates_lookup)
        self.seconds_per_place = [0] * len(places_lookup)
    def add(self, date, place, seconds):
        index = self.dates_lookup[date]
        self.seconds_per_date[index] += seconds
        index = self.places_lookup[place]
        self.seconds_per_place[index] += seconds
    def get_times(self):
        results = []
        total = 0
        for index in range(len(self.seconds_per_date)):
            current = self.seconds_per_date[index] 
            total += current
            results.append(timestamp_string(current))
        for index in range(len(self.seconds_per_place)):
            current = self.seconds_per_place[index] 
            results.append(timestamp_string(current))
        results.append(timestamp_string(total))
        return results

def daily_breakdown(request, parent="ALL", frequency="custom",
            to_year=None, to_month=None, to_day=None,
            from_year=None, from_month=None, from_day=None):
    """Create time use report with daily breakdown"""

    from datetime import date, datetime, time, timedelta

    # the default end_date is the last activity's start date 
    if to_year is None or to_month is None or to_day is None:
        end_date_supplied = False
        end_date = ActivityRecord.objects.all().order_by('-start')[0].start
    else:
        end_date_supplied = True
        end_date = date(year=int(to_year), month=int(to_month), day=int(to_day))

    # the default start_date is the first activity's start date 
    if from_year is None or from_month is None or from_day is None:
        start_date_supplied = False
        start_date = ActivityRecord.objects.all().order_by('start')[0].start
    else:
        start_date_supplied = True
        start_date = date(year=int(from_year), month=int(from_month), day=int(from_day))

    # set some parameters based on report's frequency
    if frequency == "daily":
        # no data range for daily reports
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date
        else:
            # only start date is supplied
            end_date = start_date
        previous_date = get_first_record_of(start_date - timedelta(days=1))
        next_date = get_first_record_of(end_date + timedelta(days=1))
        if previous_date:
            previous = "/timsy/reports/summary/daily/%s/%d/%d/%d" % \
                        (parent,
                         previous_date.year,
                         previous_date.month,
                         previous_date.day)
        else:
            previous = None
        if next_date:
            next = "/timsy/reports/summary/daily/%s/%d/%d/%d" % \
                    (parent,
                     next_date.year,
                     next_date.month,
                     next_date.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/daily/"
        suffix = "/%d/%d/%d" % (end_date.year, end_date.month, end_date.day)
        title = "Daily Report For %s" % (end_date.strftime("%A, %B %d, %Y"), )
    elif frequency == "weekly":
        # weekly reports are Monday to Sunday
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date - timedelta(days=end_date.weekday())
            end_date = start_date + timedelta(days=6)
        else:
            # only start date is supplied
            end_date = start_date + timedelta(days=6-start_date.weekday())
            start_date = start_date - timedelta(days=start_date.weekday())
        previous_date = get_first_record_of(start_date - timedelta(days=7))
        next_date = get_first_record_of(start_date + timedelta(days=7))
        if previous_date:
            previous = "/timsy/reports/summary/weekly/%s/%d/%d/%d" % \
                        (parent,
                         previous_date.year,
                         previous_date.month,
                         previous_date.day)
        else:
            previous = None
        if next_date:
            next = "/timsy/reports/summary/weekly/%s/%d/%d/%d" % \
                    (parent,
                     next_date.year,
                     next_date.month,
                     next_date.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/weekly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        title = "Report For The Week of %s" % (start_date.strftime("%B %d, %Y"), )
    elif frequency == "my_weekly":
        # my weekly reports are Saturday to Friday
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date - timedelta(days=(end_date.weekday()+2)%7)
            end_date = start_date + timedelta(days=6)
        else:
            # only start date is supplied
            end_date = start_date + timedelta(days=6)
            start_date = start_date - timedelta(days=5-start_date.weekday())
        previous_date = get_first_record_of(start_date - timedelta(days=7))
        next_date = get_first_record_of(start_date + timedelta(days=7))
        if previous_date:
            previous = "/timsy/reports/summary/daily_week_breakdown/%s/%d/%d/%d" % \
                        (parent,
                         previous_date.start.year,
                         previous_date.start.month,
                         previous_date.start.day)
        else:
            previous = None
        if next_date:
            next = "/timsy/reports/summary/daily_week_breakdown/%s/%d/%d/%d" % \
                    (parent,
                     next_date.start.year,
                     next_date.start.month,
                     next_date.start.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/daily_week_breakdown/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        title = "Report For The Week of %s" % (start_date.strftime("%B %d, %Y"), )
    elif frequency == "monthly":
        if end_date_supplied or not start_date_supplied:
            # either end date is supplied or both dates are not
            start_date = end_date.replace(day=1)
            if start_date.month < 12:
                end_date = start_date.replace(month=start_date.month+1) - timedelta(days=1)
            else:
                end_date = start_date.replace(day=31)
        else:
            # only start date is supplied
            start_date = start_date.replace(day=1)
            if start_date.month < 12:
                end_date = start_date.replace(month=start_date.month+1) - timedelta(days=1)
            else:
                end_date = start_date.replace(day=31)
        if start_date.month == 1:
            previous_start = date(year=start_date.year-1, month=12, day=1)
        else:
            previous_start = start_date.replace(month=start_date.month-1)
        previous_date = get_first_record_in_range(previous_start, start_date)
        next_date = get_first_record_of(end_date + timedelta(days=1))
        if previous_date:
            previous = "/timsy/reports/summary/monthly/%s/%d/%d/%d" % \
                        (parent,
                         previous_date.year,
                         previous_date.month,
                         previous_date.day)
        else:
            previous = None
        if next_date:
            next = "/timsy/reports/summary/monthly/%s/%d/%d/%d" % \
                    (parent,
                     next_date.year,
                     next_date.month,
                     next_date.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/monthly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        title = "Report For The Month of %s" % (start_date.strftime("%B %Y"), )

    else: # the default frequency is 'custom'
        delta = 1 + (end_date - start_date).days
        previous_start = get_first_record_in_range(start_date - timedelta(days=delta),
                                                  start_date)
        previous_end = end_date - timedelta(days=delta)
        next_start = get_first_record_of(start_date + timedelta(days=delta))
        next_end = end_date + timedelta(days=delta)
        if previous_start:
            previous = "/timsy/reports/summary/%s/%d/%d/%d/%d/%d/%d" % \
                        (parent,
                         previous_end.year,
                         previous_end.month,
                         previous_end.day,
                         previous_start.year,
                         previous_start.month,
                         previous_start.day)
        else:
            previous = None
        if next_start:
            next = "/timsy/reports/summary/%s/%d/%d/%d/%d/%d/%d" % \
                    (parent,
                     next_end.year,
                     next_end.month,
                     next_end.day,
                     next_start.year,
                     next_start.month,
                     next_start.day)
        else:
            next = None
        prefix = "/timsy/reports/summary/"
        suffix = "/%d/%d/%d/%d/%d/%d" % (end_date.year,
                                         end_date.month,
                                         end_date.day,
                                         start_date.year,
                                         start_date.month,
                                         start_date.day)
        title = "Reporting Period: %s to %s" % \
                (start_date.strftime("%A, %B %d, %Y"),
                 end_date.strftime("%A, %B %d, %Y"))
    
    # retrieving time use records
    from django.db import connection, transaction
    cursor = connection.cursor()
    if parent == "ALL":
        parent_pattern = "__"
    else:
        parent_pattern = "%s-__" % (parent, )
    start_date_pattern = start_date.strftime("%Y-%m-%d")
    end_date_pattern = end_date.strftime("%Y-%m-%d")
	
    days = (end_date - start_date).days + 1
    dates = [None] * days
    dates_lookup = {}
    for i in range(days):
        date = start_date + timedelta(days = i)
        dates_lookup[date.strftime("%Y-%m-%d")] = i
        dates[i] = date.strftime("%A, %m/%d")
	
    places = [place.abbreviation for place in Place.objects.all().order_by('sort_order')]
    places_lookup = {}
    for i in range(len(places)):
        places_lookup[places[i]] = i
    query = """select p.sort_order parent_order,
                      NULL activity_order,
                      p.id,
                      p.description,
					  date(r.start),
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_parent p,
                      timsy_activity a,
                      timsy_activityrecord r
                where p.id like '%s' 
                  and a.parent_id like CONCAT(p.id, '%%%%')
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by p.sort_order,
                      p.id,
                      p.description,
					  date(r.start),
                      r.place_id
                union
               select NULL parent_order,
                      a.sort_order activity_order,
                      '',
                      a.description,
					  date(r.start),
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_activityrecord r,
                      timsy_activity a
                where a.parent_id = '%s'
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by a.sort_order,
                      a.description,
					  date(r.start),
                      r.place_id
             order by activity_order,
                      parent_order""" % (parent_pattern,
                                         start_date_pattern,
                                         end_date_pattern,
                                         parent,
                                         start_date_pattern,
                                         end_date_pattern)
    cursor.execute(query)
    rows = cursor.fetchall()
    records = []
    records_lookup = {}
    total_record = DailyBreakdownSummaryRecord(id="", description="Total", dates_lookup=dates_lookup, places_lookup=places_lookup)
    for row in rows:
        id = row[2]
        description = row[3]
        date = row[4].strftime("%Y-%m-%d")
        place = row[5]
        seconds = row[6]
        if not description in records_lookup:
            records_lookup[description] = len(records)
            records.append(DailyBreakdownSummaryRecord(id=id, description=description, dates_lookup=dates_lookup, places_lookup=places_lookup))
        record = records[records_lookup[description]]
        record.add(date, place, seconds)    
        total_record.add(date, place, seconds)
    records.append(total_record)
    template = loader.get_template('daily_breakdown_report.html')
    context = {'records': records,
	           'dates': dates,
               'places': places,
               'title': title,
               'prefix': prefix,
               'suffix': suffix,
               'previous': previous,
               'next': next}
    return HttpResponse(template.render(context, request))

def latest_daily_week_breakdown(request):
    """Create the latest summary time use report for a week starting on Saturday"""
    return daily_breakdown(request=request, frequency="my_weekly")

def daily_week_breakdown(request, parent, year, month, day):
    """Create summary time use report for a week starting on Saturday"""
    return daily_breakdown(request=request, frequency="my_weekly", parent=parent,
                   from_year=year, from_month=month, from_day=day)

def calendar_view(request):
    return render(request, 'calendar.html')

def idt_list_view(request):
    context = {'records':  IdealDayTemplate.objects.all()}
    return render(request, 'ideal_day_templates.html', context)

# daily entry log form
class LogForm(forms.Form):
    class Media:
        js = ('timsy.js', 'log.js')
    urgency_list = urgencies()
    importance_list = importances()
    parent_list = parents()
    new_records = 5

def entry_log(request):
    """Create daily log form"""
    if request.method == 'POST':
        form = LogForm(request.POST)

        # if the last activity's duration has been changed, update it
        last_activity = ActivityRecord.objects.all().order_by('-start')[0]
        (hours, minutes) = [int(x) for x in request.POST['duration0'].split(":")]
        if last_activity.duration.hour != hours \
          or last_activity.duration.minute != minutes:
            last_activity.duration = \
                last_activity.duration.replace(hour=hours) 
            last_activity.duration = \
                last_activity.duration.replace(minute=minutes) 
            last_activity.save()
        
        # prepare to process new rows
        activities = Activity.objects.all()
        abbreviations = []
        for activity in activities:
            if activity.abbreviation:
                abbreviations.append(activity.abbreviation)
        parents = Parent.objects.all()
        places = Place.objects.all()
        importances = Importance.objects.all()
        urgencies = Urgency.objects.all()
        counter = 1
        start = last_activity.start + timedelta(hours=hours, minutes=minutes)
        duration = request.POST["duration" + str(counter)]

        # process rows until a row with no duration
        while (len(duration) > 0 and duration != "0:00"):
            (hours, minutes) = [int(x) for x in duration.split(":")]
            duration = time(hour=hours, minute=minutes)
            abbreviation = request.POST["abbreviation" + str(counter)]
            description = request.POST["description" + str(counter)]
            activity = None
            if not abbreviation:
                # no abbreviation entered - search by description
                candidates = activities.filter(description=description)
                if len(candidates) > 0:
                    activity = candidates[0]
            if abbreviation in abbreviations:
                # found the activity by abbreviation
                activity = activities.filter(abbreviation=abbreviation)[0]
            if activity is None:
                # a new activity
                parent_id = request.POST["parent" + str(counter)]
                parent = parents.filter(id=parent_id)[0]
                importance_id = request.POST["importance" + str(counter)]
                importance = importances.filter(id=importance_id)[0]
                urgency_id = request.POST["urgency" + str(counter)]
                urgency = urgencies.filter(id=urgency_id)[0]
                if ("can_start_today" + str(counter)) in request.POST:
                    can_start_today = True
                else:
                    can_start_today = False
                activity = Activity (sort_order=999,
                                     abbreviation=abbreviation,
                                     description=description,
                                     parent=parent,
                                     importance=importance,
                                     urgency=urgency,
                                     can_start_today=can_start_today)
                activity.save()
                if len(abbreviation) > 0:
                    abbreviations.append(abbreviation)
            place_abbr = request.POST["place" + str(counter)].upper()
            place = places.filter(abbreviation=place_abbr)[0]
            record = ActivityRecord(activity=activity,
                                    place=place,
                                    start=start,
                                    duration=duration)
            record.save()
            counter += 1
            if counter > form.new_records:
                break
            duration = request.POST["duration" + str(counter)]
            start += timedelta(hours=hours, minutes=minutes)
        return HttpResponseRedirect('/timsy/data/log/')
    else:
        form = LogForm()
    template = loader.get_template('entry_log.html')
    context = {'form': form}
    return HttpResponse(template.render(context, request))
