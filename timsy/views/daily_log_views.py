from datetime import date
from typing import Dict, Any, Optional

from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest

from timsy.models import ActivityRecord
from timsy.reports.utils import shift_date

# daily time use log view
def daily_log(request: HttpRequest, year: int, month: int, day: int) -> HttpResponse:
    """Create a daily time use log report for a specific date.
    
    Args:
        request: The HTTP request object
        year: Year for the report
        month: Month for the report
        day: Day for the report
        
    Returns:
        Rendered template showing the daily log report
    """
    report_date = date(year=int(year), month=int(month), day=int(day))
    template = loader.get_template('daily_log.html')
    records = ActivityRecord.get_records(report_date, report_date)
    previous = shift_date(report_date, -1)
    next = shift_date(report_date, 1)
    context: Dict[str, Any] = {
        'records': records,
        'previous': previous,
        'next': next
    }
    return HttpResponse(template.render(context, request))

def latest_log(request: HttpRequest) -> HttpResponse:
    """Create a daily time use log report for the most recent day with activity records.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing the latest daily log report
    """
    latest_record = ActivityRecord.get_latest()
    year = latest_record.start.year
    month = latest_record.start.month
    day = latest_record.start.day
    return daily_log(request, year, month, day)
