from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("save_chart/", views.save_chart, name="save_chart"),
# hlavní dashboard
]
