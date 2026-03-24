from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest

from timsy.models import ActivityRecord, Place, DailyPlan, Activity
from timsy.reports.utils import get_report_title, seconds_to_string, shift_date
from timsy.reports.plan_vs_fact import PlanVsFactRecord


def get_plan_vs_fact_navigation_urls(
    parent: str,
    report_date: date
) -> Tuple[str, Optional[str], str, str]:
    """Generate navigation URLs for plan-vs-fact reports.
    
    Args:
        parent: Parent activity filter ('ALL' for all activities)
        report_date: Date of the current report
        
    Returns:
        Tuple containing:
            - previous_url: URL for the previous day
            - next_url: URL for the next day (None if no next day)
            - prefix: Common URL prefix
            - suffix: Common URL suffix
    """
    previous_date = shift_date(report_date, -1)
    next_date = shift_date(report_date, 1)
    
    prefix = f"/timsy/reports/plan-vs-fact/daily/"
    suffix = f"/{report_date.year}/{report_date.month}/{report_date.day}"
    
    previous = f"/timsy/reports/plan-vs-fact/daily/{parent}/{previous_date.year}/{previous_date.month}/{previous_date.day}"
    
    if next_date is None:
        next = None
    else:
        next = f"/timsy/reports/plan-vs-fact/daily/{parent}/{next_date.year}/{next_date.month}/{next_date.day}"
    
    return previous, next, prefix, suffix


def plan_vs_fact_report(
    request: HttpRequest,
    parent: str,
    report_date: date
) -> HttpResponse:
    """Create a plan-vs-fact report for a specific date and parent category."""
    
    places = Place.get_abbreviations() if hasattr(Place, 'get_abbreviations') else list(Place.objects.values_list('abbreviation', flat=True))
    records = PlanVsFactRecord.get_plan_vs_fact_records(parent, report_date)
    
    # Pre-calculate times for each record for template rendering
    for record in records:
        record.times = record.get_times()
    
    title = f"Plan vs Fact Report For {report_date.strftime('%A, %B %d, %Y')}"
    (previous, next, prefix, suffix) = get_plan_vs_fact_navigation_urls(parent, report_date)
    
    template = loader.get_template('plan_vs_fact_report.html')
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


def plan_vs_fact_daily(request: HttpRequest, parent: str, year: int, month: int, day: int) -> HttpResponse:
    """Create a daily plan-vs-fact report."""
    report_date = date(year=int(year), month=int(month), day=int(day))
    return plan_vs_fact_report(request, parent, report_date)


def latest_plan_vs_fact_daily(request: HttpRequest) -> HttpResponse:
    """Create a plan-vs-fact report for the most recent day with activity records."""
    latest_start = ActivityRecord.get_latest().start
    return plan_vs_fact_daily(request, "ALL", latest_start.year, latest_start.month, latest_start.day) 