from django.urls import path
from . import views

app_name = "exports"

urlpatterns = [
    path("", views.export_form, name="export_form"),  # ✅ existuje
    path("upload_chart/", views.upload_chart, name="upload_chart"),
    path("pdf/", views.export_pdf, name="export_pdf"),
]
