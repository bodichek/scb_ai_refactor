from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from accounts import views as account_views

urlpatterns = [
    path("", views.landing, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/logout/", account_views.logout_view, name="logout"),
    path("coaching/", include("coaching.urls")),
    path("ingest/", include("ingest.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("survey/", include("survey.urls")),
    path("suropen/", include("suropen.urls")),
    path("exports/", include("exports.urls")),
    path("chatbot/", include("chatbot.urls")),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
