from django.urls import path

from . import views
from .views import (
    blueprint_views,
    daily_breakdown_views,
    daily_log_views,
    ideal_day_template_views,
    request_views,
    simple_summary_views,
    time_entry_log_views
)

urlpatterns = [
    path('', views.index, name='index'),
    path('reports/log/<int:year>/<int:month>/<int:day>/', views.daily_log),
    path('reports/log/latest/', views.latest_log),
    path('reports/summary/daily/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.daily_summary),
    path('reports/summary/daily/latest/', views.latest_daily_summary),
    path('reports/summary/weekly/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.weekly_summary),
    path('reports/summary/weekly/latest/', views.latest_weekly_summary),
    path('reports/summary/my_weekly/latest/', views.latest_my_weekly_summary),
    path('reports/summary/daily_week_breakdown/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.daily_week_breakdown),
    path('reports/summary/daily_week_breakdown/latest/', views.latest_daily_week_breakdown),
    path('reports/summary/monthly/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.monthly_summary),
    path('reports/summary/monthly/latest/', views.latest_monthly_summary),
    path('reports/summary/<slug:parent>/<int:from_year>/<int:from_month>/<int:from_day>/<int:to_year>/<int:to_month>/<int:to_day>/', views.custom_summary),
    path('data/activities/last/', views.get_last_activity_record),
    path('data/activities/<slug:abbreviation>/', views.get_activity_by_abbreviation),
    path('data/entry_log/', views.entry_log),
    path('data/ideal_day_templates/', views.idt_list_view, name='idt_list'),
    path('data/ideal_day_templates/view/<int:id>/', views.idt_view),
    path('data/ideal_day_templates/summary/<int:id>/', views.idt_summary),
    path('data/ideal_day_templates/edit/<int:id>/', views.idt_edit),
    path('data/plans/daily/', views.daily_plan_list, name='daily_plan_list'),
    path('data/plans/daily/create/', views.daily_plan_create, name='daily_plan_create'),
    path('data/plans/daily/<int:year>/<int:month>/<int:day>/', views.daily_plan_view, name='daily_plan_view'),
    path('data/plans/daily/<int:year>/<int:month>/<int:day>/edit/', views.daily_plan_edit, name='daily_plan_edit'),
    path('blueprints/', blueprint_views.blueprint_list_view, name='blueprint_list'),
    path('blueprints/<int:id>/', blueprint_views.blueprint_detail_view, name='blueprint_detail'),
    path('blueprints/<int:id>/edit/', blueprint_views.blueprint_edit_view, name='blueprint_edit'),
]
