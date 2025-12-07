from django.urls import path
from . import views

app_name = "ingest"

urlpatterns = [
    path("documents/", views.documents_list, name="documents"),
    path("upload/", views.upload_pdf, name="upload_pdf"),
    path("upload-many/", views.upload_many, name="upload_many"),
    path("api/documents/", views.documents_api, name="documents_api"),
    path("api/documents/<int:document_id>/", views.document_api, name="document_api"),
    path("api/upload-vision/", views.upload_vision_api, name="upload_vision_api"),
]
