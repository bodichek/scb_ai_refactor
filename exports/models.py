from django.db import models
from django.contrib.auth.models import User


class Export(models.Model):
    """
    Stores a snapshot of numeric financial metrics used for AI chat context.
    """

    SOURCE_DASHBOARD = "dashboard"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_DASHBOARD, "Dashboard"),
        (SOURCE_MANUAL, "Manual"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exports")
    statement_year = models.IntegerField(blank=True, null=True)
    data = models.JSONField()
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default=SOURCE_DASHBOARD)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        year = self.statement_year or "n/a"
        return f"Export {year} for {self.user.username}"
