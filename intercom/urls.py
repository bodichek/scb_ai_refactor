from django.urls import path
from . import views

app_name = "intercom"

urlpatterns = {
    # pro kouče – přehled vláken
}

urlpatterns = [
    path("thread/<int:client_id>/", views.thread_view, name="thread"),
    path("send/<int:client_id>/", views.send_message, name="send"),
    path("inbox/", views.inbox, name="inbox"),
    path("unread-count/", views.unread_count, name="unread_count"),
    path("notifications/mark-read/", views.mark_notifications_read, name="mark_read"),
]

