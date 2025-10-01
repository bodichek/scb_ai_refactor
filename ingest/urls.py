from django.urls import path
from . import views

app_name = "ingest"

urlpatterns = [
    path("documents/", views.documents_list, name="documents"),
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("delete/<int:document_id>/", views.delete_document, name="delete_document"),

]