import calendar
import json
from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from ..models import Parent, Program, ToDoItem
from ..reports.utils import local_today
from .todo_views import (
    _activity_choices,
    _activity_choices_by_parent,
    _edit_activity_choices,
    handle_program_todo_post,
    program_parent_choices,
    program_todos,
    program_todo_redirect,
)


def program_parents_list(request):
    """View for displaying top-level parents as the Programs entry point.

    Shows all top-level parents (2-character ids) in a table format
    with columns: ID, Sort Order, Description, Importance, State.
    """
    parents = Parent.get_direct_children("ALL").select_related('importance')
    return render(request, 'program_parents_list.html', {
        'parents': parents
    })


def _program_for_parent(parent, program_id):
    """Return the Program for this parent matching program_id, or None.

    Args:
        parent: The parent category
        program_id: Posted or queried primary key, or None

    Returns:
        Program or None: Matching program belonging to parent, if any
    """
    if not program_id:
        return None
    try:
        program_pk = int(program_id)
    except (TypeError, ValueError):
        return None
    return Program.objects.filter(parent=parent, pk=program_pk).first()


def program_editor(request, parent_id):
    """View for viewing, updating, and cloning programs for a specific parent.

    GET: Shows a selected program (latest by default; ?edit=1 for edit mode
    on the latest program only). Edit is available only when a program
    exists. ?program=<id> selects a version.
    POST action=save: Updates the latest program (creates one if none exists)
    POST action=clone: Creates a new program copying the viewed description
    and redirects into edit mode.
    POST action=create/edit/delete/reorder: ToDoItem for this parent or a descendant.
    """
    parent = get_object_or_404(Parent, id=parent_id)
    children = Parent.get_direct_children(parent_id).select_related('importance')

    if request.method == 'POST':
        if handle_program_todo_post(request, parent):
            return redirect(program_todo_redirect(request, parent_id))
        action = request.POST.get('action')
        editor_url = reverse('program_editor', args=[parent_id])

        if action == 'clone':
            source = _program_for_parent(parent, request.POST.get('program'))
            if source is None:
                source = Program.get_latest_for_parent(parent)
            description = source.description if source else ''
            Program.objects.create(parent=parent, description=description)
            return redirect(editor_url + '?edit=1')
        elif action == 'save':
            program = Program.get_latest_for_parent(parent)
            description = request.POST.get('description', '')
            if program:
                program.description = description
                program.save()
            else:
                Program.objects.create(parent=parent, description=description)

        return redirect(editor_url)

    programs = list(Program.get_all_for_parent(parent))
    latest = programs[0] if programs else None
    program = _program_for_parent(parent, request.GET.get('program'))
    if program is None:
        program = latest
    is_latest = program is not None and latest is not None and program.pk == latest.pk
    editing = is_latest and request.GET.get('edit') == '1'

    todo_edit_id = None
    raw_todo_edit = request.GET.get('todo_edit')
    if raw_todo_edit:
        try:
            todo_edit_id = int(raw_todo_edit)
        except (TypeError, ValueError):
            todo_edit_id = None

    cancel_query = {}
    if request.GET.get('program') and program:
        cancel_query['program'] = str(program.pk)
    if editing:
        cancel_query['edit'] = '1'
    cancel_path = reverse('program_editor', args=[parent_id])
    if cancel_query:
        cancel_path += '?' + urlencode(cancel_query)

    return render(request, 'program_editor.html', {
        'parent': parent,
        'children': children,
        'programs': programs,
        'program': program,
        'is_latest': is_latest,
        'editing': editing,
        'todos': program_todos(parent),
        'parent_list': program_parent_choices(parent),
        'activity_list': _activity_choices(),
        'edit_activity_list': _edit_activity_choices(todo_edit_id),
        'activities_by_parent_json': json.dumps(_activity_choices_by_parent()),
        'todo_edit_id': todo_edit_id,
        'next_path': request.get_full_path(),
        'cancel_path': cancel_path,
        'horizon_choices': ToDoItem.Horizon.choices,
        'month_choices': [
            (i, calendar.month_name[i]) for i in range(1, 13)
        ],
        'default_year': local_today().year,
    })
