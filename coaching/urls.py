# coaching/urls.py
from django.urls import path
from . import views

app_name = 'coaching'

urlpatterns = [
    path("my-clients/", views.my_clients, name="my_clients"),
    path("client/<int:client_id>/", views.client_dashboard, name="client_dashboard"),
    path("client/<int:client_id>/documents/", views.client_documents, name="client_documents"),
    path("client/<int:client_id>/notes/", views.save_client_notes, name="save_client_notes"),
    path("edit/", views.edit_coach, name="edit_coach"),
]
