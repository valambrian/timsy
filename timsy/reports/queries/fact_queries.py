"""
Fact data queries for timsy reports.

These queries aggregate actual time spent from ActivityRecord entries.
They are shared across multiple report types to ensure consistency.
"""

def get_parent_fact_query(
    parent_pattern: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get the SQL query for parent-level fact summary.
    
    Args:
        parent_pattern: Pattern for parent ID filtering
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        SQL query for parent fact summary
    """
    return """SELECT p.sort_order as parent_order,
                     NULL as activity_order,
                     p.id,
                     p.description,
                     pi.description as importance,
                     r.place_id,
                     SUM(TIME_TO_SEC(r.duration)) as total_seconds
              FROM timsy_parent p
              INNER JOIN timsy_importance pi ON pi.id = p.importance_id
              INNER JOIN timsy_activity a ON a.parent_id LIKE CONCAT(p.id, '%%')
              INNER JOIN timsy_activityrecord r ON r.activity_id = a.id
              WHERE p.id LIKE %s 
                AND r.start >= %s
                AND r.start < %s + INTERVAL 1 DAY
              GROUP BY p.sort_order, p.id, p.description, pi.description, r.place_id
              ORDER BY p.sort_order""" 

def get_activity_fact_query(
    parent: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get the SQL query for activity-level fact summary.
    
    Args:
        parent: Parent ID for activity filtering
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        SQL query for activity fact summary
    """
    return """SELECT NULL as parent_order,
                     a.sort_order as activity_order,
                     '' as id,
                     a.description,
                     ai.description as importance,
                     r.place_id,
                     SUM(TIME_TO_SEC(r.duration)) as total_seconds
              FROM timsy_activity a
              INNER JOIN timsy_importance ai ON ai.id = a.importance_id
              INNER JOIN timsy_activityrecord r ON r.activity_id = a.id
              WHERE a.parent_id = %s
                AND r.start >= %s
                AND r.start < %s + INTERVAL 1 DAY
              GROUP BY a.sort_order, a.description, ai.description, r.place_id
              ORDER BY a.sort_order"""

def get_parent_fact_daily_breakdown_query(
    parent_pattern: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get the SQL query for parent-level fact daily breakdown.
    
    Args:
        parent_pattern: Pattern for parent ID filtering
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        SQL query for parent fact daily breakdown
    """
    return """SELECT p.sort_order as parent_order,
                     NULL as activity_order,
                     p.id,
                     p.description,
                     pi.description as importance,
                     DATE(r.start) as date,
                     r.place_id,
                     SUM(TIME_TO_SEC(r.duration)) as total_seconds
              FROM timsy_parent p
              INNER JOIN timsy_importance pi ON pi.id = p.importance_id
              INNER JOIN timsy_activity a ON a.parent_id LIKE CONCAT(p.id, '%%')
              INNER JOIN timsy_activityrecord r ON r.activity_id = a.id
              WHERE p.id LIKE %s 
                AND r.start >= %s
                AND r.start < %s + INTERVAL 1 DAY
              GROUP BY p.sort_order, p.id, p.description, pi.description, DATE(r.start), r.place_id
              ORDER BY p.sort_order, DATE(r.start)"""

def get_activity_fact_daily_breakdown_query(
    parent: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get the SQL query for activity-level fact daily breakdown.
    
    Args:
        parent: Parent ID for activity filtering
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        SQL query for activity fact daily breakdown
    """
    return """SELECT NULL as parent_order,
                     a.sort_order as activity_order,
                     '' as id,
                     a.description,
                     ai.description as importance,
                     DATE(r.start) as date,
                     r.place_id,
                     SUM(TIME_TO_SEC(r.duration)) as total_seconds
              FROM timsy_activity a
              INNER JOIN timsy_importance ai ON ai.id = a.importance_id
              INNER JOIN timsy_activityrecord r ON r.activity_id = a.id
              WHERE a.parent_id = %s
                AND r.start >= %s
                AND r.start < %s + INTERVAL 1 DAY
              GROUP BY a.sort_order, a.description, ai.description, DATE(r.start), r.place_id
              ORDER BY a.sort_order, DATE(r.start)""" 