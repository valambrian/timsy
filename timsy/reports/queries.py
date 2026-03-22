"""
Database queries for the timsy application.

This module contains complex SQL queries used across different views for generating reports
and summaries. The queries are designed to aggregate activity records by various dimensions
such as time periods, places, and parent activities.

The module provides functions for:
- Generating summary reports with time aggregation by place
- Creating daily breakdown reports with time aggregation by both date and place
"""

from typing import Union

def get_summary_query(
    parent_pattern: str,
    start_date_pattern: str,
    end_date_pattern: str,
    parent: str
) -> str:
    """
    Get the SQL query for summary report.
    
    Args:
        parent_pattern: Pattern for parent ID filtering
        start_date_pattern: Start date in YYYY-MM-DD format
        end_date_pattern: End date in YYYY-MM-DD format
        parent: Parent ID for activity filtering
        
    Returns:
        SQL query for summary report
    """
    return """select p.sort_order parent_order,
                      NULL activity_order,
                      p.id,
                      p.description,
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_parent p,
                      timsy_activity a,
                      timsy_activityrecord r
                where p.id like '%s' 
                  and a.parent_id like CONCAT(p.id, '%%%%')
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by p.sort_order,
                      p.id,
                      p.description,
                      r.place_id
                union
               select NULL parent_order,
                      a.sort_order activity_order,
                      '',
                      a.description,
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_activityrecord r,
                      timsy_activity a
                where a.parent_id = '%s'
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by a.sort_order,
                      a.description,
                      r.place_id
             order by activity_order,
                      parent_order""" % (parent_pattern,
                                       start_date_pattern,
                                       end_date_pattern,
                                       parent,
                                       start_date_pattern,
                                       end_date_pattern)

def get_daily_breakdown_query(
    parent_pattern: str,
    start_date_pattern: str,
    end_date_pattern: str,
    parent: str
) -> str:
    """
    Get the SQL query for daily breakdown report.
    
    Args:
        parent_pattern: Pattern for parent ID filtering
        start_date_pattern: Start date in YYYY-MM-DD format
        end_date_pattern: End date in YYYY-MM-DD format
        parent: Parent ID for activity filtering
        
    Returns:
        SQL query for daily breakdown report
    """
    return """select p.sort_order parent_order,
                      NULL activity_order,
                      p.id,
                      p.description,
                      date(r.start),
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_parent p,
                      timsy_activity a,
                      timsy_activityrecord r
                where p.id like '%s' 
                  and a.parent_id like CONCAT(p.id, '%%%%')
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by p.sort_order,
                      p.id,
                      p.description,
                      date(r.start),
                      r.place_id
                union
               select NULL parent_order,
                      a.sort_order activity_order,
                      '',
                      a.description,
                      date(r.start),
                      r.place_id,
                      SUM(TIME_TO_SEC(r.duration))
                 from timsy_activityrecord r,
                      timsy_activity a
                where a.parent_id = '%s'
                  and r.activity_id = a.id
                  and r.start >= '%s'
                  and r.start < '%s' + INTERVAL 1 DAY
             group by a.sort_order,
                      a.description,
                      date(r.start),
                      r.place_id
             order by activity_order,
                      parent_order""" % (parent_pattern,
                                       start_date_pattern,
                                       end_date_pattern,
                                       parent,
                                       start_date_pattern,
                                       end_date_pattern) 