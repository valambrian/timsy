def get_summary_query(parent_pattern, start_date_pattern, end_date_pattern, parent):
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


def get_daily_breakdown_query(parent_pattern, start_date_pattern, end_date_pattern, parent):
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
