from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    DOC_TYPES = [
        ("income", "Výsledovka"),
        ("balance", "Rozvaha"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="documents/")
    year = models.IntegerField()
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES, default="income")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} ({self.year}, {self.doc_type})"

class FinancialStatement(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    year = models.IntegerField()
    data = models.JSONField()  # uložené metriky z OpenAI
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("owner", "year", "document")

    def __str__(self):
        return f"{self.owner.username} - {self.year} [{self.document.doc_type}]"
