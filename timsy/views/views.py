from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

# top level page
def index(request):
	template = loader.get_template('timsy.html')
	return HttpResponse(template.render({}, request))
