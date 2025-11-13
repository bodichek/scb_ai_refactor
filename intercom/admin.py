from django.contrib import admin
from .models import Thread, Message, Notification


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "coach", "last_message_at", "updated_at")
    search_fields = ("client__email", "client__username", "coach__email", "coach__username")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "sender", "created_at", "short_body")
    search_fields = ("sender__email", "sender__username", "body")
    list_filter = ("created_at",)

    def short_body(self, obj):
        return (obj.body or "")[:80]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__email", "user__username", "message__body")

