from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from urllib.parse import urlencode
from ..models import DailyPlan, Activity, Place, DailyPlanEntry, Blueprint, WeeklyPlan
from ..models.urgency import Urgency
from ..models.importance import Importance
from ..models.parent import Parent
from datetime import date, timedelta, datetime, time
from django.core.exceptions import ValidationError
from ..reports.utils import local_today, parse_duration_string, week_start_for, seconds_to_hhmm
import json
from django.db.models import Case, When, Value, IntegerField
from .todo_views import (
    handle_plan_todo_post,
    plan_todo_redirect,
    plan_todo_sidebar_context,
)

def daily_plan_list(request):
    """View for displaying a list of daily plans.
    
    Shows active daily plans by default, or all plans when show=all.
    Today's plan is listed first (if available), then the rest ordered
    by date with the most recent first.
    """
    today = local_today()
    show_all = request.GET.get('show') == 'all'
    
    # Create custom ordering: today's plan first (order=0), then by -date
    plans = DailyPlan.objects.annotate(
        custom_order=Case(
            When(date=today, then=Value(0)),
            default=Value(1),
            output_field=IntegerField()
        )
    )
    if not show_all:
        plans = plans.filter(active=True)
    plans = plans.order_by('custom_order', '-date')
    
    return render(request, 'daily_plan_list.html', {
        'plans': plans,
        'show_all': show_all,
        'today': today,
    })


def daily_plan_toggle_active(request, year, month, day):
    """Toggle a daily plan's active flag and return to the list."""
    plan_date = date(year, month, day)
    plan = get_object_or_404(DailyPlan, date=plan_date)
    plan.active = not plan.active
    plan.save(update_fields=['active'])

    url = reverse('daily_plan_list')
    if request.GET.get('show') == 'all':
        url += '?' + urlencode({'show': 'all'})
    return redirect(url)

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
    
    Shows the plan's timeline with activities, places, and durations,
    plus that date's day-horizon todos.
    """
    plan_date = date(year, month, day)
    plan = get_object_or_404(DailyPlan, date=plan_date)

    if request.method == 'POST':
        if handle_plan_todo_post(request):
            return redirect(plan_todo_redirect(request, year, month, day))
        return redirect('daily_plan_view', year=year, month=month, day=day)

    entries = plan.get_entries().select_related('activity', 'place')
    context = {
        'plan': plan,
        'entries': entries,
        'today': local_today(),
    }
    context.update(plan_todo_sidebar_context(request, plan_date))
    return render(request, 'daily_plan_view.html', context)

def week_budget_context(plan_date):
    """Return remaining-hours data for the weekly budget covering plan_date.

    Args:
        plan_date: The daily plan's date

    Returns:
        list or None: Allocation rows for the editor, or None when no weekly plan
    """
    week_start = week_start_for(plan_date)
    weekly_plan = WeeklyPlan.for_week_start(week_start)
    if weekly_plan is None:
        return None
    allocations = weekly_plan.get_allocations()
    if not allocations:
        return None
    parent_ids = [allocation.parent_id for allocation in allocations]
    other_scheduled = weekly_plan.scheduled_seconds(
        parent_ids, exclude_date=plan_date
    )
    rows = []
    for allocation in allocations:
        other = other_scheduled.get(allocation.parent_id, 0)
        rows.append({
            'parent_id': allocation.parent_id,
            'description': allocation.parent.description,
            'budget_seconds': allocation.seconds,
            'budget': seconds_to_hhmm(allocation.seconds),
            'other_scheduled_seconds': other,
            'scheduled': seconds_to_hhmm(other),
            'remaining': seconds_to_hhmm(allocation.seconds - other),
        })
    return rows


def daily_plan_edit(request, year, month, day):
    """View for editing a specific daily plan.
    
    GET: Shows the edit form with current plan data and that date's todos
    POST: Todo actions update todos only; otherwise rebuilds plan entries
    """
    plan_date = date(year, month, day)
    plan = get_object_or_404(DailyPlan, date=plan_date)
    
    # Get entries ordered by start time
    entries = plan.get_entries().select_related('activity', 'place')
    
    if request.method == 'POST':
        if handle_plan_todo_post(request):
            return redirect(
                plan_todo_redirect(request, year, month, day, edit=True)
            )

        # Start with a datetime at midnight
        current_datetime = datetime.combine(local_today(), time(hour=0, minute=0))

        # Delete all existing entries for this plan
        DailyPlanEntry.objects.filter(plan=plan).delete()

        # Process each row until we find an empty duration
        i = 0
        while True:
            duration_str = request.POST.get(f'duration{i}', '')
            if not duration_str or duration_str in ['0:00', '00:00']:
                break

            # Get form values
            abbreviation = request.POST.get(f'abbreviation{i}', '')
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
        'parent_list': Parent.get_active_choices(),
        'importance_list': [(i.id, str(i)) for i in Importance.objects.all()],
        'urgency_list': [(u.id, str(u)) for u in Urgency.objects.all()],
        'place_list': list(Place.objects.values_list('abbreviation', flat=True))
    }

    # Active blueprints whose schedule matches this plan date
    blueprints = Blueprint.for_date(plan_date)
    blueprints_data = []
    for blueprint in blueprints:
        blueprint_entries = blueprint.get_entries()
        start_time = blueprint_entries[0].start if blueprint_entries else None
        blueprints_data.append({
            'id': blueprint.id,
            'name': blueprint.name,
            'start_time': start_time.strftime('%H:%M') if start_time else None
        })

    week_budget = week_budget_context(plan_date)
    return render(request, 'daily_plan_edit.html', {
        'plan': plan,
        'entries': entries,
        'form': form,
        'blueprints': json.dumps(blueprints_data),
        'week_budget': week_budget,
        'week_budget_json': json.dumps(week_budget),
        **plan_todo_sidebar_context(request, plan_date),
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
