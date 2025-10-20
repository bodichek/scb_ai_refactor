from django.db import models
from django.contrib.auth.models import User


class ChatMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_SYSTEM = "system"
    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
        (ROLE_SYSTEM, "System"),
    ]

    QUERY_GENERAL = "general"
    QUERY_CONTEXT = "context"
    QUERY_CHOICES = [
        (QUERY_GENERAL, "General"),
        (QUERY_CONTEXT, "Context"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    section = models.CharField(max_length=100, blank=True, help_text="Kontext sekce dashboardu (např. dashboard, ingest).")
    query_type = models.CharField(max_length=20, choices=QUERY_CHOICES, default=QUERY_GENERAL)
    message = models.TextField()
    response = models.TextField(blank=True)
    context_data = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        snippet = (self.message or "")[:50]
        return f"{self.user.username} [{self.role}] {snippet}..."
