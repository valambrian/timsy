from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from ..models import DailyPlan, Activity, Place, DailyPlanEntry, Blueprint
from ..models.urgency import Urgency
from ..models.importance import Importance
from ..models.parent import Parent
from datetime import date, timedelta, datetime, time
from django.core.exceptions import ValidationError
from ..reports.utils import parse_duration_string
import json
from django.db.models import Case, When, Value, IntegerField

def daily_plan_list(request):
    """View for displaying a list of daily plans.
    
    Shows all daily plans with today's plan first (if available), 
    then the rest ordered by date with the most recent first.
    """
    today = date.today()
    
    # Create custom ordering: today's plan first (order=0), then by -date
    plans = DailyPlan.objects.annotate(
        custom_order=Case(
            When(date=today, then=Value(0)),
            default=Value(1),
            output_field=IntegerField()
        )
    ).order_by('custom_order', '-date')
    
    return render(request, 'daily_plan_list.html', {
        'plans': plans
    })

def daily_plan_create(request):
    """View for creating a new daily plan.
    
    GET: Shows the form to create a new plan
    POST: Creates a new empty plan for the specified date
    """
    if request.method == 'POST':
        try:
            # Get form data
            plan_date = request.POST.get('date')
            
            # Convert date string to date object
            year, month, day = map(int, plan_date.split('-'))
            plan_date = date(year, month, day)
            
            # Check if plan already exists for this date
            if DailyPlan.objects.filter(date=plan_date).exists():
                return render(request, 'daily_plan_create.html', {
                    'error': f'A plan already exists for {plan_date.strftime("%B %d, %Y")}'
                })
            
            # Create the plan (empty, no blueprints)
            plan = DailyPlan.objects.create(date=plan_date)
            
            # Redirect to the plan edit view so user can add entries
            return redirect('daily_plan_edit', 
                          year=plan_date.year,
                          month=plan_date.month,
                          day=plan_date.day)
            
        except Exception as e:
            return render(request, 'daily_plan_create.html', {
                'error': f'Error creating plan: {str(e)}'
            })
            
    # GET request - show the form
    return render(request, 'daily_plan_create.html')

def daily_plan_view(request, year, month, day):
    """View for displaying details of a specific daily plan.
    
    Shows the plan's timeline with activities, places, and durations.
    """
    plan_date = date(year, month, day)
    plan = get_object_or_404(DailyPlan, date=plan_date)
    
    # Get entries ordered by start time
    entries = plan.get_entries().select_related('activity', 'place')
    
    return render(request, 'daily_plan_view.html', {
        'plan': plan,
        'entries': entries
    })

def daily_plan_edit(request, year, month, day):
    """View for editing a specific daily plan.
    
    GET: Shows the edit form with current plan data
    POST: Updates the plan entries with new activities and places
    """
    plan_date = date(year, month, day)
    plan = get_object_or_404(DailyPlan, date=plan_date)
    
    # Get entries ordered by start time
    entries = plan.get_entries().select_related('activity', 'place')
    
    if request.method == 'POST':
        # Start with a datetime at midnight
        current_datetime = datetime.combine(date.today(), time(hour=0, minute=0))

        # Delete all existing entries for this plan
        DailyPlanEntry.objects.filter(plan=plan).delete()

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
            hours, minutes = parse_duration_string(duration_str)
            duration = time(hour=hours, minute=minutes)
            place = Place.objects.get(abbreviation=request.POST[f'place{i}'].upper())

            # Create or get activity
            activity = Activity.find_or_create(abbreviation, description, parent, importance, urgency)

            # Create new entry
            entry = DailyPlanEntry(
                plan=plan,
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
        return redirect('daily_plan_edit', 
                      year=year,
                      month=month,
                      day=day)

    # Prepare form data for template
    form = {
        'parent_list': [(p.id, str(p)) for p in Parent.objects.filter(active=True)],
        'importance_list': [(i.id, str(i)) for i in Importance.objects.all()],
        'urgency_list': [(u.id, str(u)) for u in Urgency.objects.all()],
        'place_list': list(Place.objects.values_list('abbreviation', flat=True))
    }

    # Get all active blueprints for the blueprint panel
    blueprints = Blueprint.objects.filter(is_active=True).order_by('name')
    blueprints_data = []
    for blueprint in blueprints:
        blueprint_entries = blueprint.get_entries()
        start_time = blueprint_entries[0].start if blueprint_entries else None
        blueprints_data.append({
            'id': blueprint.id,
            'name': blueprint.name,
            'start_time': start_time.strftime('%H:%M') if start_time else None
        })

    return render(request, 'daily_plan_edit.html', {
        'plan': plan,
        'entries': entries,
        'form': form,
        'blueprints': json.dumps(blueprints_data)
    })

def blueprint_entries_api(request, blueprint_id):
    """API endpoint to get entries for a specific blueprint.
    
    Returns JSON with blueprint entries data.
    """
    blueprint = get_object_or_404(Blueprint, id=blueprint_id, is_active=True)
    entries = blueprint.get_entries()
    
    entries_data = []
    for entry in entries:
        entries_data.append({
            'start': entry.start.strftime('%H:%M'),
            'duration': entry.duration.strftime('%H:%M'),
            'place': entry.place.abbreviation,
            'abbreviation': entry.activity.abbreviation,
            'description': entry.activity.description,
            'parent_id': entry.activity.parent.id,
            'importance_id': entry.activity.importance.id,
            'urgency_id': entry.activity.urgency.id
        })
    
    return JsonResponse({'entries': entries_data}) 
