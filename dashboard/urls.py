from django.urls import path
from . import views
from . import views_cashflow  # ⬅️ nový modul s cashflow view (ponecháno odděleně)
from . import debug_views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("save_chart/", views.save_chart, name="save_chart"),
    path("debug/", debug_views.debug_cashflow, name="debug_cashflow"),  # Debug view

    # 💰 Cashflow přehled
    path("cashflow/", views_cashflow.cashflow_view, name="cashflow"),              # výchozí stránka s výběrem roku
    path("cashflow/<int:year>/", views_cashflow.cashflow_view, name="cashflow_view"),  # zachováno pro přímý odkaz
    
    # API pro dynamické načítání cashflow
    path("api/cashflow/<int:year>/", views.api_cashflow, name="api_cashflow"),

    # hlavní dashboard
]

