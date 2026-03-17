from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('requests/last/', views.get_last_activity),
    path('requests/activity/<slug:abbreviation>/', views.get_activity),
    path('reports/log/<int:year>/<int:month>/<int:day>/', views.daily_log),
    path('reports/log/latest/', views.latest_log),
    path('reports/summary/daily/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.daily_summary),
    path('reports/summary/daily/latest/', views.latest_daily_summary),
    path('reports/summary/weekly/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.weekly_summary),
    path('reports/summary/weekly/latest/', views.latest_weekly_summary),
    path('reports/summary/my_weekly/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.my_weekly_summary),
    path('reports/summary/my_weekly/latest/', views.latest_my_weekly_summary),
    path('reports/summary/daily_week_breakdown/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.daily_week_breakdown),
    path('reports/summary/daily_week_breakdown/latest/', views.latest_daily_week_breakdown),
    path('reports/summary/monthly/<slug:parent>/<int:year>/<int:month>/<int:day>/', views.monthly_summary),
    path('reports/summary/monthly/latest/', views.latest_monthly_summary),
    path('reports/summary/<slug:parent>/<int:to_year>/<int:to_month>/<int:to_day>/<int:from_year>/<int:from_month>/<int:from_day>/', views.custom_summary),
    path('data/log/', views.entry_log),
]
