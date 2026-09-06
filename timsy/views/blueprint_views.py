from datetime import date, datetime, time, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json

from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.http import HttpRequest
from django.http import Http404
from django.forms import formset_factory
from django.urls import reverse
from urllib.parse import urlencode

from timsy.models import Activity, Blueprint, BlueprintEntry, Importance, Parent, Place, Urgency
from timsy.reports.utils import local_today, parse_duration_string


def _schedule_from_post(post) -> Tuple[int, int, Optional[date]]:
    """Parse weekday mask, interval weeks, and anchor date from a POST dict.

    Args:
        post: Request POST data

    Returns:
        tuple: (weekday_mask, interval_weeks, anchor_date)
    """
    mask = Blueprint.mask_from_weekdays(post.getlist('weekdays'))
    try:
        interval_weeks = int(post.get('interval_weeks') or 1)
    except (TypeError, ValueError):
        interval_weeks = 1
    if interval_weeks < 1:
        interval_weeks = 1
    anchor_date = None
    raw_anchor = (post.get('anchor_date') or '').strip()
    if raw_anchor:
        try:
            anchor_date = date.fromisoformat(raw_anchor)
        except ValueError:
            pass
    return mask, interval_weeks, anchor_date


def _schedule_form_context(
    weekday_mask: int = 0,
    interval_weeks: int = 1,
    anchor_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Template context for blueprint schedule fields."""
    return {
        'weekday_choices': Blueprint.WEEKDAY_CHOICES,
        'selected_weekdays': [
            day for day in range(7) if weekday_mask & (1 << day)
        ],
        'interval_weeks': interval_weeks,
        'anchor_date_value': anchor_date.isoformat() if anchor_date else '',
    }

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
    """Display a list of blueprints.

    Shows active blueprints by default, or all blueprints when show=all.
    """
    show_all = request.GET.get('show') == 'all'
    blueprints = Blueprint.objects.all()
    if not show_all:
        blueprints = blueprints.filter(is_active=True)
    return render(request, 'blueprint_list.html', {
        'records': blueprints,
        'show_all': show_all,
    })


def blueprint_toggle_active(request: HttpRequest, id: int) -> HttpResponse:
    """Toggle a blueprint's is_active flag and return to the list."""
    blueprint = get_object_or_404(Blueprint, pk=id)
    blueprint.is_active = not blueprint.is_active
    blueprint.save(update_fields=['is_active'])

    url = reverse('blueprint_list')
    if request.GET.get('show') == 'all':
        url += '?' + urlencode({'show': 'all'})
    return redirect(url)


def blueprint_create_view(request: HttpRequest) -> HttpResponse:
    """Create a new empty blueprint and open it for editing.

    GET: Shows a name field and schedule fields.
    POST: Creates an active blueprint with no entries and redirects to edit.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        weekday_mask, interval_weeks, anchor_date = _schedule_from_post(request.POST)
        context = {
            'name': name,
            'title': 'Create New Blueprint',
            'submit_label': 'Create Blueprint',
            **_schedule_form_context(weekday_mask, interval_weeks, anchor_date),
        }
        if not name:
            context['error'] = 'Name is required.'
            return render(request, 'blueprint_create.html', context)
        blueprint = Blueprint.objects.create(
            name=name,
            is_active=True,
            weekday_mask=weekday_mask,
            interval_weeks=interval_weeks,
            anchor_date=anchor_date,
        )
        return redirect('blueprint_edit', id=blueprint.id)
    return render(request, 'blueprint_create.html', {
        'title': 'Create New Blueprint',
        'submit_label': 'Create Blueprint',
        **_schedule_form_context(),
    })


def _clone_blueprint(
    source: Blueprint,
    name: str,
    weekday_mask: Optional[int] = None,
    interval_weeks: Optional[int] = None,
    anchor_date: Optional[date] = None,
) -> Blueprint:
    """Create a new blueprint copying source entries. The clone is active.

    Schedule defaults to the source unless explicit values are passed.
    """
    clone = Blueprint.objects.create(
        name=name,
        is_active=True,
        weekday_mask=source.weekday_mask if weekday_mask is None else weekday_mask,
        interval_weeks=source.interval_weeks if interval_weeks is None else interval_weeks,
        anchor_date=source.anchor_date if anchor_date is None else anchor_date,
    )
    BlueprintEntry.objects.bulk_create([
        BlueprintEntry(
            blueprint=clone,
            activity=entry.activity,
            place=entry.place,
            start=entry.start,
            duration=entry.duration,
        )
        for entry in source.get_entries()
    ])
    return clone


def blueprint_clone_view(request: HttpRequest, id: int) -> HttpResponse:
    """Clone a blueprint and open the copy for editing.

    GET: Shows a name field, defaulting to the source name plus ' (copy)'.
    POST: Copies entries onto a new active blueprint and redirects to edit.
    """
    source = get_object_or_404(Blueprint, pk=id)
    default_name = '%s (copy)' % source.name
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        weekday_mask, interval_weeks, anchor_date = _schedule_from_post(request.POST)
        if not name:
            return render(request, 'blueprint_create.html', {
                'error': 'Name is required.',
                'name': name,
                'source': source,
                'title': 'Clone Blueprint',
                'submit_label': 'Clone Blueprint',
                **_schedule_form_context(weekday_mask, interval_weeks, anchor_date),
            })
        clone = _clone_blueprint(
            source,
            name,
            weekday_mask=weekday_mask,
            interval_weeks=interval_weeks,
            anchor_date=anchor_date,
        )
        return redirect('blueprint_edit', id=clone.id)
    return render(request, 'blueprint_create.html', {
        'name': default_name,
        'source': source,
        'title': 'Clone Blueprint',
        'submit_label': 'Clone Blueprint',
        **_schedule_form_context(
            source.weekday_mask,
            source.interval_weeks,
            source.anchor_date,
        ),
    })

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
        weekday_mask, interval_weeks, anchor_date = _schedule_from_post(request.POST)
        blueprint.weekday_mask = weekday_mask
        blueprint.interval_weeks = interval_weeks
        blueprint.anchor_date = anchor_date
        blueprint.save(update_fields=['weekday_mask', 'interval_weeks', 'anchor_date'])

        # Delete all existing entries for this blueprint
        BlueprintEntry.objects.filter(blueprint=blueprint).delete()

        # Check if there's a start time for the first entry, otherwise default to midnight
        first_start_str = request.POST.get('start0', '')
        if first_start_str:
            # Parse the submitted start time
            first_start_time = datetime.strptime(first_start_str, '%H:%M').time()
            current_datetime = datetime.combine(local_today(), first_start_time)
        else:
            # Default to midnight if no start time provided
            current_datetime = datetime.combine(local_today(), time(hour=0, minute=0))

        # Process each row; ignore empty or zero-duration records
        i = 0
        while True:
            if f'duration{i}' not in request.POST:
                break
            duration_str = request.POST.get(f'duration{i}', '')
            if not duration_str or duration_str in ['0:00', '00:00']:
                i += 1
                continue

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

            if hours == 0 and minutes == 0:
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
        'blueprints_data': json.dumps(blueprints_data),
        **_schedule_form_context(
            blueprint.weekday_mask,
            blueprint.interval_weeks,
            blueprint.anchor_date,
        ),
    }
    return HttpResponse(template.render(context, request)) 