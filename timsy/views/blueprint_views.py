from datetime import date, datetime, time, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json

from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django.http import HttpRequest
from django.http import Http404
from django.forms import formset_factory

from timsy.models import Activity, Blueprint, BlueprintEntry, Importance, Parent, Place, Urgency
from timsy.reports.utils import parse_duration_string

class BlueprintEntryForm(forms.Form):
    """Form for blueprint entries.
    
    Attributes:
        entry_id: ID of existing entry (for editing)
        start: Start time
        abbreviation: Activity abbreviation
        description: Activity description
        parent: Parent activity
        importance: Importance level
        urgency: Urgency level
        duration: Duration in HH:MM format
        place: Place abbreviation
    """
    entry_id = forms.IntegerField(required=False)
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

def blueprint_list_view(request: HttpRequest) -> HttpResponse:
    """Display a list of all blueprints.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Rendered template showing all blueprints
    """
    context = {'records': Blueprint.objects.all()}
    return render(request, 'blueprint_list.html', context)

def blueprint_detail_view(request: HttpRequest, id: int) -> HttpResponse:
    """Display contents of a specific blueprint.
    
    Args:
        request: The HTTP request object
        id: Blueprint ID
        
    Returns:
        Rendered template showing the blueprint's entries
    """
    blueprint = Blueprint.objects.get(pk=id)
    entries = blueprint.get_entries()

    template = loader.get_template('blueprint_detail.html')
    context: Dict[str, Any] = {
        'entries': entries,
        'blueprint': blueprint
    }
    return HttpResponse(template.render(context, request))

def blueprint_edit_view(request: HttpRequest, id: int) -> HttpResponse:
    """Edit an existing blueprint's entries.
    
    Args:
        request: The HTTP request object
        id: Blueprint ID
        
    Returns:
        Rendered template for editing the blueprint's entries
    """
    blueprint = Blueprint.objects.get(pk=id)
    entries = blueprint.get_entries()

    if request.method == 'POST':
        # Delete all existing entries for this blueprint
        BlueprintEntry.objects.filter(blueprint=blueprint).delete()

        # Check if there's a start time for the first entry, otherwise default to midnight
        first_start_str = request.POST.get('start0', '')
        if first_start_str:
            # Parse the submitted start time
            first_start_time = datetime.strptime(first_start_str, '%H:%M').time()
            current_datetime = datetime.combine(date.today(), first_start_time)
        else:
            # Default to midnight if no start time provided
            current_datetime = datetime.combine(date.today(), time(hour=0, minute=0))

        # Process each row until we find an empty duration
        i = 0
        while True:
            duration_str = request.POST.get(f'duration{i}', '')
            if not duration_str or duration_str in ['0:00', '00:00']:
                break

            # Get form values
            abbreviation = request.POST[f'abbreviation{i}']
            description = request.POST[f'description{i}']
            parent = Parent.objects.get(id=request.POST[f'parent{i}'])
            importance = Importance.objects.get(id=request.POST[f'importance{i}'])
            urgency = Urgency.objects.get(id=request.POST[f'urgency{i}'])
            
            # Parse duration with error handling
            try:
                hours, minutes = parse_duration_string(duration_str)
            except Exception as e:
                # Print detailed error information
                print(f"ERROR: Failed to parse duration string for blueprint entry {i}")
                print(f"  Blueprint ID: {blueprint.id}")
                print(f"  Blueprint Name: {blueprint.name}")
                print(f"  Entry Index: {i}")
                print(f"  Duration String: '{duration_str}'")
                print(f"  Abbreviation: '{abbreviation}'")
                print(f"  Description: '{description}'")
                print(f"  Error: {str(e)}")
                
                # Try to fix common issues with duration string
                fixed_duration_str = duration_str.strip()
                
                # If duration starts with ":", add "0" at the beginning
                if fixed_duration_str.startswith(':'):
                    fixed_duration_str = '0' + fixed_duration_str
                    print(f"  Fixed duration string: '{fixed_duration_str}'")
                
                # If duration is just minutes (e.g., ":30"), make it "0:30"
                if fixed_duration_str.count(':') == 1 and fixed_duration_str.split(':')[0] == '':
                    fixed_duration_str = '0' + fixed_duration_str
                    print(f"  Fixed duration string: '{fixed_duration_str}'")
                
                # Try parsing again with the fixed string
                try:
                    hours, minutes = parse_duration_string(fixed_duration_str)
                    print(f"  Successfully parsed fixed duration: {hours}h {minutes}m")
                except Exception as e2:
                    print(f"  Failed to parse even after fixing: {str(e2)}")
                    print(f"  Skipping this entry and continuing...")
                    i += 1
                    continue
            
            duration = time(hour=hours, minute=minutes)
            place = Place.objects.get(abbreviation=request.POST[f'place{i}'].upper())

            # Create or get activity
            activity = Activity.find_or_create(abbreviation, description, parent, importance, urgency)

            # Create new entry
            entry = BlueprintEntry(
                blueprint=blueprint,
                start=current_datetime.time(),
                duration=duration,
                activity=activity,
                place=place
            )
            entry.save()

            # Add duration to current datetime
            duration_delta = timedelta(hours=duration.hour, minutes=duration.minute)
            current_datetime = current_datetime + duration_delta
            i += 1

        # Redirect back to edit page
        return HttpResponseRedirect(f'/timsy/blueprints/{blueprint.id}/edit/')

    # Prepare form data for template
    form = {
        'parent_list': Parent.get_active_choices(),
        'importance_list': Importance.get_choices(),
        'urgency_list': Urgency.get_choices(),
        'place_list': Place.get_abbreviations()
    }

    # Get available blueprints for blueprint-to-blueprint feature
    # Exclude current blueprint and include only active blueprints
    available_blueprints = Blueprint.objects.filter(
        is_active=True
    ).exclude(id=id)

    # Prepare available blueprints data for JavaScript consumption
    blueprints_data = []
    for blueprint_item in available_blueprints:
        blueprint_entries = blueprint_item.get_entries()
        start_time = blueprint_entries[0].start if blueprint_entries else None
        blueprints_data.append({
            'id': blueprint_item.id,
            'name': blueprint_item.name,
            'start_time': start_time.strftime('%H:%M') if start_time else None,
            'active': blueprint_item.is_active,
            'entry_count': len(blueprint_entries)
        })

    template = loader.get_template('blueprint_edit.html')
    context: Dict[str, Any] = {
        'entries': entries,
        'blueprint': blueprint,
        'form': form,
        'available_blueprints': available_blueprints,
        'blueprints_data': json.dumps(blueprints_data)
    }
    return HttpResponse(template.render(context, request)) 