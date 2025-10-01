from django.urls import path
from . import views

app_name = "suropen"

urlpatterns = [
    path("", views.form, name="form"),
    path("history/", views.history, name="history"),
]
