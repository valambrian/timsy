import re

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from ..models import Activity, Parent, Place
from ..models.urgency import Urgency
from ..models.importance import Importance


def _importance_list():
    """Return (id, description) pairs for importance selects."""
    return [(i.id, str(i)) for i in Importance.objects.all()]


def _activity_form():
    """Return choice lists used by the activity editor template."""
    return {
        'parent_list': Parent.get_active_choices(),
        'importance_list': _importance_list(),
        'urgency_list': [(u.id, str(u)) for u in Urgency.objects.all()],
        'place_list': list(Place.objects.values_list('abbreviation', flat=True))
    }


def _direct_child_id_regex(scope_id):
    """Regex that a new or listed parent id must match on this page.

    Args:
        scope_id: 'ALL' for top-level, or a parent id for its direct children

    Returns:
        str: Anchored regular expression
    """
    if scope_id == "ALL":
        return r'^.{2}$'
    return r'^%s-.{2}$' % re.escape(scope_id)


def _parent_id_format_error(scope_id):
    """User-facing error when a new parent id is the wrong shape."""
    if scope_id == "ALL":
        return "ID must be exactly 2 characters"
    return "ID must be %s- followed by 2 characters" % scope_id


def _posted_parent_row(request, i, parent_id, description, importance_id, state):
    """Snapshot of posted parent fields for redisplay after validation errors."""
    return {
        'parent_id': parent_id,
        'existing_id': request.POST.get(f'existing_id{i}', ''),
        'description': description,
        'sort_order': request.POST.get(f'sort_order{i}', ''),
        'importance': importance_id,
        'state': state,
    }


def save_parent_rows(request, scope_id):
    """Create or update posted parent rows for one hierarchy page.

    Existing rows are identified by existing_id{i}. New rows use parent_id{i}
    as the full hierarchical id. Empty rows (no id and no description) are
    skipped. Successful rows are saved even when other rows fail.

    Args:
        request: The HTTP request with POST row fields
        scope_id: 'ALL' for top-level parents, or the current parent id

    Returns:
        tuple: (errors, preserved_data, success_count)
    """
    errors = {}
    preserved_data = {}
    success_count = 0
    id_pattern = _direct_child_id_regex(scope_id)

    i = 0
    while True:
        if f'parent_id{i}' not in request.POST:
            break

        existing_id = request.POST.get(f'existing_id{i}', '').strip()
        parent_id = request.POST.get(f'parent_id{i}', '').strip()
        description = request.POST.get(f'description{i}', '').strip()
        importance_id = request.POST.get(f'importance{i}', '').strip()
        sort_order = request.POST.get(f'sort_order{i}', '').strip()
        state = request.POST.get(f'state{i}', '').strip()

        if not parent_id and not description:
            i += 1
            continue

        row_errors = []

        if parent_id and not description:
            row_errors.append("Description is required when ID is provided")
        if description and not parent_id:
            row_errors.append("ID is required")

        if not importance_id:
            row_errors.append("Importance is required when ID or description is provided")

        importance_obj = None
        try:
            if importance_id:
                importance_obj = Importance.objects.get(id=importance_id)
        except (Importance.DoesNotExist, ValueError, TypeError):
            row_errors.append("Invalid importance ID")
            importance_obj = None

        if sort_order:
            try:
                sort_order = int(sort_order)
            except ValueError:
                row_errors.append("Sort order must be a number")
                sort_order = 999
        else:
            sort_order = 999

        if existing_id:
            if not state:
                row_errors.append("State is required")
            elif state not in Parent.State.values:
                row_errors.append("Invalid state")
        else:
            if not state:
                state = Parent.State.ACTIVE
            elif state not in Parent.State.values:
                row_errors.append("Invalid state")

        if existing_id:
            try:
                existing_parent = Parent.objects.get(id=existing_id)
            except Parent.DoesNotExist:
                row_errors.append("Parent ID does not exist, record ignored")
                preserved_data[i] = _posted_parent_row(
                    request, i, parent_id, description, importance_id, state
                )
                errors[i] = row_errors
                i += 1
                continue
            if not re.match(id_pattern, existing_parent.id):
                row_errors.append("Parent does not belong on this page")
        else:
            existing_parent = None
            if parent_id:
                if not re.match(id_pattern, parent_id):
                    row_errors.append(_parent_id_format_error(scope_id))
                elif Parent.objects.filter(id=parent_id).exists():
                    row_errors.append("ID '%s' already exists" % parent_id)

        if row_errors:
            preserved_data[i] = _posted_parent_row(
                request, i, parent_id, description, importance_id,
                request.POST.get(f'state{i}', '').strip(),
            )
            errors[i] = row_errors
            i += 1
            continue

        try:
            with transaction.atomic():
                if existing_parent is not None:
                    changed = False
                    if existing_parent.description != description:
                        changed = True
                    if existing_parent.importance_id != int(importance_id):
                        changed = True
                    if existing_parent.sort_order != sort_order:
                        changed = True
                    if existing_parent.state != state:
                        changed = True

                    if changed:
                        existing_parent.description = description
                        existing_parent.importance_id = importance_id
                        existing_parent.sort_order = sort_order
                        existing_parent.state = state
                        existing_parent.save()
                        success_count += 1
                else:
                    Parent.objects.create(
                        id=parent_id,
                        description=description,
                        importance_id=importance_id,
                        sort_order=sort_order,
                        state=state,
                    )
                    success_count += 1
        except Exception as e:
            errors[i] = [f"Error saving parent: {str(e)}"]
            preserved_data[i] = _posted_parent_row(
                request, i, parent_id, description, importance_id,
                request.POST.get(f'state{i}', '').strip(),
            )

        i += 1

    return errors, preserved_data, success_count


def _top_parents_context(errors=None, preserved_data=None):
    """Context for the top-level parent editor page."""
    context = {
        'parents': Parent.get_direct_children("ALL").select_related('importance'),
        'importance_list': _importance_list(),
        'parent_state_choices': Parent.State.choices,
    }
    if errors is not None:
        context['errors'] = errors
        context['preserved_data'] = preserved_data
    return context


def top_parents_list(request):
    """View for displaying and editing top-level parents.

    GET: Shows existing top-level parents and one empty row for create.
    POST: Validates and saves parent rows independently.
    """
    if request.method == 'POST':
        errors, preserved_data, success_count = save_parent_rows(request, "ALL")
        if success_count > 0:
            messages.success(request, "Parents saved successfully")
        if errors:
            return render(
                request, 'top_parents_list.html',
                _top_parents_context(errors, preserved_data),
            )
        return redirect('top_parents_list')

    return render(request, 'top_parents_list.html', _top_parents_context())


def parent_set_state(request, parent_id):
    """Set a parent's state from POST and return to the Activities page."""
    parent = get_object_or_404(Parent, id=parent_id)
    if request.method == 'POST':
        new_state = request.POST.get('state', '')
        if new_state in Parent.State.values:
            parent.state = new_state
            parent.save(update_fields=['state'])
        nxt = request.POST.get('next', '')
    else:
        nxt = request.GET.get('next', '')
    if nxt.startswith('/timsy/'):
        return redirect(nxt)
    return redirect('top_parents_list')


def _activity_editor_context(parent, errors=None, preserved_data=None,
                             parent_errors=None, parent_preserved_data=None):
    """Context for the activity editor, including the subcategory parent form."""
    context = {
        'parent': parent,
        'activities': Activity.objects.filter(parent_id=parent.id).order_by(
            'sort_order', 'id'
        ).select_related('parent', 'importance', 'urgency'),
        'children': Parent.get_direct_children(parent.id).select_related('importance'),
        'form': _activity_form(),
        'importance_list': _importance_list(),
        'parent_state_choices': Parent.State.choices,
    }
    if errors is not None:
        context['errors'] = errors
        context['preserved_data'] = preserved_data
    if parent_errors is not None:
        context['parent_errors'] = parent_errors
        context['parent_preserved_data'] = parent_preserved_data
    return context


def save_child_parents(request, parent_id):
    """Save direct child parents of parent_id, then return to the activity editor.

    GET redirects to the activity editor. POST uses the same row saver as the
    top-level parent list.
    """
    parent = get_object_or_404(Parent, id=parent_id)
    if request.method != 'POST':
        return redirect('activity_editor', parent_id=parent_id)

    errors, preserved_data, success_count = save_parent_rows(request, parent_id)
    if success_count > 0:
        messages.success(request, "Parents saved successfully")
    if errors:
        return render(
            request, 'activity_editor.html',
            _activity_editor_context(
                parent,
                parent_errors=errors,
                parent_preserved_data=preserved_data,
            ),
        )
    return redirect('activity_editor', parent_id=parent_id)


def activity_editor(request, parent_id):
    """View for editing activities that belong to a specific parent.
    
    GET: Shows the form with existing activities and 5 empty rows
    POST: Validates and saves form data to database with independent row processing
    """
    parent = get_object_or_404(Parent, id=parent_id)
    
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
            is_placeholder = bool(request.POST.get(f'is_placeholder{i}'))
            
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
                            'is_placeholder': is_placeholder,
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
                    'is_placeholder': is_placeholder,
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
                            if existing_activity.is_placeholder != is_placeholder:
                                changed = True
                            
                            if changed:
                                existing_activity.abbreviation = abbreviation
                                existing_activity.description = description
                                existing_activity.parent_id = parent_id_field
                                existing_activity.importance_id = importance_id
                                existing_activity.urgency_id = urgency_id
                                existing_activity.sort_order = sort_order
                                existing_activity.is_placeholder = is_placeholder
                                existing_activity.save()
                                success_count += 1
                        except Activity.DoesNotExist:
                            errors[i] = ["Activity ID does not exist, record ignored"]
                            preserved_data[i] = {
                                'activity_id': activity_id,
                                'abbreviation': request.POST.get(f'abbreviation{i}', ''),
                                'description': description,
                                'is_placeholder': is_placeholder,
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
                            sort_order=sort_order,
                            is_placeholder=is_placeholder
                        )
                        success_count += 1
                        
            except Exception as e:
                errors[i] = [f"Error saving activity: {str(e)}"]
                preserved_data[i] = {
                    'activity_id': activity_id,
                    'abbreviation': request.POST.get(f'abbreviation{i}', ''),
                    'description': description,
                    'is_placeholder': is_placeholder,
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
            return render(
                request, 'activity_editor.html',
                _activity_editor_context(parent, errors, preserved_data),
            )
        
        # Redirect back to same page on success
        return redirect('activity_editor', parent_id=parent_id)
    
    return render(request, 'activity_editor.html', _activity_editor_context(parent))
