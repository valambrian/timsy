'''
Created on Jul 27, 2009

@author: valambrian
'''

from django import template

register = template.Library()

def times(count):
    return range(int(count))

def time_string(time):
    return time.strftime("%H:%M")

register.filter('times', times)
register.filter('time_string', time_string)
