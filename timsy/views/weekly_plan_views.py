from datetime import date, timedelta

from django.shortcuts import render, redirect
from django.urls import reverse

from ..models import Parent, Program, WeeklyPlan, WeeklyPlanAllocation
from ..models.weekly_plan import WEEK_SECONDS
from ..reports.utils import (
    local_today,
    parse_hhmm_to_seconds,
    seconds_to_hhmm,
    week_start_for,
)


EXTRA_EMPTY_ROWS = 3


def _week_edit_url(week_start):
    """Return the editor URL for a week start date.

    Args:
        week_start: First day of the week

    Returns:
        str: Path to the weekly plan editor
    """
    return reverse(
        'weekly_plan_edit',
        args=[week_start.year, week_start.month, week_start.day],
    )


def _latest_programs_by_parent(parent_ids):
    """Return the newest program for each parent id.

    Args:
        parent_ids: Parent primary keys to look up

    Returns:
        dict: parent id to Program
    """
    programs = {}
    if not parent_ids:
        return programs
    for program in Program.objects.filter(parent_id__in=parent_ids).order_by(
        'parent_id', '-timestamp'
    ):
        if program.parent_id not in programs:
            programs[program.parent_id] = program
    return programs


def _parent_choices():
    """Return active parents as (id, description) for extra allocation rows.

    Returns:
        list: Choice tuples
    """
    return Parent.get_active_choices()


def _hierarchy_order():
    """Return a parent id to hierarchy-position map.

    Returns:
        dict: parent id to integer order
    """
    return {
        parent.id: index
        for index, parent in enumerate(Parent._in_hierarchy_order())
    }


def _build_rows(week_start, weekly_plan):
    """Build editor rows with budget, scheduled, remaining, and fact.

    Rows are parents with a non-zero budget, scheduled time, or last-week fact.

    Args:
        week_start: First day of the week
        weekly_plan: Saved WeeklyPlan or None

    Returns:
        tuple: (rows, totals dict)
    """
    order = _hierarchy_order()
    parents_by_id = {}
    budgets = {}
    if weekly_plan:
        for allocation in weekly_plan.get_allocations():
            if not allocation.seconds:
                continue
            parents_by_id[allocation.parent_id] = allocation.parent
            budgets[allocation.parent_id] = allocation.seconds

    scratch = WeeklyPlan(week_start=week_start)
    missing_ids = (
        scratch.parent_ids_with_scheduled() | scratch.parent_ids_with_fact()
    ) - set(parents_by_id)
    if missing_ids:
        for parent in Parent.objects.filter(pk__in=missing_ids).select_related(
            'importance'
        ):
            parents_by_id[parent.id] = parent

    parents = list(parents_by_id.values())
    parent_ids = [parent.id for parent in parents]
    scheduled = scratch.scheduled_seconds(parent_ids)
    fact = scratch.fact_seconds(parent_ids)
    programs = _latest_programs_by_parent(parent_ids)

    rows = []
    total_budget = 0
    total_scheduled = 0
    total_fact = 0
    for parent in parents:
        budget_seconds = budgets.get(parent.id)
        scheduled_seconds = scheduled.get(parent.id, 0)
        fact_seconds = fact.get(parent.id, 0)
        if budget_seconds is None:
            remaining_seconds = None
            budget_display = ''
            remaining_display = ''
        else:
            remaining_seconds = budget_seconds - scheduled_seconds
            budget_display = seconds_to_hhmm(budget_seconds)
            remaining_display = seconds_to_hhmm(remaining_seconds)
            total_budget += budget_seconds
        total_scheduled += scheduled_seconds
        total_fact += fact_seconds
        program = programs.get(parent.id)
        rows.append({
            'parent': parent,
            'parent_id': parent.id,
            'description': parent.description,
            'importance': parent.importance.description,
            'program': program,
            'budget': budget_display,
            'scheduled': seconds_to_hhmm(scheduled_seconds),
            'remaining': remaining_display,
            'fact': seconds_to_hhmm(fact_seconds),
        })

    rows.sort(key=lambda row: (order.get(row['parent_id'], 10 ** 9), row['parent_id']))

    for _ in range(EXTRA_EMPTY_ROWS):
        rows.append({
            'parent': None,
            'parent_id': '',
            'description': '',
            'importance': '',
            'program': None,
            'budget': '',
            'scheduled': '',
            'remaining': '',
            'fact': '',
        })

    totals = {
        'budget': seconds_to_hhmm(total_budget) if budgets else '',
        'scheduled': seconds_to_hhmm(total_scheduled),
        'remaining': (
            seconds_to_hhmm(total_budget - total_scheduled) if budgets else ''
        ),
        'fact': seconds_to_hhmm(total_fact),
        'budget_seconds': total_budget,
        'week_seconds': WEEK_SECONDS,
        'week_hhmm': seconds_to_hhmm(WEEK_SECONDS),
        'matches_week': bool(budgets) and total_budget == WEEK_SECONDS,
    }
    return rows, totals


def _save_allocations(request, weekly_plan):
    """Rebuild allocations from posted hours rows.

    Args:
        request: HTTP request with parent and hours fields
        weekly_plan: WeeklyPlan to replace allocations on
    """
    weekly_plan.allocations.all().delete()
    seen = set()
    index = 0
    empty_streak = 0
    while empty_streak < EXTRA_EMPTY_ROWS + 2:
        parent_id = (request.POST.get('parent%d' % index) or '').strip()
        hours = request.POST.get('hours%d' % index)
        hours_text = '' if hours is None else str(hours).strip()
        if not parent_id and not hours_text:
            empty_streak += 1
            index += 1
            continue
        empty_streak = 0
        if not parent_id:
            index += 1
            continue
        seconds = parse_hhmm_to_seconds(hours_text)
        if seconds is None:
            index += 1
            continue
        if parent_id in seen:
            index += 1
            continue
        parent = Parent.objects.filter(pk=parent_id).first()
        if parent is None:
            index += 1
            continue
        WeeklyPlanAllocation.objects.create(
            weekly_plan=weekly_plan,
            parent=parent,
            seconds=seconds,
        )
        seen.add(parent_id)
        index += 1


def weekly_plan_list(request):
    """List weekly plans, with this week first even if it has no row yet."""
    today = local_today()
    this_week = week_start_for(today)
    plans = list(WeeklyPlan.objects.order_by('-week_start'))
    this_week_plan = next((plan for plan in plans if plan.week_start == this_week), None)
    other_plans = [plan for plan in plans if plan.week_start != this_week]
    return render(request, 'weekly_plan_list.html', {
        'this_week': this_week,
        'this_week_plan': this_week_plan,
        'plans': other_plans,
    })


def weekly_plan_latest(request):
    """Redirect to the weekly plan for the week that contains today."""
    start = week_start_for(local_today())
    return redirect(_week_edit_url(start))


def weekly_plan_edit(request, year, month, day):
    """View and save a week's hour budget and analysis note.

    GET: Shows allocations with scheduled, remaining, and fact.
    POST action=save: Writes note and allocations.
    POST action=clone: Copies the previous week's allocations.
    """
    requested = date(year, month, day)
    week_start = week_start_for(requested)
    if requested != week_start:
        return redirect(_week_edit_url(week_start))

    weekly_plan = WeeklyPlan.for_week_start(week_start)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'clone':
            source = WeeklyPlan.previous_before(week_start)
            if source is not None:
                if weekly_plan is None:
                    weekly_plan = WeeklyPlan.objects.create(week_start=week_start)
                weekly_plan.clone_allocations_from(source)
            return redirect(_week_edit_url(week_start))
        if weekly_plan is None:
            weekly_plan = WeeklyPlan.objects.create(week_start=week_start)
        weekly_plan.note = request.POST.get('note', weekly_plan.note)
        weekly_plan.save(update_fields=['note'])
        if action != 'save_note':
            _save_allocations(request, weekly_plan)
        return redirect(_week_edit_url(week_start))

    rows, totals = _build_rows(week_start, weekly_plan)
    previous_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    previous_plan = WeeklyPlan.previous_before(week_start)
    return render(request, 'weekly_plan_edit.html', {
        'week_start': week_start,
        'week_end': week_start + timedelta(days=6),
        'weekly_plan': weekly_plan,
        'rows': rows,
        'totals': totals,
        'parent_choices': _parent_choices(),
        'previous_week': previous_week,
        'next_week': next_week,
        'previous_plan': previous_plan,
    })
