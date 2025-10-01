# coaching/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("my-clients/", views.my_clients, name="my_clients"),
    path("edit/", views.edit_coach, name="edit_coach"),

]
