"""
RAG Admin Configuration
"""

from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from .models import DocumentChunk, SearchQuery, SearchResult
from ingest.models import Document


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'document_link',
        'chunk_index',
        'token_count',
        'char_count',
        'has_embedding',
        'created_at'
    ]
    list_filter = [
        'document__doc_type',
        'document__rag_status',
        'created_at',
        ('embedding', admin.EmptyFieldListFilter),
    ]
    search_fields = ['content', 'document__filename', 'document__owner__username']
    readonly_fields = ['created_at', 'updated_at', 'content_preview', 'embedding_info']
    ordering = ['document', 'chunk_index']

    def changelist_view(self, request, extra_context=None):
        """Add link to RAG monitor in changelist."""
        extra_context = extra_context or {}
        extra_context['rag_monitor_url'] = '/admin/rag-monitor/'
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ('Chunk Info', {
            'fields': ('document', 'chunk_index', 'content_preview')
        }),
        ('Metrics', {
            'fields': ('token_count', 'char_count')
        }),
        ('Embedding', {
            'fields': ('embedding_info',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def document_link(self, obj):
        """Link to document admin."""
        from django.urls import reverse
        url = reverse('admin:ingest_document_change', args=[obj.document.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.document.filename or obj.document.file.name
        )
    document_link.short_description = 'Document'

    def has_embedding(self, obj):
        """Check if chunk has embedding."""
        return obj.embedding is not None
    has_embedding.boolean = True
    has_embedding.short_description = 'Has Embedding'

    def content_preview(self, obj):
        """Preview of chunk content."""
        preview = obj.content[:500] + '...' if len(obj.content) > 500 else obj.content
        return format_html('<pre style="white-space: pre-wrap;">{}</pre>', preview)
    content_preview.short_description = 'Content Preview'

    def embedding_info(self, obj):
        """Embedding information."""
        if obj.embedding is None:
            return format_html('<span style="color: red;">❌ No embedding</span>')

        dimensions = len(obj.embedding) if obj.embedding else 0
        return format_html(
            '<span style="color: green;">✅ Embedding present</span><br>'
            '<strong>Dimensions:</strong> {}<br>',
            dimensions
        )
    embedding_info.short_description = 'Embedding Status'


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ['id', 'query_text_preview', 'user', 'results_count', 'search_time_ms', 'created_at']
    list_filter = ['user', 'created_at']
    search_fields = ['query_text']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def query_text_preview(self, obj):
        return obj.query_text[:100] + '...' if len(obj.query_text) > 100 else obj.query_text
    query_text_preview.short_description = 'Query'


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'search_query_preview', 'chunk', 'similarity_score', 'rank', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
    ordering = ['search_query', 'rank']

    def search_query_preview(self, obj):
        text = obj.search_query.query_text
        return text[:50] + '...' if len(text) > 50 else text
    search_query_preview.short_description = 'Search Query'


# Custom admin site with RAG monitoring dashboard
class RAGAdminSite(admin.AdminSite):
    """Custom admin site with RAG monitoring dashboard."""

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('rag-monitor/', self.admin_view(rag_monitoring_dashboard), name='rag_monitor'),
        ]
        return custom_urls + urls


@staff_member_required
def rag_monitoring_dashboard(request):
    """
    RAG Processing Monitoring Dashboard.

    Shows overview of all documents and their RAG processing status.
    """
    # Get all documents
    all_docs = Document.objects.all()

    # Status counts
    status_counts = all_docs.values('rag_status').annotate(count=Count('id'))
    status_dict = {item['rag_status']: item['count'] for item in status_counts}

    # Processing mode counts
    mode_counts = all_docs.values('rag_processing_mode').annotate(count=Count('id'))
    mode_dict = {item['rag_processing_mode']: item['count'] for item in mode_counts}

    # Documents by status
    pending_docs = all_docs.filter(rag_status='pending').select_related('owner')
    processing_docs = all_docs.filter(rag_status='processing').select_related('owner')
    completed_docs = all_docs.filter(rag_status='completed').select_related('owner')
    failed_docs = all_docs.filter(rag_status='failed').select_related('owner')

    # Chunks statistics
    total_chunks = DocumentChunk.objects.count()
    chunks_with_embeddings = DocumentChunk.objects.filter(
        embedding__isnull=False
    ).count()
    chunks_without_embeddings = total_chunks - chunks_with_embeddings

    # Documents with missing embeddings
    docs_with_chunks = Document.objects.annotate(
        chunks_count=Count('chunks'),
        chunks_with_emb=Count('chunks', filter=Q(chunks__embedding__isnull=False))
    ).filter(chunks_count__gt=0)

    docs_missing_embeddings = docs_with_chunks.filter(
        chunks_count__gt=Count('chunks', filter=Q(chunks__embedding__isnull=False))
    )

    # Recent failures
    recent_failures = failed_docs.order_by('-uploaded_at')[:10]

    context = {
        'title': 'RAG Processing Monitor',
        'site_title': 'RAG Monitor',
        'site_header': 'RAG Processing Dashboard',

        # Status overview
        'total_documents': all_docs.count(),
        'pending_count': status_dict.get('pending', 0),
        'processing_count': status_dict.get('processing', 0),
        'completed_count': status_dict.get('completed', 0),
        'failed_count': status_dict.get('failed', 0),
        'skipped_count': status_dict.get('skipped', 0),

        # Processing mode overview
        'immediate_count': mode_dict.get('immediate', 0),
        'batch_count': mode_dict.get('batch', 0),
        'manual_count': mode_dict.get('manual', 0),

        # Chunks overview
        'total_chunks': total_chunks,
        'chunks_with_embeddings': chunks_with_embeddings,
        'chunks_without_embeddings': chunks_without_embeddings,
        'embedding_completion_rate': (
            (chunks_with_embeddings / total_chunks * 100) if total_chunks > 0 else 0
        ),

        # Document lists
        'pending_docs': pending_docs[:20],
        'processing_docs': processing_docs[:20],
        'completed_docs': completed_docs[:20],
        'failed_docs': failed_docs[:20],
        'recent_failures': recent_failures,

        # Missing embeddings
        'docs_missing_embeddings_count': docs_missing_embeddings.count(),
    }

    return render(request, 'admin/rag_monitor.html', context)
