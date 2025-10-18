from django.urls import path
from . import views

app_name = "suropen"

urlpatterns = [
    path("", views.form, name="form"),
    path("history/", views.history, name="history"),
    path("api/form/", views.form_api, name="form_api"),
    path("api/history/", views.history_api, name="history_api"),
    path("api/batches/<uuid:batch_id>/", views.batch_detail_api, name="batch_detail_api"),
]
