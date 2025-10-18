# coaching/urls.py
from django.urls import path
from . import views

app_name = 'coaching'

urlpatterns = [
    path("my-clients/", views.my_clients, name="my_clients"),
    path("api/clients/", views.my_clients_api, name="my_clients_api"),
    path("client/<int:client_id>/", views.client_dashboard, name="client_dashboard"),
    path("client/<int:client_id>/documents/", views.client_documents, name="client_documents"),
    path("client/<int:client_id>/notes/", views.save_client_notes, name="save_client_notes"),
    path("edit/", views.edit_coach, name="edit_coach"),

    # JSON data endpoints for SPA / tests
    path("client/<int:client_id>/data/", views.client_data, name="client_data"),
    path("client/<int:client_id>/documents-data/", views.documents_data, name="documents_data"),
    path("client/<int:client_id>/cashflow-data/", views.cashflow_data, name="cashflow_data"),
    path("client/<int:client_id>/charts-data/", views.charts_data, name="charts_data"),
    path("client/<int:client_id>/surveys-data/", views.surveys_data, name="surveys_data"),
    path("client/<int:client_id>/suropen-data/", views.suropen_data, name="suropen_data"),
]
