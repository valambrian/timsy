from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple, Any, Dict
import json

from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest
from django.http import Http404
from django.forms import formset_factory

from timsy.models import Activity, IdealDayTemplate, IdealDayTemplateRecord, Importance, Parent, Urgency, Place
from timsy.reports.summary import SummaryRecord
from timsy.reports.utils import parse_duration_string

def idt_list_view(request: HttpRequest) -> HttpResponse:
    """Display a list of all ideal day templates.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing all ideal day templates
    """
    context = {'records':  IdealDayTemplate.objects.all()}
    return render(request, 'ideal_day_templates.html', context)


def idt_view(request: HttpRequest, id: int) -> HttpResponse:
    """Display contents of a specific ideal day template.

    Args:
        request: The HTTP request object
        id: Template ID

    Returns:
        Rendered template showing the ideal day template's records
    """
    idt = IdealDayTemplate.objects.get(pk=id)
    records = idt.get_records()

    template = loader.get_template('ideal_day_template_view.html')
    context: Dict[str, Any] = {
        'records': records,
        'name': idt.name
    }
    return HttpResponse(template.render(context, request))

def idt_summary(request: HttpRequest, id: int) -> HttpResponse:
    """Display contents of a specific ideal day template.

    Args:
        request: The HTTP request object
        id: Template ID

    Returns:
        Rendered template showing the ideal day template's records
    """
    idt = IdealDayTemplate.objects.get(pk=id)
    records = SummaryRecord.summarize_idt(id)
    places = Place.get_abbreviations()

    template = loader.get_template('ideal_day_template_summary.html')
    context: Dict[str, Any] = {
        'template': idt,
        'places': places,
        'records': records
    }
    return HttpResponse(template.render(context, request))

class IdealDayTemplateRecordForm(forms.Form):
    record_id = forms.IntegerField(required=False)
    start = forms.TimeField(required=False)
    abbreviation = forms.CharField(max_length=10, required=False)
    description = forms.CharField(max_length=200, required=False)
    parent = forms.ModelChoiceField(queryset=Parent.objects.all(), required=False)
    importance = forms.ModelChoiceField(queryset=Importance.objects.all(), required=False)
    urgency = forms.ModelChoiceField(queryset=Urgency.objects.all(), required=False)
    duration = forms.CharField(max_length=10, required=False)
    place = forms.ModelChoiceField(queryset=Place.objects.all(), to_field_name='abbreviation', required=False)

    def clean(self):
        cleaned_data = super().clean()
        # Only consider non-empty fields when checking if a form is partially filled
        non_empty_fields = {k: v for k, v in cleaned_data.items() if v not in (None, '', [])}
        
        # If any non-empty field exists (except start), all required fields must be filled
        if any(k != 'start' for k in non_empty_fields.keys()):
            required_fields = ['abbreviation', 'description', 'parent', 'importance', 'urgency', 'duration', 'place']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required when other fields are filled.')
        return cleaned_data

def idt_edit(request: HttpRequest, id: int) -> HttpResponse:
    """Allows to edit contents of a specific ideal day template.

    Args:
        request: The HTTP request object
        id: Template ID

    Returns:
        Rendered template showing the ideal day template's records
    """
    idt = IdealDayTemplate.objects.get(pk=id)
    records = idt.get_records()

    # Create a formset factory
    IdealDayTemplateRecordFormSet = formset_factory(IdealDayTemplateRecordForm, extra=5)

    if request.method == 'POST':
        print("POST data:", request.POST)
        formset = IdealDayTemplateRecordFormSet(request.POST)
        print("Management form data:", formset.management_form.data)
        print("Total forms:", formset.management_form.cleaned_data.get('TOTAL_FORMS'))
        print("Initial forms:", formset.management_form.cleaned_data.get('INITIAL_FORMS'))
        if not formset.is_valid():
            print("Formset errors:", formset.errors)
            print("Management form errors:", formset.management_form.errors)
            print("POST data:", request.POST)
        if formset.is_valid():
            # Start with a datetime at midnight
            current_datetime = datetime.combine(date.today(), time(hour=0, minute=0))

            # Delete all existing records for this template
            IdealDayTemplateRecord.objects.filter(template=idt).delete()

            for form in formset:
                # Get duration value
                duration_str = form.cleaned_data.get('duration', '')
                
                # Stop processing if duration is empty or zero
                if not duration_str or duration_str in ['0:00', '00:00']:
                    break

                # Get form values
                abbreviation = form.cleaned_data['abbreviation']
                description = form.cleaned_data['description']
                parent = form.cleaned_data['parent']
                importance = form.cleaned_data['importance']
                urgency = form.cleaned_data['urgency']
                hours, minutes = parse_duration_string(duration_str)
                duration = timedelta(hours=hours, minutes=minutes)
                place = form.cleaned_data['place']

                # Create or get activity
                activity = Activity.find_or_create(abbreviation, description, parent, importance, urgency)

                # Create new record
                record = IdealDayTemplateRecord(
                    template=idt,
                    start=current_datetime.time(),
                    duration=duration,
                    activity=activity,
                    place=place
                )
                record.save()

                # Add duration to current datetime
                current_datetime = current_datetime + duration

            # Redirect back to edit page
            return HttpResponseRedirect(f'/timsy/data/ideal_day_templates/edit/{id}/')
    else:
        # For GET request, prepare initial data
        initial_data = []
        for record in records:
            initial_data.append({
                'record_id': record.id,
                'start': record.start.strftime('%H:%M'),
                'abbreviation': record.activity.abbreviation,
                'description': record.activity.description,
                'parent': record.activity.parent,
                'importance': record.activity.importance,
                'urgency': record.activity.urgency,
                'duration': f"{record.duration.seconds // 3600:02d}:{(record.duration.seconds % 3600) // 60:02d}",
                'place': record.place.abbreviation
            })
        formset = IdealDayTemplateRecordFormSet(initial=initial_data)

    # Prepare form data for template
    form = {
        'parent_list': json.dumps([{'value': str(p.id), 'text': str(p)} for p in Parent.objects.all()]),
        'importance_list': json.dumps([{'value': str(i.id), 'text': str(i)} for i in Importance.objects.all()]),
        'urgency_list': json.dumps([{'value': str(u.id), 'text': str(u)} for u in Urgency.objects.all()]),
        'place_list': Place.get_abbreviations()
    }

    template = loader.get_template('ideal_day_template_edit.html')
    context: Dict[str, Any] = {
        'records': records,
        'template': idt,
        'form': form,
        'formset': formset
    }
    return HttpResponse(template.render(context, request))
