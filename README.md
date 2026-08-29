# Timsy - Time Management System

Timsy is a Django-based time management and activity tracking system designed to help users track, analyze, and optimize their time usage.

## Features

- Activity tracking with importance and urgency levels, and optional notes per record
- Location-based time tracking
- Comprehensive reporting system:
  - Daily logs
  - Weekly summaries
  - Monthly summaries
  - Plan-vs-fact comparisons (daily and weekly)
  - Custom date range reports
- Daily plans, built from reusable blueprints, with active/inactive filtering
- Programs: versioned, free-text planning docs per parent category
- Parent-Child activity organization

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
- `Activity`: Individual tasks with importance and urgency levels
- `ActivityRecord`: Records of when activities were performed, with an optional note
- `Parent`: High-level categories for activities
- `Importance`: Classification of activity importance
- `Urgency`: Classification of activity urgency
- `Place`: Different locations where activities can occur
- `DailyPlan` / `DailyPlanEntry`: A plan of activities for a specific date; plans can be marked active/inactive
- `Blueprint` / `BlueprintEntry`: Reusable templates for building daily plans
- `Program`: A versioned, free-text planning document for a parent category

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
4. Plan your day using daily plans, optionally seeded from a blueprint

## API Endpoints

### Reports
- `GET /timsy/reports/log/<year>/<month>/<day>/`: Daily log
- `GET /timsy/reports/log/latest/`: Most recent daily log
- `GET /timsy/reports/summary/daily/<parent>/<year>/<month>/<day>/`: Daily summary
- `GET /timsy/reports/summary/daily/latest/`: Most recent daily summary
- `GET /timsy/reports/summary/weekly/<parent>/<year>/<month>/<day>/`: Weekly summary
- `GET /timsy/reports/summary/weekly/latest/`: Most recent weekly summary
- `GET /timsy/reports/summary/my_weekly/latest/`: Most recent personal weekly summary
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
- `GET /timsy/parents/top/`: Top-level parent list

### Daily Plans
- `GET /timsy/data/plans/daily/`: Daily plan list (active only by default; `?show=all` for all)
- `GET/POST /timsy/data/plans/daily/create/`: Create a daily plan
- `GET /timsy/data/plans/daily/<year>/<month>/<day>/`: View a daily plan
- `GET/POST /timsy/data/plans/daily/<year>/<month>/<day>/edit/`: Edit a daily plan
- `GET /timsy/data/plans/daily/<year>/<month>/<day>/toggle-active/`: Toggle a plan's active flag

### Blueprints
- `GET /timsy/blueprints/`: Blueprint list
- `GET /timsy/blueprints/<id>/`: Blueprint detail
- `GET/POST /timsy/blueprints/<id>/edit/`: Edit a blueprint
- `GET /timsy/api/blueprints/<blueprint_id>/entries/`: Blueprint entries (JSON)

### Programs
- `GET /timsy/programs/parents/top/`: Top-level parent list (Programs entry point)
- `GET/POST /timsy/programs/<parent_id>/`: View, edit, or clone a parent's program

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License.
