from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    DOC_TYPES = [
        ("income", "Income Statement"),
        ("balance", "Balance Sheet"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="documents/")
    year = models.IntegerField()
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES, blank=True)
    analyzed = models.BooleanField(default=False)  # ✅ nově
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} ({self.year})"


class FinancialStatement(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    year = models.IntegerField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("owner", "year")  # ⬅️ ochrana do budoucna

    def __str__(self):
        return f"FS {self.year} – {self.owner}"
