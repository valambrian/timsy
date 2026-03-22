import calendar
from datetime import date, datetime, time, timedelta
from typing import Dict, Any, List, Optional, Tuple

from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest

from timsy.models import ActivityRecord, Place
from timsy.reports.summary import SummaryRecord
from timsy.reports.utils import get_report_title, get_navigation_urls

# daily / weekly / monthly / custom period summary report
def summary_report(
    request: HttpRequest,
    frequency: str,
    parent: str,
    start_date: date,
    end_date: date
) -> HttpResponse:
    """Create a summary time use report for a specified period.
    
    Args:
        request: The HTTP request object
        frequency: Report frequency ('daily', 'weekly', 'monthly', or 'custom')
        parent: Parent activity filter ('ALL' for all activities)
        start_date: Start date for the report period
        end_date: End date for the report period
        
    Returns:
        Rendered template showing the summary report
    """

    places = Place.get_abbreviations()
    records = SummaryRecord.get_summary_records(parent, start_date, end_date)

    title = get_report_title(frequency, start_date, end_date)
    (previous, next, prefix, suffix) = get_navigation_urls(frequency, parent, start_date, end_date)

    template = loader.get_template('summary_report.html')
    context: Dict[str, Any] = {
        'records': records,
        'places': places,
        'title': title,
        'prefix': prefix,
        'suffix': suffix,
        'previous': previous,
        'next': next
    }
    return HttpResponse(template.render(context, request))

def daily_summary(request: HttpRequest, parent: str, year: int, month: int, day: int) -> HttpResponse:
    """Create a daily summary time use report.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        year: Year for the report
        month: Month for the report
        day: Day for the report
        
    Returns:
        Rendered template showing the daily summary
    """
    report_date = date(year=int(year), month=int(month), day=int(day))
    return summary_report(request, "daily", parent, report_date, report_date)

def latest_daily_summary(request: HttpRequest) -> HttpResponse:
    """Create a summary time use report for the most recent day with activity records.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing the latest daily summary
    """
    latest_start = ActivityRecord.get_latest().start
    return daily_summary(request, "ALL", latest_start.year, latest_start.month, latest_start.day)

def weekly_summary(request: HttpRequest, parent: str, year: int, month: int, day: int) -> HttpResponse:
    """Create a weekly summary time use report starting from the specified date.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        year: Year for the report start date
        month: Month for the report start date
        day: Day for the report start date
        
    Returns:
        Rendered template showing the weekly summary
    """
    start_date = date(year=int(year), month=int(month), day=int(day))
    end_date = start_date + timedelta(days=6)
    return summary_report(request, "weekly", parent, start_date, end_date)

def latest_weekly_summary(request: HttpRequest) -> HttpResponse:
    """Create a summary time use report for the most recent week (Monday-Sunday).
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing the latest weekly summary
    """
    latest_record_date = ActivityRecord.get_latest().start.date()
    monday = latest_record_date - timedelta(days=latest_record_date.weekday())
    return weekly_summary(request, "ALL", monday.year, monday.month, monday.day)

def latest_my_weekly_summary(request: HttpRequest) -> HttpResponse:
    """Create a summary time use report for the most recent week (Saturday-Friday).
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing the latest weekly summary
    """
    latest_record_date = ActivityRecord.get_latest().start.date()
    days_to_subtract = (latest_record_date.weekday() - 5) % 7
    saturday = latest_record_date - timedelta(days=days_to_subtract)
    return weekly_summary(request, "ALL", saturday.year, saturday.month, saturday.day)

def monthly_summary(request: HttpRequest, parent: str, year: int, month: int, day: int) -> HttpResponse:
    """Create a monthly summary time use report.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        year: Year for the report
        month: Month for the report
        day: Day (used only for consistency with URL pattern)
        
    Returns:
        Rendered template showing the monthly summary
    """
    start_date = date(year=int(year), month=int(month), day=1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year=int(year), month=int(month), day=last_day)
    return summary_report(request, "monthly", parent, start_date, end_date)

def latest_monthly_summary(request: HttpRequest) -> HttpResponse:
    """Create a summary time use report for the most recent month with activity records.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing the latest monthly summary
    """
    date_to_use = ActivityRecord.get_latest().start.date()
    return monthly_summary(request, "ALL", date_to_use.year, date_to_use.month, date_to_use.day)

def custom_summary(
    request: HttpRequest,
    parent: str,
    to_year: int,
    to_month: int,
    to_day: int,
    from_year: int,
    from_month: int,
    from_day: int
) -> HttpResponse:
    """Create a custom period summary time use report.
    
    Args:
        request: The HTTP request object
        parent: Parent activity filter ('ALL' for all activities)
        to_year: End year for the report
        to_month: End month for the report
        to_day: End day for the report
        from_year: Start year for the report
        from_month: Start month for the report
        from_day: Start day for the report
        
    Returns:
        Rendered template showing the custom period summary
    """
    start_date = date(year=int(from_year), month=int(from_month), day=int(from_day))
    end_date = date(year=int(to_year), month=int(to_month), day=int(to_day))
    return summary_report(request, "custom", parent, start_date, end_date)
