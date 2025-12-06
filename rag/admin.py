"""
RAG Admin Configuration
"""

from django.contrib import admin
from .models import DocumentChunk, SearchQuery, SearchResult


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'chunk_index', 'token_count', 'char_count', 'has_embedding', 'created_at']
    list_filter = ['document__doc_type', 'created_at']
    search_fields = ['content', 'document__filename']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['document', 'chunk_index']

    def has_embedding(self, obj):
        return obj.embedding is not None
    has_embedding.boolean = True


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
