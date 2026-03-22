from datetime import timedelta, date
from typing import Dict, List, Optional, Any, Union
from django.db import connection

from ..models import IdealDayTemplate, IdealDayTemplateRecord, Place
from .queries import get_summary_query, get_daily_breakdown_query

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

        records = []
        records_lookup = {}
        total_record = SummaryRecord(id="", description="Total", places_lookup=places_lookup)

        query = get_summary_query(parent_pattern, start_date_pattern, end_date_pattern, parent)
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            id = row[2]
            description = row[3]
            place = row[4]
            seconds = row[5]
            if not description in records_lookup:
                records_lookup[description] = len(records)
                records.append(SummaryRecord(id=id, description=description, places_lookup=places_lookup))
            record = records[records_lookup[description]]
            record.add(place, seconds)
            total_record.add(place, seconds)
        records.append(total_record)
        return records

    @classmethod
    def summarize_idt(cls, template_id: int) -> List['SummaryRecord']:
        """Get summary records for an ideal day template.
        
        Retrieves and aggregates template records by activity and place.
        
        Args:
            template_id: ID of the ideal day template to summarize
            
        Returns:
            List of SummaryRecord objects containing aggregated time data
        """
        # Get the template and its records
        template = IdealDayTemplate.objects.get(id=template_id)
        template_records = template.get_records()
        
        # Initialize places lookup
        places = Place.get_abbreviations()
        places_lookup = {}
        for i in range(len(places)):
            places_lookup[places[i]] = i
            
        # Initialize records list and lookup
        records = []
        records_lookup = {}
        total_record = SummaryRecord(id="", description="Total", places_lookup=places_lookup)
        
        # Process each template record
        for record in template_records:
            seconds = int(record.duration.total_seconds())
            
            # Get activity info
            activity = record.activity
            description = activity.description
            
            # Get place abbreviation
            place = record.place.abbreviation
            
            # Add to records
            if description not in records_lookup:
                records_lookup[description] = len(records)
                records.append(SummaryRecord(id=str(activity.id), description=description, places_lookup=places_lookup))
            
            record = records[records_lookup[description]]
            record.add(place, seconds)
            total_record.add(place, seconds)
            
        records.append(total_record)
        return records

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

        query = get_daily_breakdown_query(parent_pattern, start_date_pattern, end_date_pattern, parent)
        cursor.execute(query)
        rows = cursor.fetchall()
        records = []
        records_lookup = {}
        total_record = DailyBreakdownSummaryRecord(id="", description="Total", dates_lookup=dates_lookup,
                                                   places_lookup=places_lookup)
        for row in rows:
            id = row[2]
            description = row[3]
            date = row[4].strftime("%Y-%m-%d")
            place = row[5]
            seconds = row[6]
            if not description in records_lookup:
                records_lookup[description] = len(records)
                records.append(DailyBreakdownSummaryRecord(id=id, description=description, dates_lookup=dates_lookup,
                                                           places_lookup=places_lookup))
            record = records[records_lookup[description]]
            record.add(date, place, seconds)
            total_record.add(date, place, seconds)
        records.append(total_record)
        return records

# Import timestamp_string from utils to use in get_times methods
from .utils import seconds_to_string