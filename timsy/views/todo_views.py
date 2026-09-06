import calendar
import json
from datetime import date, timedelta

from django.db.models import Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..models import Activity, Parent, ToDoItem
from ..reports.utils import week_start_for, local_today


PAST_BGCOLOR = '#dddddd'


def _make_date(year, month, day):
    """Return a date or 404 if the calendar date is invalid."""
    try:
        return date(year, month, day)
    except ValueError:
        raise Http404


def _add_months(year, month, delta):
    """Shift a year/month by delta months. Returns (year, month)."""
    total = year * 12 + (month - 1) + delta
    return total // 12, total % 12 + 1


def _month_start(year, month):
    """First day of a month."""
    return date(year, month, 1)


def _month_end(year, month):
    """Last calendar day of a month."""
    return date(year, month, calendar.monthrange(year, month)[1])


def _period_end(horizon, horizon_date):
    """Last calendar day of a horizon period."""
    if horizon == ToDoItem.Horizon.DAY:
        return horizon_date
    if horizon == ToDoItem.Horizon.WEEK:
        return horizon_date + timedelta(days=6)
    if horizon == ToDoItem.Horizon.MONTH:
        return _month_end(horizon_date.year, horizon_date.month)
    return date(horizon_date.year, 12, 31)


def _is_past(horizon, horizon_date, today):
    """True when the period has already ended."""
    if horizon == ToDoItem.Horizon.YEAR:
        return horizon_date.year < today.year
    return _period_end(horizon, horizon_date) < today


def _horizon_date_for(horizon, d):
    """Canonical horizon_date for a period containing d."""
    if horizon == ToDoItem.Horizon.YEAR:
        return date(d.year, 1, 1)
    if horizon == ToDoItem.Horizon.MONTH:
        return date(d.year, d.month, 1)
    if horizon == ToDoItem.Horizon.WEEK:
        return week_start_for(d)
    return d


def _column_url(horizon, horizon_date):
    """List-page URL for a column header."""
    if horizon == ToDoItem.Horizon.YEAR:
        return reverse('todo_yearly', args=[horizon_date.year])
    if horizon == ToDoItem.Horizon.MONTH:
        return reverse('todo_monthly', args=[horizon_date.year, horizon_date.month])
    if horizon == ToDoItem.Horizon.WEEK:
        return reverse(
            'todo_weekly',
            args=[horizon_date.year, horizon_date.month, horizon_date.day],
        )
    return reverse(
        'todo_daily',
        args=[horizon_date.year, horizon_date.month, horizon_date.day],
    )


def _column_title(horizon, horizon_date):
    """Human-readable column heading."""
    if horizon == ToDoItem.Horizon.YEAR:
        return str(horizon_date.year)
    if horizon == ToDoItem.Horizon.MONTH:
        return horizon_date.strftime('%B %Y')
    if horizon == ToDoItem.Horizon.WEEK:
        return 'Week of %s' % horizon_date.strftime('%b %d, %Y')
    return horizon_date.strftime('%a %b %d, %Y')


def _items_for(horizon, horizon_date):
    """ToDoItems for one column, in sort_order."""
    return list(
        ToDoItem.objects.filter(
            horizon=horizon, horizon_date=horizon_date
        ).select_related('parent', 'activity').order_by('sort_order', 'id')
    )


def _build_column(horizon, horizon_date, today):
    """Column dict for the list template."""
    past = _is_past(horizon, horizon_date, today)
    return {
        'horizon': horizon,
        'horizon_date': horizon_date,
        'horizon_date_iso': horizon_date.isoformat(),
        'title': _column_title(horizon, horizon_date),
        'header_url': _column_url(horizon, horizon_date),
        'is_past': past,
        'bgcolor': PAST_BGCOLOR if past else '',
        'items': _items_for(horizon, horizon_date),
    }


def _next_sort_order(horizon, horizon_date):
    """Next sort_order in a column (0 if empty)."""
    maximum = ToDoItem.objects.filter(
        horizon=horizon, horizon_date=horizon_date
    ).aggregate(Max('sort_order'))['sort_order__max']
    return 0 if maximum is None else maximum + 1


def _next_program_order():
    """Next program_order among all todos (new items go last on program pages)."""
    maximum = ToDoItem.objects.aggregate(Max('program_order'))['program_order__max']
    return 0 if maximum is None else maximum + 1


def _parent_choices():
    """(id, description) for the parent select."""
    return Parent.get_active_choices()


def _activity_label(activity):
    """Abbreviation-prefixed label for an activity option."""
    if activity.abbreviation:
        return '%s: %s' % (activity.abbreviation, activity.description)
    return activity.description


def _activity_choices(parent_id=None):
    """(id, label) for the optional activity select."""
    activities = Activity.objects.order_by('sort_order', 'id')
    if parent_id is not None:
        activities = activities.filter(parent_id=parent_id)
    return [(activity.id, _activity_label(activity)) for activity in activities]


def _activity_choices_by_parent():
    """parent_id -> [(id, label), ...] for filtering the activity select."""
    grouped = {}
    for activity in Activity.objects.order_by('sort_order', 'id'):
        grouped.setdefault(activity.parent_id, []).append(
            (activity.id, _activity_label(activity))
        )
    return grouped


def _edit_activity_choices(edit_id):
    """Activity options for the todo being edited, limited to its parent."""
    if not edit_id:
        return []
    item = ToDoItem.objects.filter(pk=edit_id).only('parent_id').first()
    if item is None:
        return []
    return _activity_choices(item.parent_id)


def _activity_for_parent(activity_id, parent_id):
    """Activity with this id that belongs to parent_id, or None."""
    if not activity_id:
        return None
    return Activity.objects.filter(pk=activity_id, parent_id=parent_id).first()


def _parse_posted_date(value):
    """Parse an ISO date from POST, or None."""
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _safe_next(request):
    """Redirect target after POST: same todos or daily-plan path, or this view."""
    nxt = request.POST.get('next', '')
    if nxt.startswith('/timsy/todos/') or nxt.startswith('/timsy/data/plans/daily/'):
        return nxt
    return request.path


def _resequence_column(horizon, horizon_date, ordered_items):
    """Write sort_order 0..n-1 for items now in a column."""
    for index, item in enumerate(ordered_items):
        update_fields = ['sort_order']
        if item.horizon != horizon or item.horizon_date != horizon_date:
            item.horizon = horizon
            item.horizon_date = horizon_date
            update_fields.extend(['horizon', 'horizon_date'])
        if item.sort_order != index:
            item.sort_order = index
            item.save(update_fields=update_fields)
        elif 'horizon' in update_fields:
            item.sort_order = index
            item.save(update_fields=update_fields)


def _handle_create(request):
    """Create a ToDoItem in the posted column if the column is not past."""
    today = local_today()
    horizon = request.POST.get('horizon', '')
    horizon_date = _parse_posted_date(request.POST.get('horizon_date'))
    description = request.POST.get('description', '').strip()
    parent_id = request.POST.get('parent', '')
    if horizon not in ToDoItem.Horizon.values or horizon_date is None:
        return
    if _is_past(horizon, horizon_date, today):
        return
    if not description or not parent_id:
        return
    parent = Parent.objects.filter(pk=parent_id).first()
    if parent is None:
        return
    activity = _activity_for_parent(
        request.POST.get('activity', '').strip(), parent.id
    )
    ToDoItem.objects.create(
        parent=parent,
        description=description,
        activity=activity,
        horizon=horizon,
        horizon_date=horizon_date,
        status=ToDoItem.Status.OPEN,
        sort_order=_next_sort_order(horizon, horizon_date),
        program_order=_next_program_order(),
        note=request.POST.get('note', ''),
    )


def _handle_edit(request):
    """Update parent, description, activity, and note on an existing item."""
    item = get_object_or_404(ToDoItem, pk=request.POST.get('item_id'))
    description = request.POST.get('description', '').strip()
    parent_id = request.POST.get('parent', '')
    if not description or not parent_id:
        return
    parent = Parent.objects.filter(pk=parent_id).first()
    if parent is None:
        return
    activity = _activity_for_parent(
        request.POST.get('activity', '').strip(), parent.id
    )
    item.parent = parent
    item.description = description
    item.activity = activity
    item.note = request.POST.get('note', '')
    item.save()


def _handle_delete(request):
    """Delete a ToDoItem."""
    item = ToDoItem.objects.filter(pk=request.POST.get('item_id')).first()
    if item:
        item.delete()


def _handle_set_status(request):
    """Set open/done from the checkbox (done present => done)."""
    item = ToDoItem.objects.filter(pk=request.POST.get('item_id')).first()
    if item is None:
        return
    if request.POST.get('done'):
        item.status = ToDoItem.Status.DONE
    else:
        item.status = ToDoItem.Status.OPEN
    item.save(update_fields=['status'])


def _handle_move(request):
    """Move an item to another column or reorder within a column."""
    item = ToDoItem.objects.filter(pk=request.POST.get('item_id')).first()
    move_target = request.POST.get('move_target', '')
    if move_target and '|' in move_target:
        horizon, date_str = move_target.split('|', 1)
        horizon_date = _parse_posted_date(date_str)
    else:
        horizon = request.POST.get('horizon', '')
        horizon_date = _parse_posted_date(request.POST.get('horizon_date'))
    if item is None or horizon not in ToDoItem.Horizon.values or horizon_date is None:
        return
    siblings = list(
        ToDoItem.objects.filter(
            horizon=horizon, horizon_date=horizon_date
        ).exclude(pk=item.pk).order_by('sort_order', 'id')
    )
    before_id = request.POST.get('before_id', '').strip()
    new_order = []
    inserted = False
    if before_id:
        try:
            before_pk = int(before_id)
        except (TypeError, ValueError):
            before_pk = None
        for sibling in siblings:
            if sibling.pk == before_pk:
                new_order.append(item)
                inserted = True
            new_order.append(sibling)
    if not inserted:
        new_order = siblings + [item]
    _resequence_column(horizon, horizon_date, new_order)


TODO_ACTIONS = ('create', 'edit', 'delete', 'set_status', 'move')


def _handle_post(request):
    """Dispatch a list-page POST action."""
    action = request.POST.get('action')
    if action == 'create':
        _handle_create(request)
    elif action == 'edit':
        _handle_edit(request)
    elif action == 'delete':
        _handle_delete(request)
    elif action == 'set_status':
        _handle_set_status(request)
    elif action == 'move':
        _handle_move(request)


def _list_context(request, title, columns, prev_url, next_url, extra_nav=None):
    """Shared template context for period list pages."""
    edit_id = None
    raw_edit = request.GET.get('edit')
    if raw_edit:
        try:
            edit_id = int(raw_edit)
        except (TypeError, ValueError):
            edit_id = None
    cancel_path = request.path
    month = request.GET.get('month')
    if month:
        cancel_path += '?month=%s' % month
    return {
        'title': title,
        'columns': columns,
        'prev_url': prev_url,
        'next_url': next_url,
        'extra_nav': extra_nav or [],
        'parent_list': _parent_choices(),
        'activity_list': _activity_choices(),
        'edit_activity_list': _edit_activity_choices(edit_id),
        'activities_by_parent_json': json.dumps(_activity_choices_by_parent()),
        'edit_id': edit_id,
        'next_path': request.get_full_path(),
        'cancel_path': cancel_path,
    }


def _render_list(request, title, columns, prev_url, next_url, extra_nav=None):
    """Handle POST then render the shared list template."""
    if request.method == 'POST':
        _handle_post(request)
        return redirect(_safe_next(request))
    return render(
        request,
        'todo_list.html',
        _list_context(request, title, columns, prev_url, next_url, extra_nav),
    )


def _yearly_month_start(year, today, requested):
    """First month of the four-month window (1-12)."""
    if requested is not None:
        return max(1, min(12, requested))
    if year == today.year:
        return today.month
    return 1


def _yearly_months(start_month):
    """Up to four months from start_month through December."""
    months = []
    month = start_month
    while month <= 12 and len(months) < 4:
        months.append(month)
        month += 1
    return months


def todo_today(request):
    """Redirect to the daily list for today."""
    today = local_today()
    return redirect('todo_daily', today.year, today.month, today.day)


def todo_this_week(request):
    """Redirect to the weekly list for the current week."""
    start = week_start_for(local_today())
    return redirect('todo_weekly', start.year, start.month, start.day)


def todo_this_month(request):
    """Redirect to the monthly list for the current month."""
    today = local_today()
    return redirect('todo_monthly', today.year, today.month)


def todo_this_year(request):
    """Redirect to the yearly list for the current year."""
    return redirect('todo_yearly', local_today().year)


def todo_daily(request, year, month, day):
    """Daily list: selected day | next day."""
    selected = _make_date(year, month, day)
    tomorrow = selected + timedelta(days=1)
    today = local_today()
    columns = [
        _build_column(ToDoItem.Horizon.DAY, selected, today),
        _build_column(ToDoItem.Horizon.DAY, tomorrow, today),
    ]
    prev_day = selected - timedelta(days=1)
    next_day = selected + timedelta(days=1)
    title = 'Daily todos — %s' % selected.strftime('%A, %B %d, %Y')
    return _render_list(
        request,
        title,
        columns,
        reverse('todo_daily', args=[prev_day.year, prev_day.month, prev_day.day]),
        reverse('todo_daily', args=[next_day.year, next_day.month, next_day.day]),
    )


def todo_weekly(request, year, month, day):
    """Weekly list: days of the week | this week | next week."""
    raw = _make_date(year, month, day)
    start = week_start_for(raw)
    if raw != start and request.method == 'GET':
        return redirect('todo_weekly', start.year, start.month, start.day)
    today = local_today()
    columns = []
    for offset in range(7):
        columns.append(
            _build_column(ToDoItem.Horizon.DAY, start + timedelta(days=offset), today)
        )
    next_week = start + timedelta(days=7)
    prev_week = start - timedelta(days=7)
    columns.append(_build_column(ToDoItem.Horizon.WEEK, start, today))
    columns.append(_build_column(ToDoItem.Horizon.WEEK, next_week, today))
    title = 'Weekly todos — week of %s' % start.strftime('%A, %B %d, %Y')
    return _render_list(
        request,
        title,
        columns,
        reverse('todo_weekly', args=[prev_week.year, prev_week.month, prev_week.day]),
        reverse('todo_weekly', args=[next_week.year, next_week.month, next_week.day]),
    )


def _weeks_starting_in_month(year, month):
    """Week-start dates that fall in this calendar month."""
    first = date(year, month, 1)
    last = _month_end(year, month)
    week_start = week_start_for(first)
    weeks = []
    while week_start <= last:
        if week_start.year == year and week_start.month == month:
            weeks.append(week_start)
        week_start += timedelta(days=7)
    return weeks


def todo_monthly(request, year, month):
    """Monthly list: weeks starting in the month | this month | next month."""
    if month < 1 or month > 12:
        raise Http404
    this_month = _month_start(year, month)
    next_year, next_month = _add_months(year, month, 1)
    prev_year, prev_month = _add_months(year, month, -1)
    today = local_today()
    columns = [
        _build_column(ToDoItem.Horizon.WEEK, week_start, today)
        for week_start in _weeks_starting_in_month(year, month)
    ]
    columns.append(_build_column(ToDoItem.Horizon.MONTH, this_month, today))
    columns.append(
        _build_column(ToDoItem.Horizon.MONTH, _month_start(next_year, next_month), today)
    )
    title = 'Monthly todos — %s' % this_month.strftime('%B %Y')
    return _render_list(
        request,
        title,
        columns,
        reverse('todo_monthly', args=[prev_year, prev_month]),
        reverse('todo_monthly', args=[next_year, next_month]),
    )


def todo_yearly(request, year):
    """Yearly list: month window | this year | next year."""
    today = local_today()
    requested = request.POST.get('month_window') or request.GET.get('month')
    start_month = None
    if requested:
        try:
            start_month = int(requested)
        except (TypeError, ValueError):
            start_month = None
    start_month = _yearly_month_start(year, today, start_month)
    months = _yearly_months(start_month)
    this_year = date(year, 1, 1)
    next_year_date = date(year + 1, 1, 1)
    columns = [
        _build_column(ToDoItem.Horizon.MONTH, date(year, month, 1), today)
        for month in months
    ]
    columns.append(_build_column(ToDoItem.Horizon.YEAR, this_year, today))
    columns.append(_build_column(ToDoItem.Horizon.YEAR, next_year_date, today))
    extra_nav = []
    if start_month > 1:
        extra_nav.append({
            'label': 'Earlier months',
            'url': reverse('todo_yearly', args=[year]) + '?month=%d' % (start_month - 1),
        })
    if start_month < 12:
        extra_nav.append({
            'label': 'Later months',
            'url': reverse('todo_yearly', args=[year]) + '?month=%d' % (start_month + 1),
        })
    title = 'Yearly todos — %d' % year
    return _render_list(
        request,
        title,
        columns,
        reverse('todo_yearly', args=[year - 1]),
        reverse('todo_yearly', args=[year + 1]),
        extra_nav,
    )


def _parent_in_program_scope(owner_id, parent):
    """True if owner_id is this parent or a descendant in the id tree."""
    return owner_id == parent.id or owner_id.startswith(parent.id + '-')


def _todo_in_program_scope(item, parent):
    """True if the item belongs to this parent or a descendant in the id tree."""
    return _parent_in_program_scope(item.parent_id, parent)


def program_parent_choices(parent):
    """(id, description) for this parent and descendants, hierarchy order."""
    prefix = parent.id + '-'
    choices = [(parent.id, parent.description)]
    for obj in Parent._in_hierarchy_order():
        if obj.id.startswith(prefix):
            choices.append((obj.id, obj.description))
    return choices


def program_todos(parent):
    """Open todos for this parent and descendants, in program_order."""
    prefix = parent.id + '-'
    items = list(
        ToDoItem.objects.filter(status=ToDoItem.Status.OPEN)
        .filter(Q(parent=parent) | Q(parent__id__startswith=prefix))
        .select_related('parent', 'activity')
        .order_by('program_order', 'id')
    )
    for item in items:
        item.horizon_title = _column_title(item.horizon, item.horizon_date)
        item.horizon_url = _column_url(item.horizon, item.horizon_date)
    return items


def _handle_program_reorder(request, parent):
    """Reorder open todos on this program page. Parent is unchanged."""
    item = ToDoItem.objects.filter(pk=request.POST.get('item_id')).first()
    if item is None or not _todo_in_program_scope(item, parent):
        return
    siblings = [todo for todo in program_todos(parent) if todo.pk != item.pk]
    before_id = request.POST.get('before_id', '').strip()
    new_order = []
    inserted = False
    if before_id:
        try:
            before_pk = int(before_id)
        except (TypeError, ValueError):
            before_pk = None
        else:
            for sibling in siblings:
                if sibling.pk == before_pk:
                    new_order.append(item)
                    inserted = True
                new_order.append(sibling)
    if not inserted:
        new_order = siblings + [item]
    for index, row in enumerate(new_order):
        if row.program_order != index:
            row.program_order = index
            row.save(update_fields=['program_order'])


def _posted_horizon_date(request):
    """Canonical horizon and horizon_date from posted parts, or (None, None).

    Horizon defaults to year. Year defaults to the current year. Month and
    day are ignored for coarser horizons. Invalid calendar dates return None.
    """
    horizon = request.POST.get('horizon', '')
    if horizon not in ToDoItem.Horizon.values:
        horizon = ToDoItem.Horizon.YEAR
    try:
        year = int(request.POST.get('year'))
    except (TypeError, ValueError):
        year = local_today().year
    month = 1
    day = 1
    if horizon != ToDoItem.Horizon.YEAR:
        try:
            month = int(request.POST.get('month'))
        except (TypeError, ValueError):
            return None, None
    if horizon in (ToDoItem.Horizon.WEEK, ToDoItem.Horizon.DAY):
        try:
            day = int(request.POST.get('day'))
        except (TypeError, ValueError):
            return None, None
    try:
        posted = date(year, month, day)
    except ValueError:
        return None, None
    return horizon, _horizon_date_for(horizon, posted)


def handle_program_todo_post(request, parent):
    """Create, edit, delete, or reorder a todo from the program editor.

    Parent for create is this page's parent or a descendant. Edit, delete,
    and reorder also apply to descendant-owned items. Reorder changes
    program_order only. Create and edit use posted horizon/year/month/day.
    Returns True if this POST was a todo action.
    """
    action = request.POST.get('action')
    if action not in ('create', 'edit', 'delete', 'reorder'):
        return False
    if action == 'create':
        description = request.POST.get('description', '').strip()
        owner_id = request.POST.get('parent', '').strip()
        if owner_id:
            owner = Parent.objects.filter(pk=owner_id).first()
        else:
            owner = parent
        horizon, horizon_date = _posted_horizon_date(request)
        if (
            description
            and owner is not None
            and _parent_in_program_scope(owner.id, parent)
            and horizon_date is not None
        ):
            activity = _activity_for_parent(
                request.POST.get('activity', '').strip(), owner.id
            )
            ToDoItem.objects.create(
                parent=owner,
                description=description,
                activity=activity,
                horizon=horizon,
                horizon_date=horizon_date,
                status=ToDoItem.Status.OPEN,
                sort_order=_next_sort_order(horizon, horizon_date),
                program_order=_next_program_order(),
                note=request.POST.get('note', ''),
            )
        return True
    if action == 'reorder':
        _handle_program_reorder(request, parent)
        return True
    item = ToDoItem.objects.filter(pk=request.POST.get('item_id')).first()
    if item is None or not _todo_in_program_scope(item, parent):
        return True
    if action == 'delete':
        item.delete()
        return True
    description = request.POST.get('description', '').strip()
    if not description:
        return True
    horizon, horizon_date = _posted_horizon_date(request)
    if horizon_date is None:
        return True
    owner_id = request.POST.get('parent', '').strip()
    if owner_id:
        owner = Parent.objects.filter(pk=owner_id).first()
    else:
        owner = item.parent
    if owner is None or not _parent_in_program_scope(owner.id, parent):
        return True
    activity = _activity_for_parent(
        request.POST.get('activity', '').strip(), owner.id
    )
    update_fields = ['parent', 'description', 'activity', 'note']
    item.parent = owner
    item.description = description
    item.activity = activity
    item.note = request.POST.get('note', '')
    if item.horizon != horizon or item.horizon_date != horizon_date:
        item.horizon = horizon
        item.horizon_date = horizon_date
        item.sort_order = _next_sort_order(horizon, horizon_date)
        update_fields.extend(['horizon', 'horizon_date', 'sort_order'])
    item.save(update_fields=update_fields)
    return True


def program_todo_redirect(request, parent_id):
    """Stay on the program editor after a todo POST, preserving query string."""
    nxt = request.POST.get('next', '')
    if nxt.startswith('/timsy/programs/'):
        return nxt
    return reverse('program_editor', args=[parent_id])


def plan_todo_sidebar_context(request, plan_date):
    """Template context for the day-horizon todo sidebar on a daily plan.

    Columns are that date and the next calendar day (open and done). Move
    and drag use those same two days, matching the daily todo list.
    """
    today = local_today()
    tomorrow = plan_date + timedelta(days=1)
    columns = [
        _build_column(ToDoItem.Horizon.DAY, plan_date, today),
        _build_column(ToDoItem.Horizon.DAY, tomorrow, today),
    ]
    return _list_context(request, '', columns, None, None)


def handle_plan_todo_post(request):
    """Handle a todo sidebar POST from a daily plan page.

    Returns True if this POST was a todo action.
    """
    if request.POST.get('action') not in TODO_ACTIONS:
        return False
    _handle_post(request)
    return True


def plan_todo_redirect(request, year, month, day, edit=False):
    """Stay on the daily plan view or edit page after a todo POST."""
    nxt = request.POST.get('next', '')
    if nxt.startswith('/timsy/data/plans/daily/'):
        return nxt
    if edit:
        return reverse('daily_plan_edit', args=[year, month, day])
    return reverse('daily_plan_view', args=[year, month, day])

