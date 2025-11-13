from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Thread(models.Model):
    """Jedno vlákno pro 1:1 konverzaci klient–kouč.

    Unikátní dvojice (client, coach). Kouč je `auth.User` (Coach.user).
    """

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="intercom_client_threads")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="intercom_coach_threads")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("client", "coach")
        ordering = ("-last_message_at", "-updated_at")

    def __str__(self):
        return f"Thread {self.client} ↔ {self.coach}"

    @staticmethod
    def for_pair(client, coach):
        obj, _ = Thread.objects.get_or_create(client=client, coach=coach)
        return obj


class Message(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="intercom_sent_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"

    def mark_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])


class Notification(models.Model):
    """Jednoduchá in‑app notifikace na novou zprávu."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="intercom_notifications")
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Notif -> {self.user} : {self.message}"

