from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple, List, Union
from django.db.models import QuerySet

from ..models import Activity, ActivityRecord

def seconds_to_string(seconds: Optional[int]) -> str:
    """
    Convert seconds into a formatted time string (HH:MM).
    
    Args:
        seconds: Number of seconds to convert
        
    Returns:
        Formatted time string in HH:MM format, or "---" if seconds is None
    """
    if not seconds:
        return "---"
    
    # Handle negative values
    is_negative = seconds < 0
    abs_seconds = abs(seconds)
    
    minutes = int(abs_seconds / 60)
    hours = int(minutes / 60)
    minutes -= 60 * hours
    
    # Format with proper sign
    if is_negative:
        return "-%02d:%02d" % (hours, minutes)
    else:
        return "%02d:%02d" % (hours, minutes)

def shift_date(report_date: date, days: int) -> Optional[date]:
    """Shift a date by a specified number of days, ensuring it doesn't exceed today's date.
    
    Args:
        report_date: The date to shift
        days: Number of days to shift (positive or negative)
        
    Returns:
        The shifted date, or None if the result would be after today
    """
    new_date = report_date + timedelta(days=days)
    if new_date > date.today():
        new_date = None
    return new_date

def get_navigation_urls(
    frequency: str,
    parent: str,
    start_date: date,
    end_date: date,
    link_token: Optional[str] = None
) -> Tuple[str, Optional[str], str, str]:
    """Generate navigation URLs for report views.
    
    Creates URLs for previous/next periods and common URL components based on the report frequency.
    
    Args:
        frequency: Report frequency ('daily', 'weekly', 'monthly', or 'custom')
        parent: Parent activity filter ('ALL' for all activities)
        start_date: Start date of the current report period
        end_date: End date of the current report period
        link_token: Custom URL token for navigation. Defaults to frequency.
        
    Returns:
        Tuple containing:
            - previous_url: URL for the previous period
            - next_url: URL for the next period (None if no next period)
            - prefix: Common URL prefix
            - suffix: Common URL suffix
    """
    if frequency == "custom":
        return get_custom_navigation_urls(parent, start_date, end_date)

    if frequency == "daily":
        previous_date = shift_date(start_date, -1)
        next_date = shift_date(end_date, 1)
    elif frequency == "weekly":
        previous_date = shift_date(start_date, -7)
        next_date = shift_date(end_date, 1)
    elif frequency == "monthly":
        if start_date.month == 1:
            previous_date = date(start_date.year - 1, 12, 1)
        else:
            previous_date = date(start_date.year, start_date.month - 1, 1)
        if end_date.month == 12:
            next_date = date(end_date.year + 1, 1, 1)
        else:
            next_date = date(end_date.year, end_date.month + 1, 1)
        if next_date > date.today():
            next_date = None

    if link_token is None:
        link_token = frequency

    prefix = f"/timsy/reports/summary/{link_token}/"
    suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
    previous = "/timsy/reports/summary/%s/%s/%d/%d/%d" % (
        link_token, parent, previous_date.year, previous_date.month, previous_date.day
    )

    if next_date is None:
        next = None
    else:
        next = "/timsy/reports/summary/%s/%s/%d/%d/%d" % (
            link_token, parent, next_date.year, next_date.month, next_date.day
        )

    return previous, next, prefix, suffix

def get_custom_navigation_urls(
    parent: str,
    start_date: date,
    end_date: date
) -> Tuple[str, str, str, str]:
    """Generate navigation URLs for custom period reports.
    
    Creates URLs for previous/next periods and common URL components for custom date ranges.
    
    Args:
        parent: Parent activity filter ('ALL' for all activities)
        start_date: Start date of the current report period
        end_date: End date of the current report period
        
    Returns:
        Tuple containing:
            - previous_url: URL for the previous period
            - next_url: URL for the next period
            - prefix: Common URL prefix
            - suffix: Common URL suffix
    """
    previous_start_date = shift_date(start_date, (start_date - end_date).days - 1)
    previous_end_date = shift_date(start_date, - 1)
    next_start_date = shift_date(end_date, 1)
    next_end_date = shift_date(end_date, (end_date - start_date).days + 1)

    if next_start_date is None:
        next_start_date = ActivityRecord.get_latest().date()
    if next_end_date is None:
        next_end_date = ActivityRecord.get_latest().date()

    prefix = "/timsy/reports/summary/"
    suffix = "/%d/%d/%d/%d/%d" % (
        start_date.year, start_date.month, start_date.day,
        end_date.year, end_date.month, end_date.day)
    previous = "/timsy/reports/summary/%s/%d/%d/%d/%d/%d/%d" % (
        parent,
        previous_start_date.year, previous_start_date.month, previous_start_date.day,
        previous_end_date.year, previous_end_date.month, previous_end_date.day
    )
    next = "/timsy/reports/summary/%s/%d/%d/%d/%d/%d/%d" % (
        parent,
        next_start_date.year, next_start_date.month, next_start_date.day,
        next_end_date.year, next_end_date.month, next_end_date.day
    )

    return previous, next, prefix, suffix

def get_report_title(
    frequency: str,
    start_date: date,
    end_date: Optional[date] = None
) -> str:
    """Generate a formatted title for a report based on its frequency and date range.
    
    Args:
        frequency: Report frequency ('daily', 'weekly', 'monthly', or 'custom')
        start_date: Start date of the report period
        end_date: End date of the report period. Required for custom reports.
        
    Returns:
        Formatted report title
    """
    if frequency == "daily":
        title = "Report For %s" % (start_date.strftime("%A, %B %d, %Y"), )
    elif frequency == "weekly":
        title = "Report For The Week of %s" % (start_date.strftime("%A, %B %d, %Y"))
    elif frequency == "monthly":
        title = "Report For The Month of %s" % (start_date.strftime("%B %Y"), )
    else:
        title = "Report For The Period From %s To %s" % (
            start_date.strftime("%A, %B %d, %Y"),
            end_date.strftime("%A, %B %d, %Y")
        )
    return title

def parse_duration_string(duration_str: str) -> Tuple[int, int]:
    """Parse a duration string in HH:MM format into hours and minutes.
    
    Args:
        duration_str: Duration string in HH:MM format
        
    Returns:
        Tuple of (hours, minutes) as integers. Returns (0, 0) if parsing fails.
    """
    try:
        return tuple(int(x) for x in duration_str.split(":"))
    except (ValueError, AttributeError):
        return (0, 0) 