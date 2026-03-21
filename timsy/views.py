# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime, time, timedelta
from django.utils.timezone import make_aware
import json

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django import forms
from django.db import connection, transaction

from .models import Activity, ActivityRecord, Importance, Parent, Place, Urgency, IdealDayTemplate
from .utils import (
    timestamp_string, get_first_record_of, get_first_record_in_range,
    get_report_dates, get_navigation_urls, get_report_title
)
from .summary import SummaryRecord, DailyBreakdownSummaryRecord
from .queries import get_summary_query, get_daily_breakdown_query

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

def get_last_activity_record(request):
    if request.method == 'GET':
        record = ActivityRecord.objects.all().order_by('-start')[0]
        return HttpResponse(json.dumps(record.as_hash()))

def get_activity(request, abbreviation):
    if request.method == 'GET':
        record = Activity.objects.filter(abbreviation=abbreviation).first()
        response_dict = record.as_hash() if record else {}
        return HttpResponse(json.dumps(response_dict))

# daily / weekly / monthly / custom period summary report
def summary(request, parent="ALL", frequency="custom",
            to_year=None, to_month=None, to_day=None,
            from_year=None, from_month=None, from_day=None):
    """Create summary time use report"""
    # Get end date
    if to_year is None or to_month is None or to_day is None:
        end_date_supplied = False
        end_date = ActivityRecord.objects.all().order_by('-start')[0].start
    else:
        end_date_supplied = True
        end_date = date(year=int(to_year), month=int(to_month), day=int(to_day))

    # Get start date
    if from_year is None or from_month is None or from_day is None:
        start_date_supplied = False
        start_date = ActivityRecord.objects.all().order_by('start')[0].start
    else:
        start_date_supplied = True
        start_date = date(year=int(from_year), month=int(from_month), day=int(from_day))

    start_date, end_date = get_report_dates(
        frequency, end_date_supplied, start_date_supplied, end_date, start_date
    )
    previous, next, prefix, suffix = get_navigation_urls(
        frequency, parent, start_date, end_date
    )
    title = get_report_title(frequency, start_date, end_date)

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

    query = get_summary_query(parent_pattern, start_date_pattern, end_date_pattern, parent)
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
def daily_breakdown(request, parent="ALL", frequency="custom",
            to_year=None, to_month=None, to_day=None,
            from_year=None, from_month=None, from_day=None):
    """Create time use report with daily breakdown"""
    # Get end date
    if to_year is None or to_month is None or to_day is None:
        end_date_supplied = False
        end_date = ActivityRecord.objects.all().order_by('-start')[0].start
    else:
        end_date_supplied = True
        end_date = date(year=int(to_year), month=int(to_month), day=int(to_day))

    # Get start date
    if from_year is None or from_month is None or from_day is None:
        start_date_supplied = False
        start_date = ActivityRecord.objects.all().order_by('start')[0].start
    else:
        start_date_supplied = True
        start_date = date(year=int(from_year), month=int(from_month), day=int(from_day))

    start_date, end_date = get_report_dates(
        frequency, end_date_supplied, start_date_supplied, end_date, start_date
    )
    previous, next, prefix, suffix = get_navigation_urls(
        frequency, parent, start_date, end_date
    )
    title = get_report_title(frequency, start_date, end_date)

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
        date = start_date + timedelta(days=i)
        dates_lookup[date.strftime("%Y-%m-%d")] = i
        dates[i] = date.strftime("%A, %m/%d")

    places = [place.abbreviation for place in Place.objects.all().order_by('sort_order')]
    places_lookup = {}
    for i in range(len(places)):
        places_lookup[places[i]] = i

    query = get_daily_breakdown_query(parent_pattern, start_date_pattern, end_date_pattern, parent)
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

def idt_list_view(request):
    context = {'records': IdealDayTemplate.objects.all()}
    return render(request, 'ideal_day_templates.html', context)

# daily entry log form
class LogForm(forms.Form):
    class Media:
        js = ('timsy.js', 'log.js')
    urgency_list = Urgency.get_choices()
    importance_list = Importance.get_choices()
    parent_list = Parent.get_active_choices()
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
        while len(duration) > 0 and duration != "0:00":
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
                activity = Activity(sort_order=999,
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
