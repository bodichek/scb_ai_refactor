from django.db import models
from django.contrib.auth.models import User
from coaching.models import Coach


class CompanyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Identifikace
    company_name = models.CharField("Název firmy", max_length=255)
    ico = models.CharField("IČO", max_length=20, blank=True, null=True)

    # Kontaktní údaje
    contact_person = models.CharField("Kontaktní osoba", max_length=255, blank=True, null=True)
    phone = models.CharField("Telefon", max_length=30, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    website = models.URLField("Webové stránky", blank=True, null=True)
    linkedin = models.URLField("LinkedIn", blank=True, null=True)

    # Firemní info
    industry = models.CharField("Odvětví působnosti", max_length=100, blank=True, null=True)
    employees_count = models.PositiveIntegerField("Počet zaměstnanců", blank=True, null=True)

    # Přiřazený kouč
    assigned_coach = models.ForeignKey(Coach, on_delete=models.SET_NULL, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name or self.user.username

class UserRole(models.Model):
    ROLE_CHOICES = [
        ("company", "Firma"),
        ("coach", "Kouč"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="company")

    def __str__(self):
        return f"{self.user.username} ({self.role})"