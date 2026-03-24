"""
Plan data queries for timsy reports.

These queries aggregate planned time from DailyPlan entries,
mirroring the structure of fact queries but working with plan data.
"""

def get_parent_plan_query(
    parent_pattern: str,
    report_date: str
) -> str:
    """
    Get the SQL query for parent-level plan summary.
    
    Args:
        parent_pattern: Pattern for parent ID filtering
        report_date: Report date in YYYY-MM-DD format
        
    Returns:
        SQL query for parent plan summary
    """
    return """SELECT p.sort_order as parent_order,
                     NULL as activity_order,
                     p.id,
                     p.description,
                     pi.description as importance,
                     dpe.place_id,
                     SUM(TIME_TO_SEC(dpe.duration)) as total_seconds
              FROM timsy_parent p
              INNER JOIN timsy_importance pi ON pi.id = p.importance_id
              INNER JOIN timsy_activity a ON a.parent_id LIKE CONCAT(p.id, '%%')
              INNER JOIN timsy_dailyplanentry dpe ON dpe.activity_id = a.id
              INNER JOIN timsy_dailyplan dp ON dp.id = dpe.plan_id
              WHERE p.id LIKE %s 
                AND dp.date = %s
              GROUP BY p.sort_order, p.id, p.description, pi.description, dpe.place_id
              ORDER BY p.sort_order"""

def get_activity_plan_query(
    parent: str,
    report_date: str
) -> str:
    """
    Get the SQL query for activity-level plan summary.
    
    Args:
        parent: Parent ID for activity filtering
        report_date: Report date in YYYY-MM-DD format
        
    Returns:
        SQL query for activity plan summary
    """
    return """SELECT NULL as parent_order,
                     a.sort_order as activity_order,
                     '' as id,
                     a.description,
                     ai.description as importance,
                     dpe.place_id,
                     SUM(TIME_TO_SEC(dpe.duration)) as total_seconds
              FROM timsy_activity a
              INNER JOIN timsy_importance ai ON ai.id = a.importance_id
              INNER JOIN timsy_dailyplanentry dpe ON dpe.activity_id = a.id
              INNER JOIN timsy_dailyplan dp ON dp.id = dpe.plan_id
              WHERE a.parent_id = %s
                AND dp.date = %s
              GROUP BY a.sort_order, a.description, ai.description, dpe.place_id
              ORDER BY a.sort_order"""

def get_parent_plan_daily_breakdown_query(
    parent_pattern: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get the SQL query for parent-level plan daily breakdown.
    
    Args:
        parent_pattern: Pattern for parent ID filtering
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        SQL query for parent plan daily breakdown
    """
    return """SELECT p.sort_order as parent_order,
                     NULL as activity_order,
                     p.id,
                     p.description,
                     pi.description as importance,
                     DATE(dp.date) as date,
                     dpe.place_id,
                     SUM(TIME_TO_SEC(dpe.duration)) as total_seconds
              FROM timsy_parent p
              INNER JOIN timsy_importance pi ON pi.id = p.importance_id
              INNER JOIN timsy_activity a ON a.parent_id LIKE CONCAT(p.id, '%%')
              INNER JOIN timsy_dailyplanentry dpe ON dpe.activity_id = a.id
              INNER JOIN timsy_dailyplan dp ON dp.id = dpe.plan_id
              WHERE p.id LIKE %s 
                AND dp.date >= %s
                AND dp.date <= %s
              GROUP BY p.sort_order, p.id, p.description, pi.description, DATE(dp.date), dpe.place_id
              ORDER BY p.sort_order, DATE(dp.date)"""

def get_activity_plan_daily_breakdown_query(
    parent: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get the SQL query for activity-level plan daily breakdown.
    
    Args:
        parent: Parent ID for activity filtering
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        SQL query for activity plan daily breakdown
    """
    return """SELECT NULL as parent_order,
                     a.sort_order as activity_order,
                     '' as id,
                     a.description,
                     ai.description as importance,
                     DATE(dp.date) as date,
                     dpe.place_id,
                     SUM(TIME_TO_SEC(dpe.duration)) as total_seconds
              FROM timsy_activity a
              INNER JOIN timsy_importance ai ON ai.id = a.importance_id
              INNER JOIN timsy_dailyplanentry dpe ON dpe.activity_id = a.id
              INNER JOIN timsy_dailyplan dp ON dp.id = dpe.plan_id
              WHERE a.parent_id = %s
                AND dp.date >= %s
                AND dp.date <= %s
              GROUP BY a.sort_order, a.description, ai.description, DATE(dp.date), dpe.place_id
              ORDER BY a.sort_order, DATE(dp.date)"""