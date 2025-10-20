from django.urls import path
from . import views
from . import views_cashflow  # původní modul s cashflow view (ponecháno odděleně)
from . import debug_views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("save_chart/", views.save_chart, name="save_chart"),
    path("ask-coach/", views.ask_coach, name="ask_coach"),
    path("debug/", debug_views.debug_cashflow, name="debug_cashflow"),  # Debug view

    # Cashflow přehled
    path("cashflow/", views_cashflow.cashflow_view, name="cashflow"),
    path("cashflow/<int:year>/", views_cashflow.cashflow_view, name="cashflow_view"),

    # API
    path("api/cashflow/<int:year>/", views.api_cashflow, name="api_cashflow"),
]

# Extra API endpoints appended
urlpatterns += [
    path("api/metrics/series/", views.api_metrics_series, name="api_metrics_series"),
    path("api/profitability/", views.api_profitability, name="api_profitability"),
    path("api/cashflow/summary/", views.api_cashflow_summary, name="api_cashflow_summary"),
]
