from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from ..models import Parent, Program


def program_parents_list(request):
    """View for displaying top-level parents as the Programs entry point.

    Shows all top-level parents (2-character ids) in a table format
    with columns: ID, Sort Order, Description, Importance, Active.
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
    """
    parent = get_object_or_404(Parent, id=parent_id)
    children = Parent.get_direct_children(parent_id).select_related('importance')

    if request.method == 'POST':
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

    return render(request, 'program_editor.html', {
        'parent': parent,
        'children': children,
        'programs': programs,
        'program': program,
        'is_latest': is_latest,
        'editing': editing
    })
