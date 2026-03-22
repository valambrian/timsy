from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest

from timsy.models import ActivityRecord, Place
from timsy.reports.summary import DailyBreakdownSummaryRecord
from timsy.reports.utils import (get_navigation_urls, get_report_title)

# weekly-daily report
def daily_breakdown_report(request: HttpRequest, parent: str, start_date: date) -> HttpResponse:
    """Create a time use report with daily breakdown for a week.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        start_date: Start date for the week (Saturday)
        
    Returns:
        Rendered template showing the daily breakdown report
    """

    end_date = start_date + timedelta(days=6)

    # Get navigation URLs and report title
    previous, next, prefix, suffix = get_navigation_urls(
        "weekly", parent, start_date, end_date, "daily_week_breakdown"
    )
    title = get_report_title("weekly", start_date)

    places = Place.get_abbreviations()
    days = (end_date - start_date).days + 1
    dates: List[Optional[str]] = [None] * days
    for i in range(days):
        date = start_date + timedelta(days=i)
        dates[i] = date.strftime("%A, %m/%d")

    records = DailyBreakdownSummaryRecord.get_records(parent, start_date, end_date)

    template = loader.get_template('daily_breakdown_report.html')
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

def daily_week_breakdown(request: HttpRequest, parent: str, year: int, month: int, day: int) -> HttpResponse:
    """Create a time use report with daily breakdown for a week starting on Saturday.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        year: Year for the report start date
        month: Month for the report start date
        day: Day for the report start date
        
    Returns:
        Rendered template showing the daily breakdown report
    """
    start_date = date(year=int(year), month=int(month), day=int(day))
    return daily_breakdown_report(request, parent, start_date)

def latest_daily_week_breakdown(request: HttpRequest) -> HttpResponse:
    """Create a time use report with daily breakdown for the most recent week (Saturday-Friday).
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing the latest daily breakdown report
    """
    latest_record_date = ActivityRecord.get_latest().start.date()
    days_to_subtract = (latest_record_date.weekday() - 5) % 7
    saturday = latest_record_date - timedelta(days=days_to_subtract)
    return daily_week_breakdown(request, "ALL", saturday.year, saturday.month, saturday.day)
