from datetime import date, timedelta
from typing import Dict, List, Any
from django.db import connection

from ..models import Place
from .utils import seconds_to_string
from .queries.fact_queries import get_parent_fact_daily_breakdown_query, get_activity_fact_daily_breakdown_query
from .queries.plan_queries import get_parent_plan_daily_breakdown_query, get_activity_plan_daily_breakdown_query


class PlanVsFactWeeklyRecord:
    """
    A class to represent a weekly plan-vs-fact record with daily and place breakdown.
    
    This class aggregates and compares planned vs actual time spent by both date and place,
    providing methods to add time data and retrieve formatted summaries.
    """
    
    def __init__(self, id: str, description: str, importance: str, dates_lookup: Dict[str, int], places_lookup: Dict[str, int]) -> None:
        """
        Initialize a PlanVsFactWeeklyRecord.
        
        Args:
            id: The ID of the record
            description: The description of the record
            importance: The importance level description
            dates_lookup: Dictionary mapping date strings to their indices
            places_lookup: Dictionary mapping place IDs to their indices
        """
        self.id = id
        self.description = description
        self.importance = importance
        self.dates_lookup = dates_lookup
        self.places_lookup = places_lookup
        self.plan_seconds_by_date_place = {}  # {(date, place): seconds}
        self.fact_seconds_by_date_place = {}  # {(date, place): seconds}

    def add_plan_time(self, date: str, place: str, seconds: int) -> None:
        """
        Add planned time for a specific date and place.
        
        Args:
            date: The date in YYYY-MM-DD format
            place: The place ID
            seconds: Number of seconds planned
        """
        key = (date, place)
        if key in self.plan_seconds_by_date_place:
            self.plan_seconds_by_date_place[key] += seconds
        else:
            self.plan_seconds_by_date_place[key] = seconds

    def add_fact_time(self, date: str, place: str, seconds: int) -> None:
        """
        Add actual time for a specific date and place.
        
        Args:
            date: The date in YYYY-MM-DD format
            place: The place ID
            seconds: Number of seconds actually spent
        """
        key = (date, place)
        if key in self.fact_seconds_by_date_place:
            self.fact_seconds_by_date_place[key] += seconds
        else:
            self.fact_seconds_by_date_place[key] = seconds

    def get_times(self, places_filter: List[str] = None) -> List[str]:
        """
        Get formatted time strings for all dates and places in order.
        
        Args:
            places_filter: Optional list of place abbreviations to include. 
                          If None, includes all places.
        
        Returns:
            List of formatted time strings in order:
                For each date: [plan, fact, difference]
                For each place in places_filter: [plan, fact, difference]
                Then: [total_plan, total_fact, total_difference]
        """
        result = []
        total_plan_seconds = 0
        total_fact_seconds = 0
        
        # Use filtered places or all places
        places_to_include = places_filter if places_filter is not None else list(self.places_lookup.keys())
        
        # Add times by date
        for date in sorted(self.dates_lookup.keys()):
            date_plan_seconds = 0
            date_fact_seconds = 0
            
            for place in self.places_lookup.keys():  # Still check all places for date totals
                key = (date, place)
                plan_seconds = self.plan_seconds_by_date_place.get(key, 0)
                fact_seconds = self.fact_seconds_by_date_place.get(key, 0)
                date_plan_seconds += plan_seconds
                date_fact_seconds += fact_seconds
            
            total_plan_seconds += date_plan_seconds
            total_fact_seconds += date_fact_seconds
            
            result.append(seconds_to_string(date_plan_seconds))
            result.append(seconds_to_string(date_fact_seconds))
            result.append(seconds_to_string(date_fact_seconds - date_plan_seconds))
        
        # Add times by place (only for filtered places)
        for place in places_to_include:
            place_plan_seconds = 0
            place_fact_seconds = 0
            
            for date in self.dates_lookup.keys():
                key = (date, place)
                place_plan_seconds += self.plan_seconds_by_date_place.get(key, 0)
                place_fact_seconds += self.fact_seconds_by_date_place.get(key, 0)
            
            result.append(seconds_to_string(place_plan_seconds))
            result.append(seconds_to_string(place_fact_seconds))
            result.append(seconds_to_string(place_fact_seconds - place_plan_seconds))
        
        # Add totals
        result.append(seconds_to_string(total_plan_seconds))
        result.append(seconds_to_string(total_fact_seconds))
        result.append(seconds_to_string(total_fact_seconds - total_plan_seconds))
        
        return result

    @classmethod
    def get_records(cls, parent: str, start_date: date, end_date: date) -> List['PlanVsFactWeeklyRecord']:
        """Get weekly plan-vs-fact records for a specified period.
        
        Retrieves and aggregates both plan and fact data by date and place for the given date range.
        Uses separate optimized queries for better performance.
        
        Args:
            parent: Parent activity filter ('ALL' for all activities)
            start_date: Start date of the report period
            end_date: End date of the report period
            
        Returns:
            List of PlanVsFactWeeklyRecord objects containing aggregated plan vs fact data
        """
        cursor = connection.cursor()
        if parent == "ALL":
            parent_pattern = "__"
        else:
            parent_pattern = "%s-__" % (parent,)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Create date and place lookups
        days = (end_date - start_date).days + 1
        dates_lookup = {}
        for i in range(days):
            date = start_date + timedelta(days=i)
            dates_lookup[date.strftime("%Y-%m-%d")] = i

        places = Place.get_abbreviations()
        places_lookup = {}
        for i in range(len(places)):
            places_lookup[places[i]] = i

        # Execute plan queries
        parent_plan_query = get_parent_plan_daily_breakdown_query(parent_pattern, start_date_str, end_date_str)
        cursor.execute(parent_plan_query, [parent_pattern, start_date_str, end_date_str])
        parent_plan_rows = cursor.fetchall()

        activity_plan_query = get_activity_plan_daily_breakdown_query(parent, start_date_str, end_date_str)
        cursor.execute(activity_plan_query, [parent, start_date_str, end_date_str])
        activity_plan_rows = cursor.fetchall()

        # Execute fact queries
        parent_fact_query = get_parent_fact_daily_breakdown_query(parent_pattern, start_date_str, end_date_str)
        cursor.execute(parent_fact_query, [parent_pattern, start_date_str, end_date_str])
        parent_fact_rows = cursor.fetchall()

        activity_fact_query = get_activity_fact_daily_breakdown_query(parent, start_date_str, end_date_str)
        cursor.execute(activity_fact_query, [parent, start_date_str, end_date_str])
        activity_fact_rows = cursor.fetchall()

        # Convert rows to dictionaries for easier handling
        plan_data = {}  # {description: {(date, place): seconds}}
        fact_data = {}  # {description: {(date, place): seconds}}
        sort_keys = {}  # {description: (parent_order, activity_order)}
        id_lookup = {}  # {description: id}
        importance_lookup = {}  # {description: importance}

        # Process plan data
        for row in parent_plan_rows + activity_plan_rows:
            parent_order = row[0]
            activity_order = row[1]
            id_value = row[2]
            description = row[3]
            importance = row[4]
            date = row[5].strftime("%Y-%m-%d") if hasattr(row[5], 'strftime') else str(row[5])
            place_id = row[6]
            seconds = row[7]
            
            if description not in plan_data:
                plan_data[description] = {}
            key = (date, place_id)
            plan_data[description][key] = plan_data[description].get(key, 0) + seconds
            
            sort_keys[description] = (parent_order, activity_order)
            id_lookup[description] = id_value
            importance_lookup[description] = importance

        # Process fact data
        for row in parent_fact_rows + activity_fact_rows:
            parent_order = row[0]
            activity_order = row[1]
            id_value = row[2]
            description = row[3]
            importance = row[4]
            date = row[5].strftime("%Y-%m-%d") if hasattr(row[5], 'strftime') else str(row[5])
            place_id = row[6]
            seconds = row[7]
            
            if description not in fact_data:
                fact_data[description] = {}
            key = (date, place_id)
            fact_data[description][key] = fact_data[description].get(key, 0) + seconds
            
            sort_keys[description] = (parent_order, activity_order)
            id_lookup[description] = id_value
            importance_lookup[description] = importance

        # Create PlanVsFactWeeklyRecord objects
        records = []
        records_lookup = {}
        total_record = PlanVsFactWeeklyRecord(id="", description="Total", importance="", dates_lookup=dates_lookup, places_lookup=places_lookup)

        # Get all unique descriptions from both plan and fact data
        all_descriptions = set(plan_data.keys()) | set(fact_data.keys())
        
        # Sort descriptions by parent_order first (nulls last), then by activity_order
        def sort_key(description):
            parent_order, activity_order = sort_keys[description]
            if parent_order is not None:
                # Parent record: sort by parent_order, put before activities
                return (0, parent_order, 0)
            else:
                # Activity record: sort by activity_order, put after parents
                return (1, 0, activity_order)
        
        for description in sorted(all_descriptions, key=sort_key):
            if description not in records_lookup:
                records_lookup[description] = len(records)
                record_id = id_lookup[description]
                records.append(PlanVsFactWeeklyRecord(id=record_id, description=description, importance=importance_lookup[description], dates_lookup=dates_lookup, places_lookup=places_lookup))
            
            record = records[records_lookup[description]]
            
            # Add plan data
            if description in plan_data:
                for (date, place_id), seconds in plan_data[description].items():
                    record.add_plan_time(date, place_id, seconds)
                    total_record.add_plan_time(date, place_id, seconds)
            
            # Add fact data
            if description in fact_data:
                for (date, place_id), seconds in fact_data[description].items():
                    record.add_fact_time(date, place_id, seconds)
                    total_record.add_fact_time(date, place_id, seconds)

        records.append(total_record)
        return records 