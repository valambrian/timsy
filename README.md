# Timsy - Time Management System

Timsy is a Django-based time management and activity tracking system designed to help users track, analyze, and optimize their time usage.

## Features

- Activity tracking with importance and urgency levels
- Location-based time tracking
- Comprehensive reporting system:
  - Daily logs
  - Weekly summaries
  - Monthly summaries
  - Custom date range reports
- Calendar view for activity planning
- Ideal day template system
- Parent-Child activity organization

## Project Structure

```
vgsite/
├── timsy/                 # Main application
│   ├── models.py         # Data models
│   ├── views.py          # View logic
│   ├── urls.py           # URL routing
│   ├── templates/        # HTML templates
│   ├── static/          # Static files (CSS, JS)
│   └── migrations/      # Database migrations
├── vgsite/              # Project settings
│   ├── settings.py      # Project configuration
│   ├── urls.py          # Main URL routing
│   └── wsgi.py         # WSGI configuration
└── manage.py            # Django management script
```

## Data Models

### Core Models
- `Activity`: Individual tasks with importance and urgency levels
- `ActivityRecord`: Records of when activities were performed
- `Parent`: High-level categories for activities
- `Importance`: Classification of activity importance
- `Urgency`: Classification of activity urgency
- `Place`: Different locations where activities can occur
- `IdealDayTemplate`: Templates for planning ideal daily schedules

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Usage

1. Access the main interface at `http://localhost:8000/timsy/`
2. Use the activity log to record your activities
3. View reports and summaries through the reporting interface
4. Plan your ideal day using the template system

## API Endpoints

### Activity Management
- `GET /timsy/requests/last/`: Get the last activity record
- `GET /timsy/requests/activity/<abbreviation>/`: Get activity details

### Reports
- `GET /timsy/reports/log/<year>/<month>/<day>/`: Daily log
- `GET /timsy/reports/summary/daily/<parent>/<year>/<month>/<day>/`: Daily summary
- `GET /timsy/reports/summary/weekly/<parent>/<year>/<month>/<day>/`: Weekly summary
- `GET /timsy/reports/summary/monthly/<parent>/<year>/<month>/<day>/`: Monthly summary

### Data Entry
- `GET /timsy/data/log/`: Activity log entry interface
- `GET /timsy/data/calendar/`: Calendar view
- `GET /timsy/data/idts/`: Ideal day template list

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 