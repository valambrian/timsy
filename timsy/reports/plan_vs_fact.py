from datetime import date
from typing import Dict, List, Any
from django.db import connection

from ..models import Place
from .utils import seconds_to_string
from .queries.fact_queries import get_parent_fact_query, get_activity_fact_query
from .queries.plan_queries import get_parent_plan_query, get_activity_plan_query


class PlanVsFactRecord:
    """
    A class to represent a plan-vs-fact record of activities.
    
    This class aggregates and compares planned vs actual time spent by place,
    providing methods to add time data and retrieve formatted summaries.
    """
    
    def __init__(self, id: str, description: str, importance: str, places_lookup: Dict[str, int]) -> None:
        """
        Initialize a PlanVsFactRecord.
        
        Args:
            id: The ID of the record
            description: The description of the record
            importance: The importance level description
            places_lookup: Dictionary mapping place IDs to their indices
        """
        self.id = id
        self.description = description
        self.importance = importance
        self.places_lookup = places_lookup
        self.plan_seconds = [0] * len(places_lookup)
        self.fact_seconds = [0] * len(places_lookup)

    def add_plan_time(self, place: str, seconds: int) -> None:
        """
        Add planned time spent at a place.
        
        Args:
            place: The place ID
            seconds: Number of seconds planned to be spent at the place
        """
        index = self.places_lookup[place]
        self.plan_seconds[index] += seconds

    def add_fact_time(self, place: str, seconds: int) -> None:
        """
        Add actual time spent at a place.
        
        Args:
            place: The place ID
            seconds: Number of seconds actually spent at the place
        """
        index = self.places_lookup[place]
        self.fact_seconds[index] += seconds

    def get_times(self) -> List[str]:
        """
        Get formatted time strings for all places in order.
        
        Returns:
            List of formatted time strings in order:
                For each place: [plan, fact, difference]
                Then: [total_plan, total_fact, total_difference]
        """
        result = []
        total_plan_seconds = 0
        total_fact_seconds = 0
        
        # Add times by place
        for index in range(len(self.places_lookup)):
            current_plan_seconds = self.plan_seconds[index]
            current_fact_seconds = self.fact_seconds[index]
            total_plan_seconds += current_plan_seconds
            total_fact_seconds += current_fact_seconds
            
            result.append(seconds_to_string(current_plan_seconds))
            result.append(seconds_to_string(current_fact_seconds))
            result.append(seconds_to_string(current_fact_seconds - current_plan_seconds))  # fact - plan
        
        # Add totals
        result.append(seconds_to_string(total_plan_seconds))
        result.append(seconds_to_string(total_fact_seconds))
        result.append(seconds_to_string(total_fact_seconds - total_plan_seconds))
        
        return result

    @classmethod
    def get_plan_vs_fact_records(cls, parent: str, report_date: date) -> List['PlanVsFactRecord']:
        """Get plan-vs-fact records for a specified date and parent category.
        
        Uses optimized SQL queries to retrieve both plan and fact data efficiently.
        
        Args:
            parent: Parent activity filter ('ALL' for all activities)
            report_date: Date for the report
            
        Returns:
            List of PlanVsFactRecord objects containing plan vs fact data
        """
        cursor = connection.cursor()
        if parent == "ALL":
            parent_pattern = "__"
        else:
            parent_pattern = "%s-__" % (parent,)
        report_date_str = report_date.strftime("%Y-%m-%d")

        places = Place.get_abbreviations()
        places_lookup = {}
        for i in range(len(places)):
            places_lookup[places[i]] = i

        # Execute plan queries
        parent_plan_query = get_parent_plan_query(parent_pattern, report_date_str)
        cursor.execute(parent_plan_query, [parent_pattern, report_date_str])
        parent_plan_rows = cursor.fetchall()

        activity_plan_query = get_activity_plan_query(parent, report_date_str)
        cursor.execute(activity_plan_query, [parent, report_date_str])
        activity_plan_rows = cursor.fetchall()

        # Execute fact queries (using same date for start and end)
        parent_fact_query = get_parent_fact_query(parent_pattern, report_date_str, report_date_str)
        cursor.execute(parent_fact_query, [parent_pattern, report_date_str, report_date_str])
        parent_fact_rows = cursor.fetchall()

        activity_fact_query = get_activity_fact_query(parent, report_date_str, report_date_str)
        cursor.execute(activity_fact_query, [parent, report_date_str, report_date_str])
        activity_fact_rows = cursor.fetchall()

        # Convert rows to dictionaries for easier handling
        plan_data = {}  # {description: {place_id: seconds}}
        fact_data = {}  # {description: {place_id: seconds}}
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
            place_id = row[5]
            seconds = row[6]
            
            if description not in plan_data:
                plan_data[description] = {}
            plan_data[description][place_id] = plan_data[description].get(place_id, 0) + seconds
            
            # Store sort key (parent_order, activity_order) for this description
            sort_keys[description] = (parent_order, activity_order)
            # Store ID for this description
            id_lookup[description] = id_value
            # Store importance for this description
            importance_lookup[description] = importance

        # Process fact data
        for row in parent_fact_rows + activity_fact_rows:
            parent_order = row[0]
            activity_order = row[1]
            id_value = row[2]
            description = row[3]
            importance = row[4]
            place_id = row[5]
            seconds = row[6]
            
            if description not in fact_data:
                fact_data[description] = {}
            fact_data[description][place_id] = fact_data[description].get(place_id, 0) + seconds
            
            # Store sort key (parent_order, activity_order) for this description
            sort_keys[description] = (parent_order, activity_order)
            # Store ID for this description
            id_lookup[description] = id_value
            # Store importance for this description
            importance_lookup[description] = importance

        # Create PlanVsFactRecord objects
        records = []
        records_lookup = {}
        total_record = PlanVsFactRecord(id="", description="Total", importance="", places_lookup=places_lookup)

        # Get all unique descriptions from both plan and fact data
        all_descriptions = set(plan_data.keys()) | set(fact_data.keys())
        
        # Sort descriptions by parent_order first (nulls last), then by activity_order
        # Parents have non-null parent_order and null activity_order
        # Activities have null parent_order and non-null activity_order
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
                # Use the actual ID from the query results
                record_id = id_lookup[description]
                records.append(PlanVsFactRecord(id=record_id, description=description, importance=importance_lookup[description], places_lookup=places_lookup))
            
            record = records[records_lookup[description]]
            
            # Add plan data
            if description in plan_data:
                for place_id, seconds in plan_data[description].items():
                    record.add_plan_time(place_id, seconds)
                    total_record.add_plan_time(place_id, seconds)
            
            # Add fact data
            if description in fact_data:
                for place_id, seconds in fact_data[description].items():
                    record.add_fact_time(place_id, seconds)
                    total_record.add_fact_time(place_id, seconds)

        records.append(total_record)
        return records
