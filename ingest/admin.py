from django.contrib import admin
from .models import Document, FinancialStatement


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("file", "owner", "year", "doc_type", "uploaded_at")
    list_filter = ("doc_type", "year")
    search_fields = ("file", "owner__username")


@admin.register(FinancialStatement)
class FinancialStatementAdmin(admin.ModelAdmin):
    list_display = ("owner", "year", "document", "created_at")
    list_filter = ("year", "document__doc_type")
    search_fields = ("owner__username",)
