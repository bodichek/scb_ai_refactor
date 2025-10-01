from django.urls import path
from . import views

app_name = "ingest"

urlpatterns = [
    path("documents/", views.documents_list, name="documents"),
    path("upload/", views.upload_pdf, name="upload_pdf"),   # ✔ sjednoceno
    path("process/<int:document_id>/", views.process_pdf, name="process_pdf"),
]