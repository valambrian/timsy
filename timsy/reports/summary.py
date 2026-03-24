from datetime import date
from typing import Dict, List, Any
from django.db import connection

from ..models import Place
from .utils import seconds_to_string
from .queries.fact_queries import get_parent_fact_query, get_activity_fact_query

class SummaryRecord:
    """
    A class to represent a summary record of activities.
    
    This class is used to aggregate and summarize activity records by place,
    providing methods to add time spent and retrieve formatted summaries.
    """
    
    def __init__(self, id: str, description: str, places_lookup: Dict[str, int]) -> None:
        """
        Initialize a SummaryRecord.
        
        Args:
            id: The ID of the record
            description: The description of the record
            places_lookup: Dictionary mapping place IDs to their descriptions
        """
        self.id = id
        self.description = description
        self.places_lookup = places_lookup
        self.seconds = [0] * len(places_lookup)

    def add(self, place: str, seconds: int) -> None:
        """
        Add time spent at a place to the summary.
        
        Args:
            place: The place ID
            seconds: Number of seconds spent at the place
        """
        index = self.places_lookup[place]
        self.seconds[index] += seconds

    def get_times(self) -> List[str]:
        """
        Get a formatted summary of time spent at each place.
        
        Returns:
            List of dictionaries containing place descriptions and formatted times
        """
        result = []
        total = 0
        for index in range(len(self.seconds)):
            current_seconds = self.seconds[index]
            total += current_seconds
            result.append(seconds_to_string(current_seconds))
        result.append(seconds_to_string(total))
        return result

    @classmethod
    def get_summary_records(cls, parent: str, start_date: date, end_date: date) -> List['SummaryRecord']:
        """Get summary records for a specified period.
        
        Retrieves and aggregates activity records by parent and place for the given date range.
        Uses separate optimized queries for better performance.
        
        Args:
            parent: Parent activity filter ('ALL' for all activities)
            start_date: Start date of the report period
            end_date: End date of the report period
            
        Returns:
            List of SummaryRecord objects containing aggregated time data
        """
        cursor = connection.cursor()
        if parent == "ALL":
            parent_pattern = "__"
        else:
            parent_pattern = "%s-__" % (parent,)
        start_date_pattern = start_date.strftime("%Y-%m-%d")
        end_date_pattern = end_date.strftime("%Y-%m-%d")

        places = Place.get_abbreviations()
        places_lookup = {}
        for i in range(len(places)):
            places_lookup[places[i]] = i

        # Execute separate queries for better performance
        parent_query = get_parent_fact_query(parent_pattern, start_date_pattern, end_date_pattern)
        cursor.execute(parent_query, [parent_pattern, start_date_pattern, end_date_pattern])
        parent_rows = cursor.fetchall()

        activity_query = get_activity_fact_query(parent, start_date_pattern, end_date_pattern)
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
                'place_id': row[5],
                'total_seconds': row[6]
            })

        activity_results = []
        for row in activity_rows:
            activity_results.append({
                'parent_order': row[0],
                'activity_order': row[1],
                'id': row[2],
                'description': row[3],
                'importance': row[4],
                'place_id': row[5],
                'total_seconds': row[6]
            })

        # Combine and sort results
        combined_rows = list(parent_results) + list(activity_results)
        
        # Sort by activity_order first (NULLs first), then by parent_order
        def sort_key(row):
            activity_order = row.get('activity_order')
            parent_order = row.get('parent_order')
            
            # NULLs should come first for activity_order, last for parent_order
            activity_sort = (0, 0) if activity_order is None else (1, activity_order)
            parent_sort = (1, 0) if parent_order is None else (0, parent_order)
            
            return (activity_sort, parent_sort)
        
        combined_rows = sorted(combined_rows, key=sort_key)

        # Process combined results into SummaryRecord objects
        records = []
        records_lookup = {}
        total_record = SummaryRecord(id="", description="Total", places_lookup=places_lookup)

        for row in combined_rows:
            id = row['id']
            description = row['description']
            place = row['place_id']
            seconds = row['total_seconds']
            
            if description not in records_lookup:
                records_lookup[description] = len(records)
                records.append(SummaryRecord(id=id, description=description, places_lookup=places_lookup))
            record = records[records_lookup[description]]
            record.add(place, seconds)
            total_record.add(place, seconds)
            
        records.append(total_record)
        return records