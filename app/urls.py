from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.landing, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("coaching/", include("coaching.urls")),
    path("ingest/", include("ingest.urls")),
    path("dashboard/", include("dashboard.urls")),
]
