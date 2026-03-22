from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple, Any, Dict

from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest

from timsy.models import Activity, ActivityRecord, Importance, Parent, Place, Urgency
from timsy.reports.utils import parse_duration_string

# daily entry log form
class LogForm(forms.Form):
    """Form for creating daily activity log entries.
    
    Attributes:
        urgency_list: List of urgency choices
        importance_list: List of importance choices
        parent_list: List of active parent choices
        place_list: List of valid place abbreviations
        new_records: Number of new record slots to display (default: 5)
    """
    urgency_list: List[Tuple[str, str]] = Urgency.get_choices()
    importance_list: List[Tuple[str, str]] = Importance.get_choices()
    parent_list: List[Tuple[str, str]] = Parent.get_active_choices()
    place_list: List[str] = Place.get_abbreviations()
    new_records: int = 5


def entry_log(request: HttpRequest) -> HttpResponse:
    """Create and process daily activity log entries.
    
    Handles both GET and POST requests:
    - GET: Displays the log entry form
    - POST: Processes submitted log entries, creating new activity records
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template for GET requests
        Redirects to log view after successful POST
    """
    if request.method == 'POST':
        form = LogForm(request.POST)

        hours, minutes = parse_duration_string(request.POST['duration0'])
        last_activity = ActivityRecord.get_latest()
        last_activity.update_duration(hours, minutes)
        start = last_activity.start + timedelta(hours=hours, minutes=minutes)

        parents = Parent.objects.all()
        places = Place.objects.all()
        importances = Importance.objects.all()
        urgencies = Urgency.objects.all()

        for i in range(1, form.new_records + 1):
            # process rows until a row with no duration
            hours, minutes = parse_duration_string(request.POST[f"duration{i}"])
            if hours == 0 and minutes == 0:
                break

            abbreviation = request.POST[f"abbreviation{i}"]
            description = request.POST[f"description{i}"]
            parent = parents.filter(id=request.POST[f"parent{i}"]).first()
            importance = importances.filter(id=request.POST[f"importance{i}"]).first()
            urgency = urgencies.filter(id=request.POST[f"urgency{i}"]).first()

            activity = Activity.find_or_create(abbreviation, description, parent, importance, urgency)

            duration = time(hour=hours, minute=minutes)
            place = places.filter(abbreviation=request.POST[f"place{i}"].upper()).first()
            record = ActivityRecord(activity=activity,
                                    place=place,
                                    start=start,
                                    duration=duration)
            record.save()
            start += timedelta(hours=hours, minutes=minutes)
        return HttpResponseRedirect('/timsy/data/entry_log/')
    else:
        form = LogForm()
    template = loader.get_template('entry_log.html')
    context: Dict[str, Any] = {'form': form}
    return HttpResponse(template.render(context, request))

