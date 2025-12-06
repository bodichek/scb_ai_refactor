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

RAG_PROCESSING_STATUS = [
    ("pending", "Pending"),
    ("processing", "Processing"),
    ("completed", "Completed"),
    ("failed", "Failed"),
    ("skipped", "Skipped"),
]

RAG_PROCESSING_MODE = [
    ("immediate", "Immediate"),
    ("batch", "Batch (nightly)"),
    ("manual", "Manual only"),
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

    # RAG processing fields
    rag_status = models.CharField(
        max_length=20,
        choices=RAG_PROCESSING_STATUS,
        default="pending",
        help_text="Status of RAG processing (chunking + embeddings)"
    )
    rag_processing_mode = models.CharField(
        max_length=20,
        choices=RAG_PROCESSING_MODE,
        default="immediate",
        help_text="When to process this document for RAG"
    )
    rag_processed_at = models.DateTimeField(null=True, blank=True)
    rag_error_message = models.TextField(blank=True, help_text="Error details if RAG processing failed")
    rag_retry_count = models.IntegerField(default=0, help_text="Number of retry attempts")

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
