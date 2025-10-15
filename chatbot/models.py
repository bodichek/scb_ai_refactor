from django.db import models
from django.contrib.auth.models import User


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    context = models.CharField(max_length=100, blank=True, help_text="Kontext: ingest, dashboard, survey, atd.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}..."
