from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

DOC_TYPES = [
    ("income_statement", "Income Statement"),
    ("balance_sheet", "Balance Sheet"),
    ("income", "Income Statement (legacy)"),
    ("balance", "Balance Sheet (legacy)"),
    ("rozvaha", "Rozvaha (legacy)"),
    ("vysledovka", "Vysledovka (legacy)"),
    ("cashflow", "Cash Flow"),
    ("other", "Other"),
]


class Document(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="documents/")
    filename = models.CharField(max_length=255, blank=True)  # Original filename
    description = models.TextField(blank=True)  # Optional description
    year = models.IntegerField(null=True, blank=True)
    doc_type = models.CharField(
        max_length=32,
        choices=DOC_TYPES,
        default="other",
        blank=True,
    )
    analyzed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = self.file.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file.name} ({self.year or '-'})"


class FinancialStatement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    year = models.IntegerField()
    income = models.JSONField(null=True, blank=True)
    balance = models.JSONField(null=True, blank=True)
    scale = models.CharField(max_length=20, default="thousands")
    document = models.OneToOneField('Document', on_delete=models.CASCADE)

    # New fields for vision-based extraction
    local_image_path = models.CharField(max_length=500, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "year"),
                name="unique_statement_per_user_year",
            )
        ]

    def __str__(self):
        return f"FS {self.year} - {self.user}"
