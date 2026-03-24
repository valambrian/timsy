from datetime import timedelta, date
from typing import Dict, List, Any
from django.db import connection

from ..models import Place
from .utils import seconds_to_string
from .queries.fact_queries import get_parent_fact_daily_breakdown_query, get_activity_fact_daily_breakdown_query


class DailyBreakdownSummaryRecord:
    """
    A class to represent a summary record with daily breakdown of activities.
    
    This class is used to aggregate and summarize activity records by both date and place,
    providing methods to add time spent and retrieve formatted summaries.
    """
    
    def __init__(self, id: str, description: str, dates_lookup: Dict[str, int], places_lookup: Dict[str, int]) -> None:
        """
        Initialize a DailyBreakdownSummaryRecord.
        
        Args:
            id: The ID of the record
            description: The description of the record
            dates_lookup: Dictionary mapping date strings to their indices
            places_lookup: Dictionary mapping place IDs to their indices
        """
        self.id = id
        self.description = description
        self.dates_lookup = dates_lookup
        self.places_lookup = places_lookup
        self.times_by_date: Dict[str, int] = {}  # Dictionary to store time spent per date
        self.times_by_place: Dict[str, int] = {}  # Dictionary to store time spent per place

    def add(self, date: str, place: str, seconds: int) -> None:
        """
        Add time spent at a place on a specific date to the summary.
        
        Args:
            date: The date in YYYY-MM-DD format
            place: The place ID
            seconds: Number of seconds spent
        """
        # Add to date breakdown
        if date in self.times_by_date:
            self.times_by_date[date] += seconds
        else:
            self.times_by_date[date] = seconds
            
        # Add to place breakdown
        if place in self.times_by_place:
            self.times_by_place[place] += seconds
        else:
            self.times_by_place[place] = seconds

    def get_times(self) -> List[str]:
        """
        Get a formatted summary of time spent by date and place.
        
        Returns:
            List of formatted time strings in order:
                 1. Time spent per date (in order of dates_lookup)
                 2. Time spent per place (in order of places_lookup)
                 3. Total time spent
        """
        result = []
        total = 0
        
        # Add times by date
        for date in sorted(self.dates_lookup.keys()):
            seconds = self.times_by_date.get(date, 0)
            total += seconds
            result.append(seconds_to_string(seconds))
            
        # Add times by place
        for place in self.places_lookup.keys():
            seconds = self.times_by_place.get(place, 0)
            result.append(seconds_to_string(seconds))
            
        # Add total
        result.append(seconds_to_string(total))
        return result

    @classmethod
    def get_records(cls, parent: str, start_date: date, end_date: date) -> List['DailyBreakdownSummaryRecord']:
        """Get daily breakdown records for a specified period.
        
        Retrieves and aggregates activity records by date and place for the given date range.
        Uses separate optimized queries for better performance.
        
        Args:
            parent: Parent activity filter ('ALL' for all activities)
            start_date: Start date of the report period
            end_date: End date of the report period
            
        Returns:
            List of DailyBreakdownSummaryRecord objects containing aggregated time data
        """
        cursor = connection.cursor()
        if parent == "ALL":
            parent_pattern = "__"
        else:
            parent_pattern = "%s-__" % (parent,)
        start_date_pattern = start_date.strftime("%Y-%m-%d")
        end_date_pattern = end_date.strftime("%Y-%m-%d")

        days = (end_date - start_date).days + 1
        dates = [None] * days
        dates_lookup = {}
        for i in range(days):
            date = start_date + timedelta(days=i)
            dates_lookup[date.strftime("%Y-%m-%d")] = i
            dates[i] = date.strftime("%A, %m/%d")

        places = Place.get_abbreviations()
        places_lookup = {}
        for i in range(len(places)):
            places_lookup[places[i]] = i

        # Execute separate queries for better performance
        parent_query = get_parent_fact_daily_breakdown_query(parent_pattern, start_date_pattern, end_date_pattern)
        cursor.execute(parent_query, [parent_pattern, start_date_pattern, end_date_pattern])
        parent_rows = cursor.fetchall()

        activity_query = get_activity_fact_daily_breakdown_query(parent, start_date_pattern, end_date_pattern)
        cursor.execute(activity_query, [parent, start_date_pattern, end_date_pattern])
        activity_rows = cursor.fetchall()

        # Convert rows to dictionaries for easier handling
        parent_results = []
        for row in parent_rows:
            parent_results.append({
                'parent_order': row[0],
                'activity_order': row[1],
                'id': row[2],
                'description': row[3],
                'importance': row[4],
                'date': row[5],
                'place_id': row[6],
                'total_seconds': row[7]
            })

        activity_results = []
        for row in activity_rows:
            activity_results.append({
                'parent_order': row[0],
                'activity_order': row[1],
                'id': row[2],
                'description': row[3],
                'importance': row[4],
                'date': row[5],
                'place_id': row[6],
                'total_seconds': row[7]
            })

        # Combine and sort results
        combined_rows = list(parent_results) + list(activity_results)
        
        # Sort by activity_order (NULLs first), then parent_order, then date
        def sort_key(row):
            date = row.get('date')
            activity_order = row.get('activity_order')
            parent_order = row.get('parent_order')
            
            # NULLs should come first for activity_order, last for parent_order
            activity_sort = (0, 0) if activity_order is None else (1, activity_order)
            parent_sort = (1, 0) if parent_order is None else (0, parent_order)
            
            return (activity_sort, parent_sort, date)
        
        combined_rows = sorted(combined_rows, key=sort_key)

        # Process combined results into DailyBreakdownSummaryRecord objects
        records = []
        records_lookup = {}
        total_record = DailyBreakdownSummaryRecord(id="", description="Total", dates_lookup=dates_lookup,
                                                   places_lookup=places_lookup)
        
        for row in combined_rows:
            id = row['id']
            description = row['description']
            date = row['date'].strftime("%Y-%m-%d") if hasattr(row['date'], 'strftime') else str(row['date'])
            place = row['place_id']
            seconds = row['total_seconds']
            
            if description not in records_lookup:
                records_lookup[description] = len(records)
                records.append(DailyBreakdownSummaryRecord(id=id, description=description, dates_lookup=dates_lookup,
                                                           places_lookup=places_lookup))
            record = records[records_lookup[description]]
            record.add(date, place, seconds)
            total_record.add(date, place, seconds)
            
        records.append(total_record)
        return records