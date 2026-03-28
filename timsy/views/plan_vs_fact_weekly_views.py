from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple

from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest

from timsy.models import ActivityRecord, Place
from timsy.reports.plan_vs_fact_weekly import PlanVsFactWeeklyRecord
from timsy.reports.utils import get_report_title


def get_plan_vs_fact_weekly_navigation_urls(
    parent: str,
    start_date: date
) -> Tuple[str, Optional[str], str, str]:
    """Generate navigation URLs for weekly plan-vs-fact reports.
    
    Args:
        parent: Parent activity filter ('ALL' for all activities)
        start_date: Start date of the current week (Saturday)
        
    Returns:
        Tuple containing:
            - previous_url: URL for the previous week
            - next_url: URL for the next week (None if no next week)
            - prefix: Common URL prefix
            - suffix: Common URL suffix
    """
    previous_date = start_date - timedelta(days=7)
    next_date = start_date + timedelta(days=7)
    
    # Check if next week should be available (don't go beyond today)
    today = date.today()
    if next_date > today:
        next = None
    else:
        next = f"/timsy/reports/plan-vs-fact/weekly/{parent}/{next_date.year}/{next_date.month}/{next_date.day}"
    
    prefix = f"/timsy/reports/plan-vs-fact/weekly/"
    suffix = f"/{start_date.year}/{start_date.month}/{start_date.day}"
    
    previous = f"/timsy/reports/plan-vs-fact/weekly/{parent}/{previous_date.year}/{previous_date.month}/{previous_date.day}"
    
    return previous, next, prefix, suffix


def plan_vs_fact_weekly_report(request: HttpRequest, parent: str, start_date: date) -> HttpResponse:
    """Create a weekly plan-vs-fact report with daily and place breakdown.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        start_date: Start date for the week (Saturday)
        
    Returns:
        Rendered template showing the weekly plan-vs-fact report
    """
    end_date = start_date + timedelta(days=6)

    # Get navigation URLs and report title
    previous, next, prefix, suffix = get_plan_vs_fact_weekly_navigation_urls(parent, start_date)
    title = f"Plan vs Fact: {get_report_title('weekly', start_date)}"

    records = PlanVsFactWeeklyRecord.get_records(parent, start_date, end_date)

    # Filter places to only include those with actual data
    all_places = Place.get_abbreviations()
    places_with_data = set()
    
    # Check each record (except Total) for places that have non-zero plan or fact time
    for record in records:
        if record.description != "Total":  # Skip the total row
            for place in all_places:
                # Check if this place has any plan or fact time across all dates
                has_data = False
                for date_str in record.dates_lookup.keys():
                    key = (date_str, place)
                    if (record.plan_seconds_by_date_place.get(key, 0) > 0 or 
                        record.fact_seconds_by_date_place.get(key, 0) > 0):
                        has_data = True
                        break
                if has_data:
                    places_with_data.add(place)
    
    # Use only places that have data, maintaining original order
    places = [place for place in all_places if place in places_with_data]

    # Generate filtered time data for each record
    for record in records:
        record.times = record.get_times(places)

    days = (end_date - start_date).days + 1
    dates: List[Optional[str]] = [None] * days
    for i in range(days):
        date = start_date + timedelta(days=i)
        dates[i] = date.strftime("%A, %m/%d")

    template = loader.get_template('plan_vs_fact_weekly_report.html')
    context: Dict[str, Any] = {
        'records': records,
        'dates': dates,
        'places': places,
        'title': title,
        'prefix': prefix,
        'suffix': suffix,
        'previous': previous,
        'next': next
    }
    return HttpResponse(template.render(context, request))


def plan_vs_fact_weekly(request: HttpRequest, parent: str, year: int, month: int, day: int) -> HttpResponse:
    """Create a weekly plan-vs-fact report starting on Saturday.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        year: Year for the report start date
        month: Month for the report start date
        day: Day for the report start date
        
    Returns:
        Rendered template showing the weekly plan-vs-fact report
    """
    start_date = date(year=int(year), month=int(month), day=int(day))
    return plan_vs_fact_weekly_report(request, parent, start_date)


def latest_plan_vs_fact_weekly(request: HttpRequest) -> HttpResponse:
    """Create a weekly plan-vs-fact report for the most recent week (Saturday-Friday).
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing the latest weekly plan-vs-fact report
    """
    latest_record_date = ActivityRecord.get_latest().start.date()
    days_to_subtract = (latest_record_date.weekday() - 5) % 7
    saturday = latest_record_date - timedelta(days=days_to_subtract)
    return plan_vs_fact_weekly(request, "ALL", saturday.year, saturday.month, saturday.day) 