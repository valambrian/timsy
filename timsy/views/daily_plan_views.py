from django.shortcuts import render, get_object_or_404, redirect
from ..models import DailyPlan, IdealDayTemplate, Activity, Place, DailyPlanEntry
from ..models.urgency import Urgency
from ..models.importance import Importance
from ..models.parent import Parent
from django import forms
from datetime import date, timedelta, datetime, time
from django.core.exceptions import ValidationError
import json

class DailyPlanEntryForm(forms.Form):
    record_id = forms.IntegerField(required=False)
    start = forms.TimeField(required=False)
    abbreviation = forms.CharField(max_length=10, required=False)
    description = forms.CharField(max_length=200, required=False)
    parent = forms.ModelChoiceField(queryset=Parent.objects.filter(active=True), required=False)
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

DailyPlanEntryFormSet = forms.formset_factory(DailyPlanEntryForm, extra=5)

def daily_plan_list(request):
    """View for displaying a list of daily plans.
    
    Shows all daily plans ordered by date, with the most recent first.
    """
    plans = DailyPlan.objects.all().order_by('-date')
    return render(request, 'daily_plan_list.html', {
        'plans': plans
    })

def daily_plan_create(request):
    """View for creating a new daily plan.
    
    GET: Shows the form to create a new plan
    POST: Creates a new plan from the selected template
    """
    if request.method == 'POST':
        try:
            # Get form data
            plan_date = request.POST.get('date')
            template_id = request.POST.get('template')
            
            # Convert date string to date object
            year, month, day = map(int, plan_date.split('-'))
            plan_date = date(year, month, day)
            
            # Get template
            template = get_object_or_404(IdealDayTemplate, id=template_id)
            
            # Create the plan using the class method
            plan = DailyPlan.generate_daily_plan(date=plan_date, template=template)
            
            # Redirect to the plan view
            return redirect('daily_plan_view', 
                          year=plan_date.year,
                          month=plan_date.month,
                          day=plan_date.day)
            
        except ValidationError as e:
            # If plan already exists, show error
            return render(request, 'daily_plan_create.html', {
                'templates': IdealDayTemplate.objects.filter(is_active=True),
                'error': str(e)
            })
            
    # GET request - show the form
    return render(request, 'daily_plan_create.html', {
        'templates': IdealDayTemplate.objects.filter(is_active=True)
    })

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
    
    # Get list of valid places for validation
    valid_places = list(Place.objects.values_list('abbreviation', flat=True))
    
    # Prepare option lists for select fields
    parent_list = json.dumps([{'value': str(p.id), 'text': str(p)} for p in Parent.objects.filter(active=True)])
    importance_list = json.dumps([{'value': str(i.id), 'text': str(i)} for i in Importance.objects.all()])
    urgency_list = json.dumps([{'value': str(u.id), 'text': str(u)} for u in Urgency.objects.all()])
    
    if request.method == 'POST':
        formset = DailyPlanEntryFormSet(request.POST)
        if formset.is_valid():
            # Delete all existing entries for this plan
            DailyPlanEntry.objects.filter(plan=plan).delete()
            
            # Start with a datetime at midnight
            current_datetime = datetime.combine(date.today(), time(hour=0, minute=0))
            
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
                hours, minutes = map(int, duration_str.split(':'))
                duration = timedelta(hours=hours, minutes=minutes)
                place = form.cleaned_data['place']

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
                current_datetime = current_datetime + duration

            # Redirect back to edit page
            return redirect('daily_plan_edit', 
                          year=year,
                          month=month,
                          day=day)
    else:
        # For GET request, prepare initial data
        initial_data = []
        for entry in entries:
            initial_data.append({
                'record_id': entry.id,
                'start': entry.start.strftime('%H:%M'),
                'abbreviation': entry.activity.abbreviation,
                'description': entry.activity.description,
                'parent': entry.activity.parent,
                'importance': entry.activity.importance,
                'urgency': entry.activity.urgency,
                'duration': f"{entry.duration.seconds // 3600:02d}:{(entry.duration.seconds % 3600) // 60:02d}",
                'place': entry.place.abbreviation
            })
        formset = DailyPlanEntryFormSet(initial=initial_data)

    return render(request, 'daily_plan_edit.html', {
        'plan': plan,
        'formset': formset,
        'valid_places': json.dumps(valid_places),
        'parent_list': parent_list,
        'importance_list': importance_list,
        'urgency_list': urgency_list
    }) 
