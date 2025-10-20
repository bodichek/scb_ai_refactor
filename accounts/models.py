import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from coaching.models import Coach


class CompanyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Identifikace
    company_name = models.CharField("Název firmy", max_length=255)
    ico = models.CharField("IČO", max_length=20, blank=True, null=True)
    legal_form = models.CharField("Právní forma", max_length=100, blank=True, null=True)

    # Adresa
    address = models.CharField("Adresa", max_length=500, blank=True, null=True)
    city = models.CharField("Město", max_length=100, blank=True, null=True)
    postal_code = models.CharField("PSČ", max_length=10, blank=True, null=True)

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


class CoachClientNotes(models.Model):
    """Model pro poznámky kouče o klientovi"""
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='client_notes')
    client = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='coach_notes')
    notes = models.TextField("Poznámky", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['coach', 'client']
        verbose_name = "Poznámka kouče"
        verbose_name_plural = "Poznámky kouče"

    def __str__(self):
        return f"Poznámky kouče {self.coach} o {self.client.company_name}"


class OnboardingProgress(models.Model):
    class Steps(models.TextChoices):
        UPLOAD = "upload", _("Nahrání PDF")
        SURVEY = "survey", _("Dotazník")
        OPEN_SURVEY = "open_survey", _("Otevřený dotazník")
        DONE = "done", _("Dokončeno")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="onboarding_progress")
    current_step = models.CharField(max_length=32, choices=Steps.choices, default=Steps.UPLOAD)
    is_completed = models.BooleanField(default=False)
    survey_submission = models.ForeignKey(
        "survey.SurveySubmission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_progresses",
    )
    suropen_batch_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Onboarding průvodce"
        verbose_name_plural = "Onboarding průvodci"

    def __str__(self):
        status = dict(self.Steps.choices).get(self.current_step, self.current_step)
        return f"Onboarding {self.user.username} – {status}"

    def mark_step(self, step, *, survey_submission=None, suropen_batch_id=None, completed=False, commit=True):
        self.current_step = step
        if survey_submission is not None:
            self.survey_submission = survey_submission
        if suropen_batch_id is not None:
            if suropen_batch_id == "":
                self.suropen_batch_id = None
            elif isinstance(suropen_batch_id, uuid.UUID):
                self.suropen_batch_id = suropen_batch_id
            else:
                self.suropen_batch_id = uuid.UUID(str(suropen_batch_id))
        if completed:
            self.is_completed = True
            self.current_step = self.Steps.DONE
        if commit:
            self.save()
