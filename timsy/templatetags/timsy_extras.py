'''
Created on Jul 27, 2009

@author: valambrian
'''

from datetime import time, timedelta
from typing import List, Union, Any

from django import template

register = template.Library()

def times(count: Union[int, float, str]) -> List[int]:
    return range(int(count))

def time_string(time_obj: time) -> str:
    return time_obj.strftime("%H:%M")

def timedelta_string(duration: timedelta) -> str:
    seconds = int(duration.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

@register.filter
def duration_format(duration):
    """Format a timedelta duration as HH:MM."""
    if not isinstance(duration, timedelta):
        return str(duration)
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    return f"{hours:02d}:{minutes:02d}"

register.filter('times', times)
register.filter('time_string', time_string)
register.filter('timedelta_string', timedelta_string)
