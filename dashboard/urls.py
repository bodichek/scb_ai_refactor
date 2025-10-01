from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("profitability/", views.profitability, name="profitability"),
    path("report/", views.report_view, name="report"),
]
