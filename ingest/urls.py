from django.urls import path
from . import views

app_name = "ingest"

urlpatterns = [
    path("documents/", views.documents_list, name="documents"),
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("upload-many/", views.upload_many, name="upload_many"),
    path("upload-many-api/", views.upload_many_api, name="upload_many_api"),
    path("api/documents/", views.documents_api, name="documents_api"),
    path("api/documents/<int:document_id>/", views.document_api, name="document_api"),
    path("delete/<int:document_id>/", views.delete_document, name="delete_document"),
]
