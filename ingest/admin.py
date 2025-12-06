from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Document, FinancialStatement


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "owner",
        "year",
        "doc_type",
        "rag_status_badge",
        "rag_processing_mode",
        "chunks_count",
        "uploaded_at",
        "rag_actions",
    )
    list_filter = (
        "year",
        "doc_type",
        "owner",
        "rag_status",
        "rag_processing_mode",
    )
    search_fields = ("filename", "file", "owner__username")
    readonly_fields = (
        "rag_status",
        "rag_processed_at",
        "rag_error_message",
        "rag_retry_count",
        "chunks_info",
    )

    fieldsets = (
        ("Document Info", {
            "fields": ("owner", "file", "filename", "description", "year", "doc_type")
        }),
        ("Analysis", {
            "fields": ("analyzed",)
        }),
        ("RAG Processing", {
            "fields": (
                "rag_processing_mode",
                "rag_status",
                "rag_processed_at",
                "rag_retry_count",
                "rag_error_message",
                "chunks_info",
            ),
            "classes": ("collapse",),
        }),
    )

    actions = ["trigger_rag_processing", "retry_failed_documents"]

    def rag_status_badge(self, obj):
        """Display RAG status as colored badge."""
        colors = {
            "pending": "gray",
            "processing": "blue",
            "completed": "green",
            "failed": "red",
            "skipped": "orange",
        }
        color = colors.get(obj.rag_status, "gray")

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.rag_status.upper()
        )
    rag_status_badge.short_description = "RAG Status"

    def chunks_count(self, obj):
        """Display number of chunks created."""
        count = obj.chunks.count()
        with_embeddings = obj.chunks.filter(embedding__isnull=False).count()

        if count == 0:
            return "-"

        color = "green" if count == with_embeddings else "orange"
        return format_html(
            '<span style="color: {};">{} chunks ({} with embeddings)</span>',
            color,
            count,
            with_embeddings
        )
    chunks_count.short_description = "Chunks"

    def chunks_info(self, obj):
        """Detailed chunks information for detail view."""
        chunks = obj.chunks.all()
        count = chunks.count()

        if count == 0:
            return "No chunks created yet"

        with_embeddings = chunks.filter(embedding__isnull=False).count()
        total_chars = sum(c.char_count for c in chunks)
        total_tokens = sum(c.token_count for c in chunks)

        return format_html(
            "<strong>Chunks:</strong> {}<br>"
            "<strong>With embeddings:</strong> {}<br>"
            "<strong>Total characters:</strong> {:,}<br>"
            "<strong>Total tokens:</strong> {:,}",
            count,
            with_embeddings,
            total_chars,
            total_tokens,
        )
    chunks_info.short_description = "Chunks Details"

    def rag_actions(self, obj):
        """Action buttons for RAG processing."""
        if obj.rag_status == "failed":
            return format_html(
                '<a class="button" href="#" onclick="return confirm(\'Retry processing?\');">Retry</a>'
            )
        elif obj.rag_status == "pending":
            return format_html(
                '<a class="button" href="#" onclick="return confirm(\'Start processing?\');">Process Now</a>'
            )
        elif obj.rag_status == "completed":
            url = reverse("admin:rag_documentchunk_changelist") + f"?document__id__exact={obj.id}"
            return format_html(
                '<a class="button" href="{}">View Chunks</a>',
                url
            )
        return "-"
    rag_actions.short_description = "Actions"

    def trigger_rag_processing(self, request, queryset):
        """Admin action to trigger RAG processing for selected documents."""
        from rag.tasks import process_document_rag

        processed = 0
        for doc in queryset:
            try:
                # Trigger async processing
                process_document_rag.delay(doc.id)
                processed += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to queue document {doc.id}: {str(e)}",
                    level="ERROR"
                )

        self.message_user(
            request,
            f"Queued {processed} documents for RAG processing",
            level="SUCCESS"
        )
    trigger_rag_processing.short_description = "Trigger RAG processing"

    def retry_failed_documents(self, request, queryset):
        """Admin action to retry failed RAG processing."""
        from rag.tasks import process_document_rag

        failed_docs = queryset.filter(rag_status="failed")
        retried = 0

        for doc in failed_docs:
            try:
                # Reset retry count and trigger again
                doc.rag_retry_count = 0
                doc.rag_status = "pending"
                doc.save(update_fields=["rag_retry_count", "rag_status"])

                process_document_rag.delay(doc.id)
                retried += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to retry document {doc.id}: {str(e)}",
                    level="ERROR"
                )

        self.message_user(
            request,
            f"Retrying {retried} failed documents",
            level="SUCCESS"
        )
    retry_failed_documents.short_description = "Retry failed RAG processing"


@admin.register(FinancialStatement)
class FinancialStatementAdmin(admin.ModelAdmin):
    list_display = ("user", "year", "scale", "document", "uploaded_at")

    def uploaded_at(self, obj):
        return obj.document.uploaded_at if obj.document else None
    uploaded_at.admin_order_field = "document__uploaded_at"
    uploaded_at.short_description = "Uploaded at"
