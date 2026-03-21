from datetime import date, datetime, timedelta
from django.utils.timezone import make_aware

from .models import ActivityRecord


def timestamp_string(seconds):
    if not seconds:
        return "----"
    minutes = int(seconds / 60)
    hours = int(minutes / 60)
    minutes -= 60 * hours
    return "%d:%02d" % (hours, minutes)


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


def get_report_dates(frequency, end_date_supplied, start_date_supplied, end_date, start_date):
    if frequency == "daily":
        if end_date_supplied or not start_date_supplied:
            start_date = end_date
        else:
            end_date = start_date
    elif frequency == "weekly":
        if end_date_supplied or not start_date_supplied:
            start_date = end_date - timedelta(days=end_date.weekday())
            end_date = start_date + timedelta(days=6)
        else:
            end_date = start_date + timedelta(days=6-start_date.weekday())
            start_date = start_date - timedelta(days=start_date.weekday())
    elif frequency == "my_weekly":
        if end_date_supplied or not start_date_supplied:
            start_date = end_date - timedelta(days=(end_date.weekday()+2)%7)
            end_date = start_date + timedelta(days=6)
        else:
            end_date = start_date + timedelta(days=6)
            start_date = start_date - timedelta(days=5-start_date.weekday())
    elif frequency == "monthly":
        if end_date_supplied or not start_date_supplied:
            start_date = end_date.replace(day=1)
            if start_date.month < 12:
                end_date = start_date.replace(month=start_date.month+1) - timedelta(days=1)
            else:
                end_date = start_date.replace(day=31)
        else:
            start_date = start_date.replace(day=1)
            if start_date.month < 12:
                end_date = start_date.replace(month=start_date.month+1) - timedelta(days=1)
            else:
                end_date = start_date.replace(day=31)
    return start_date, end_date


def get_navigation_urls(frequency, parent, start_date, end_date):
    if frequency == "daily":
        previous_date = get_first_record_of(start_date - timedelta(days=1))
        next_date = get_first_record_of(end_date + timedelta(days=1))
        prefix = "/timsy/reports/summary/daily/"
        suffix = "/%d/%d/%d" % (end_date.year, end_date.month, end_date.day)
        previous = "%s%s/%d/%d/%d" % (prefix, parent, previous_date.start.year, previous_date.start.month, previous_date.start.day) if previous_date else None
        next = "%s%s/%d/%d/%d" % (prefix, parent, next_date.start.year, next_date.start.month, next_date.start.day) if next_date else None
    elif frequency == "weekly":
        previous_date = get_first_record_of(start_date - timedelta(days=7))
        next_date = get_first_record_of(start_date + timedelta(days=7))
        prefix = "/timsy/reports/summary/weekly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        previous = "%s%s/%d/%d/%d" % (prefix, parent, previous_date.start.year, previous_date.start.month, previous_date.start.day) if previous_date else None
        next = "%s%s/%d/%d/%d" % (prefix, parent, next_date.start.year, next_date.start.month, next_date.start.day) if next_date else None
    elif frequency == "my_weekly":
        previous_date = get_first_record_of(start_date - timedelta(days=7))
        next_date = get_first_record_of(start_date + timedelta(days=7))
        prefix = "/timsy/reports/summary/my_weekly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        previous = "%s%s/%d/%d/%d" % (prefix, parent, previous_date.start.year, previous_date.start.month, previous_date.start.day) if previous_date else None
        next = "%s%s/%d/%d/%d" % (prefix, parent, next_date.start.year, next_date.start.month, next_date.start.day) if next_date else None
    elif frequency == "monthly":
        if start_date.month == 1:
            previous_start = date(year=start_date.year-1, month=12, day=1)
        else:
            previous_start = start_date.replace(month=start_date.month-1)
        previous_date = get_first_record_in_range(previous_start, start_date)
        next_date = get_first_record_of(end_date + timedelta(days=1))
        prefix = "/timsy/reports/summary/monthly/"
        suffix = "/%d/%d/%d" % (start_date.year, start_date.month, start_date.day)
        previous = "%s%s/%d/%d/%d" % (prefix, parent, previous_date.start.year, previous_date.start.month, previous_date.start.day) if previous_date else None
        next = "%s%s/%d/%d/%d" % (prefix, parent, next_date.start.year, next_date.start.month, next_date.start.day) if next_date else None
    else:  # custom
        delta = 1 + (end_date - start_date).days
        previous_start = get_first_record_in_range(start_date - timedelta(days=delta), start_date)
        previous_end = end_date - timedelta(days=delta)
        next_start = get_first_record_of(start_date + timedelta(days=delta))
        next_end = end_date + timedelta(days=delta)
        prefix = "/timsy/reports/summary/"
        suffix = "/%d/%d/%d/%d/%d/%d" % (end_date.year, end_date.month, end_date.day,
                                          start_date.year, start_date.month, start_date.day)
        previous = "%s%s/%d/%d/%d/%d/%d/%d" % (prefix, parent, previous_end.year, previous_end.month, previous_end.day, previous_start.start.year, previous_start.start.month, previous_start.start.day) if previous_start else None
        next = "%s%s/%d/%d/%d/%d/%d/%d" % (prefix, parent, next_end.year, next_end.month, next_end.day, next_start.start.year, next_start.start.month, next_start.start.day) if next_start else None
    return previous, next, prefix, suffix


def get_report_title(frequency, start_date, end_date):
    if frequency == "daily":
        return "Daily Report For %s" % end_date.strftime("%A, %B %d, %Y")
    elif frequency in ["weekly", "my_weekly"]:
        return "Report For The Week of %s" % start_date.strftime("%B %d, %Y")
    elif frequency == "monthly":
        return "Report For The Month of %s" % start_date.strftime("%B %Y")
    else:
        return "Reporting Period: %s to %s" % (start_date.strftime("%A, %B %d, %Y"),
                                                end_date.strftime("%A, %B %d, %Y"))
