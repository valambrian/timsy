from django.http import HttpResponse
import json
from timsy.models import Activity, ActivityRecord

def get_last_activity_record(request):
    """
    Get the most recent activity record.

    Args:
        request: The HTTP request object

    Returns:
        HttpResponse: JSON response containing the last activity record's data
    """
    if request.method == 'GET':
        latest_record = ActivityRecord.get_latest()
        return HttpResponse(json.dumps(latest_record.as_hash()))


def get_activity_by_abbreviation(request, abbreviation):
    """
    Get an activity by its abbreviation.

    Args:
        request: The HTTP request object
        abbreviation (str): The activity's abbreviation

    Returns:
        HttpResponse: JSON response containing the activity's data, or empty dict if not found
    """
    if request.method == 'GET':
        record = Activity.objects.filter(abbreviation=abbreviation).first()
        response_dict = record.as_hash() if record else {}
        return HttpResponse(json.dumps(response_dict))
