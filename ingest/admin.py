from django.contrib import admin
from .models import Document, FinancialStatement


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("owner", "file", "year", "doc_type", "uploaded_at")
    list_filter = ("year", "doc_type", "owner")
    search_fields = ("file", "owner__username")


@admin.register(FinancialStatement)
class FinancialStatementAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "scale", "document", "uploaded_at")

    def uploaded_at(self, obj):
        return obj.document.uploaded_at if obj.document else None
    uploaded_at.admin_order_field = "document__uploaded_at"
    uploaded_at.short_description = "Uploaded at"
