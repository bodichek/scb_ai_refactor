from django.db import models
from django.contrib.auth.models import User


class Coach(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=200, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)           # krátký popis kouče
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)       # odkaz na LinkedIn profil
    website = models.URLField(blank=True, null=True)        # osobní web
    city = models.CharField(max_length=100, blank=True, null=True)  # kde působí
    available = models.BooleanField(default=True)           # dostupnost kouče

    def __str__(self):
        return f"{self.user.username} ({self.specialization or 'Coach'})"


class UserCoachAssignment(models.Model):
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE)
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)         # poznámky k přiřazení

    class Meta:
        unique_together = ("coach", "client")

    def __str__(self):
        return f"{self.coach.user.username} → {self.client.username}"
