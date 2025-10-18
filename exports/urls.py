from django.urls import path
from . import views

app_name = "exports"

urlpatterns = [
    path("", views.export_form, name="export_form"),
    path("pdf/", views.export_pdf, name="export_pdf"),
    path("upload_chart/", views.upload_chart, name="upload_chart"),
    path("api/config/", views.export_config_api, name="export_config_api"),
]
