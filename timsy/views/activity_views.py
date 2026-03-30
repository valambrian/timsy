from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from ..models import Activity, Parent, Place
from ..models.urgency import Urgency
from ..models.importance import Importance

def top_parents_list(request):
    """View for displaying a list of top-level parents.
    
    Shows all top-level parents (2-character abbreviations) in a table format
    with columns: ID, Sort Order, Description, Importance, Active.
    """
    parents = Parent.get_direct_children("ALL").select_related('importance')
    return render(request, 'top_parents_list.html', {
        'parents': parents
    })

def activity_editor(request, parent_id):
    """View for editing activities that belong to a specific parent.
    
    GET: Shows the form with existing activities and 5 empty rows
    POST: Validates and saves form data to database with independent row processing
    """
    parent = get_object_or_404(Parent, id=parent_id)
    
    # Get activities for this parent
    activities = Activity.objects.filter(parent_id=parent_id).order_by('sort_order', 'id').select_related('parent', 'importance', 'urgency')
    
    # Get direct children of current parent
    children = Parent.get_direct_children(parent_id).select_related('importance')
    
    if request.method == 'POST':
        errors = {}
        success_count = 0
        preserved_data = {}
        
        # Process each row independently
        i = 0
        while True:
            # Get form data for this row
            activity_id = request.POST.get(f'activity_id{i}', '').strip()
            abbreviation = request.POST.get(f'abbreviation{i}', '').strip()
            description = request.POST.get(f'description{i}', '').strip()
            parent_id_field = request.POST.get(f'parent{i}', '').strip()
            importance_id = request.POST.get(f'importance{i}', '').strip()
            urgency_id = request.POST.get(f'urgency{i}', '').strip()
            sort_order = request.POST.get(f'sort_order{i}', '').strip()
            
            # Check if we've processed all rows (no more form data)
            if f'activity_id{i}' not in request.POST:
                break
            
            # Skip row if both abbreviation AND description are empty
            if not abbreviation and not description:
                i += 1
                continue
            
            # Row will be processed - validate all required fields
            row_errors = []
            
            # Cross-field validation: if abbreviation provided, description required
            if abbreviation and not description:
                row_errors.append("Description is required when abbreviation is provided")
            
            # Required fields when processing
            if not parent_id_field:
                row_errors.append("Parent is required when abbreviation or description is provided")
            if not importance_id:
                row_errors.append("Importance is required when abbreviation or description is provided")
            if not urgency_id:
                row_errors.append("Urgency is required when abbreviation or description is provided")
            
            # Validate parent, importance, urgency exist
            try:
                if parent_id_field:
                    parent_obj = Parent.objects.get(id=parent_id_field)
            except Parent.DoesNotExist:
                row_errors.append("Invalid parent ID")
                parent_obj = None
            
            try:
                if importance_id:
                    importance_obj = Importance.objects.get(id=importance_id)
            except Importance.DoesNotExist:
                row_errors.append("Invalid importance ID")
                importance_obj = None
            
            try:
                if urgency_id:
                    urgency_obj = Urgency.objects.get(id=urgency_id)
            except Urgency.DoesNotExist:
                row_errors.append("Invalid urgency ID")
                urgency_obj = None
            
            # Process abbreviation
            if abbreviation:
                abbreviation = abbreviation.lower()
            
            # Process sort order
            if sort_order:
                try:
                    sort_order = int(sort_order)
                except ValueError:
                    row_errors.append("Sort order must be a number")
                    sort_order = 999
            else:
                sort_order = 999
            
            # Check abbreviation uniqueness if not empty
            if abbreviation:
                if activity_id:
                    # Existing activity - check if abbreviation changed
                    try:
                        existing_activity = Activity.objects.get(id=activity_id)
                        if existing_activity.abbreviation != abbreviation:
                            # Abbreviation changed - check uniqueness
                            if Activity.objects.filter(abbreviation=abbreviation).exists():
                                row_errors.append(f"Abbreviation '{abbreviation}' already exists in another activity")
                    except Activity.DoesNotExist:
                        row_errors.append("Activity ID does not exist, record ignored")
                        preserved_data[i] = {
                            'activity_id': activity_id,
                            'abbreviation': request.POST.get(f'abbreviation{i}', ''),
                            'description': description,
                            'parent': parent_id_field,
                            'importance': importance_id,
                            'urgency': urgency_id,
                            'sort_order': request.POST.get(f'sort_order{i}', '')
                        }
                        errors[i] = row_errors
                        i += 1
                        continue
                else:
                    # New activity - check uniqueness
                    if Activity.objects.filter(abbreviation=abbreviation).exists():
                        row_errors.append(f"Abbreviation '{abbreviation}' already exists in another activity")
            
            # If there are validation errors, preserve data and continue
            if row_errors:
                preserved_data[i] = {
                    'activity_id': activity_id,
                    'abbreviation': request.POST.get(f'abbreviation{i}', ''),
                    'description': description,
                    'parent': parent_id_field,
                    'importance': importance_id,
                    'urgency': urgency_id,
                    'sort_order': request.POST.get(f'sort_order{i}', '')
                }
                errors[i] = row_errors
                i += 1
                continue
            
            # Save the activity (each in its own transaction)
            try:
                with transaction.atomic():
                    if activity_id:
                        # Update existing activity
                        try:
                            existing_activity = Activity.objects.get(id=activity_id)
                            
                            # Check if anything changed
                            changed = False
                            if existing_activity.abbreviation != abbreviation:
                                changed = True
                            if existing_activity.description != description:
                                changed = True
                            if existing_activity.parent_id != parent_id_field:
                                changed = True
                            if existing_activity.importance_id != int(importance_id):
                                changed = True
                            if existing_activity.urgency_id != int(urgency_id):
                                changed = True
                            if existing_activity.sort_order != sort_order:
                                changed = True
                            
                            if changed:
                                existing_activity.abbreviation = abbreviation
                                existing_activity.description = description
                                existing_activity.parent_id = parent_id_field
                                existing_activity.importance_id = importance_id
                                existing_activity.urgency_id = urgency_id
                                existing_activity.sort_order = sort_order
                                existing_activity.save()
                                success_count += 1
                        except Activity.DoesNotExist:
                            errors[i] = ["Activity ID does not exist, record ignored"]
                            preserved_data[i] = {
                                'activity_id': activity_id,
                                'abbreviation': request.POST.get(f'abbreviation{i}', ''),
                                'description': description,
                                'parent': parent_id_field,
                                'importance': importance_id,
                                'urgency': urgency_id,
                                'sort_order': request.POST.get(f'sort_order{i}', '')
                            }
                    else:
                        # Create new activity
                        Activity.objects.create(
                            abbreviation=abbreviation,
                            description=description,
                            parent_id=parent_id_field,
                            importance_id=importance_id,
                            urgency_id=urgency_id,
                            sort_order=sort_order
                        )
                        success_count += 1
                        
            except Exception as e:
                errors[i] = [f"Error saving activity: {str(e)}"]
                preserved_data[i] = {
                    'activity_id': activity_id,
                    'abbreviation': request.POST.get(f'abbreviation{i}', ''),
                    'description': description,
                    'parent': parent_id_field,
                    'importance': importance_id,
                    'urgency': urgency_id,
                    'sort_order': request.POST.get(f'sort_order{i}', '')
                }
            
            i += 1
        
        # Add messages
        if success_count > 0:
            messages.success(request, "Activities saved successfully")
        
        # If there are errors, render with error data
        if errors:
            # Refresh activities from database to show any successful saves
            activities = Activity.objects.filter(parent_id=parent_id).order_by('sort_order', 'id').select_related('parent', 'importance', 'urgency')
            
            # Prepare form data
            form = {
                'parent_list': [(p.id, str(p)) for p in Parent.objects.filter(active=True)],
                'importance_list': [(i.id, str(i)) for i in Importance.objects.all()],
                'urgency_list': [(u.id, str(u)) for u in Urgency.objects.all()],
                'place_list': list(Place.objects.values_list('abbreviation', flat=True))
            }
            
            return render(request, 'activity_editor.html', {
                'parent': parent,
                'activities': activities,
                'children': children,
                'form': form,
                'errors': errors,
                'preserved_data': preserved_data
            })
        
        # Redirect back to same page on success
        return redirect('activity_editor', parent_id=parent_id)
    
    # Prepare form data for template
    form = {
        'parent_list': [(p.id, str(p)) for p in Parent.objects.filter(active=True)],
        'importance_list': [(i.id, str(i)) for i in Importance.objects.all()],
        'urgency_list': [(u.id, str(u)) for u in Urgency.objects.all()],
        'place_list': list(Place.objects.values_list('abbreviation', flat=True))
    }
    
    return render(request, 'activity_editor.html', {
        'parent': parent,
        'activities': activities,
        'children': children,
        'form': form
    }) 