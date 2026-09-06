# Timsy - Time Management System

Timsy is a Django-based time management and activity tracking system designed to help users track, analyze, and optimize their time usage.

## Features

- Activity tracking with importance and urgency levels, optional notes per record, and a placeholder flag for time-bucket slots
- Location-based time tracking
- Comprehensive reporting system:
  - Daily logs
  - Weekly summaries (configurable week start), monthly summaries
  - Plan-vs-fact comparisons (daily and weekly), with shared free-text review notes
  - Custom date range reports
- Daily plans, built from reusable blueprints, with active/inactive filtering
- Blueprints can declare a recurring schedule (weekdays, interval, anchor date) so only matching ones are offered per day, plus creation and cloning
- Weekly hour budgets by parent, with remaining-hours shown on the daily plan editor
- Programs: versioned, free-text planning docs per parent category
- ToDoItem queues per parent, worked at year/month/week/day horizons from Programs or the daily plan view
- A pomodoro timer embedded in today's daily plan view, with current-row highlighting
- Parent-Child activity organization, with an inline editor and a pending/active/paused/completed/cancelled lifecycle state

## Project Structure

```
timsy/                    # Repo root
├── timsy/                 # Main application
│   ├── models/            # Data models
│   ├── views/              # View logic
│   ├── reports/            # Report-building logic
│   ├── urls.py             # URL routing
│   ├── templates/          # HTML templates
│   ├── static/              # Static files (CSS, JS)
│   ├── templatetags/        # Custom template tags
│   └── migrations/          # Database migrations
├── vgsite/                 # Project settings
│   ├── settings.py          # Project configuration
│   ├── urls.py               # Main URL routing
│   └── wsgi.py                # WSGI configuration
└── manage.py                 # Django management script
```

## Data Models

### Core Models
- `Activity`: Individual tasks with importance and urgency levels, and an `is_placeholder` flag for time-bucket slots
- `ActivityRecord`: Records of when activities were performed, with an optional note
- `Parent`: High-level categories for activities, with a pending/active/paused/completed/cancelled lifecycle state
- `Importance`: Classification of activity importance
- `Urgency`: Classification of activity urgency
- `Place`: Different locations where activities can occur
- `DailyPlan` / `DailyPlanEntry`: A plan of activities for a specific date; plans can be marked active/inactive and carry a review note
- `Blueprint` / `BlueprintEntry`: Reusable templates for building daily plans, with an optional recurring schedule (weekdays, interval, anchor date)
- `Program`: A versioned, free-text planning document for a parent category
- `ToDoItem`: A work-queue item scoped to a parent, tracked at a year/month/week/day horizon
- `WeeklyPlan` / `WeeklyPlanAllocation`: An hour budget per parent for a given week, with a shared review note

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in `SECRET_KEY` and `DB_PASSWORD` (and any other DB settings that differ from the defaults)
5. Run migrations:
   ```bash
   python manage.py migrate
   ```
6. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Usage

1. Access the main interface at `http://localhost:8000/timsy/`
2. Use the activity log to record your activities
3. View reports and summaries through the reporting interface
4. Plan your day using daily plans, optionally seeded from a blueprint (with a pomodoro timer on today's plan)
5. Set an hour budget per parent for the week using Weekly Plans
6. Track a parent's work queue at year/month/week/day horizons using ToDo Queues, from Programs or the daily plan view

## API Endpoints

### Reports
- `GET /timsy/reports/log/<year>/<month>/<day>/`: Daily log
- `GET /timsy/reports/log/latest/`: Most recent daily log
- `GET /timsy/reports/summary/daily/<parent>/<year>/<month>/<day>/`: Daily summary
- `GET /timsy/reports/summary/daily/latest/`: Most recent daily summary
- `GET /timsy/reports/summary/weekly/<parent>/<year>/<month>/<day>/`: Weekly summary
- `GET /timsy/reports/summary/weekly/latest/`: Most recent weekly summary (week starts on `TIMSY_WEEK_START_DAY`)
- `GET /timsy/reports/summary/monthly/<parent>/<year>/<month>/<day>/`: Monthly summary
- `GET /timsy/reports/summary/monthly/latest/`: Most recent monthly summary
- `GET /timsy/reports/summary/daily_week_breakdown/<parent>/<year>/<month>/<day>/`: Daily/weekly breakdown
- `GET /timsy/reports/summary/daily_week_breakdown/latest/`: Most recent daily/weekly breakdown
- `GET /timsy/reports/summary/<parent>/<from_year>/<from_month>/<from_day>/<to_year>/<to_month>/<to_day>/`: Custom date range summary
- `GET /timsy/reports/plan-vs-fact/daily/<parent>/<year>/<month>/<day>/`: Daily plan-vs-fact report
- `GET /timsy/reports/plan-vs-fact/daily/latest/`: Most recent daily plan-vs-fact report
- `GET /timsy/reports/plan-vs-fact/weekly/<parent>/<year>/<month>/<day>/`: Weekly plan-vs-fact report
- `GET /timsy/reports/plan-vs-fact/weekly/latest/`: Most recent weekly plan-vs-fact report

### Activity Management
- `GET /timsy/data/activities/last/`: Get the last activity record
- `GET /timsy/data/activities/<abbreviation>/`: Get activity details
- `GET/POST /timsy/data/entry_log/`: Activity log entry interface
- `GET /timsy/activities/<parent_id>/`: Activity editor
- `GET /timsy/parents/top/`: Top-level parent list; also creates/updates top-level parents (POST)
- `POST /timsy/parents/<parent_id>/set-state/`: Set a parent's lifecycle state
- `GET/POST /timsy/parents/<parent_id>/`: Create/update a parent's direct child categories

### Daily Plans
- `GET /timsy/data/plans/daily/`: Daily plan list (active only by default; `?show=all` for all)
- `GET/POST /timsy/data/plans/daily/create/`: Create a daily plan
- `GET /timsy/data/plans/daily/<year>/<month>/<day>/`: View a daily plan
- `GET/POST /timsy/data/plans/daily/<year>/<month>/<day>/edit/`: Edit a daily plan
- `GET /timsy/data/plans/daily/<year>/<month>/<day>/toggle-active/`: Toggle a plan's active flag

### Weekly Plans
- `GET /timsy/data/plans/weekly/`: Weekly plan list
- `GET /timsy/data/plans/weekly/latest/`: Most recent configured week
- `GET/POST /timsy/data/plans/weekly/<year>/<month>/<day>/`: View/edit an hour budget per parent, or clone the prior week

### Blueprints
- `GET /timsy/blueprints/`: Blueprint list (active only by default; `?show=all` for all)
- `GET/POST /timsy/blueprints/create/`: Create a blueprint (name plus optional schedule)
- `GET /timsy/blueprints/<id>/toggle-active/`: Toggle a blueprint's active flag
- `GET/POST /timsy/blueprints/<id>/clone/`: Clone a blueprint's entries and schedule
- `GET /timsy/blueprints/<id>/`: Blueprint detail
- `GET/POST /timsy/blueprints/<id>/edit/`: Edit a blueprint
- `GET /timsy/api/blueprints/<blueprint_id>/entries/`: Blueprint entries (JSON)

### Programs
- `GET /timsy/programs/parents/top/`: Top-level parent list (Programs entry point)
- `GET/POST /timsy/programs/<parent_id>/`: View, edit, or clone a parent's program; also creates/edits/deletes/reorders that parent's todos

### ToDo Queues
- `GET /timsy/todos/today/`, `this-week/`, `this-month/`, `this-year/`: Redirect to the matching dated list below, relative to today
- `GET/POST /timsy/todos/daily/<year>/<month>/<day>/`, `weekly/<year>/<month>/<day>/`, `monthly/<year>/<month>/`, `yearly/<year>/`: Todos due for a specific period; also creates/edits/deletes/reorders/moves todos

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License.
