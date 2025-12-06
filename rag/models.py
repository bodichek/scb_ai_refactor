"""
RAG (Retrieval-Augmented Generation) Models

Stores document chunks with vector embeddings for semantic search.
Uses pgvector extension for efficient similarity search.
"""

from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField


class DocumentChunk(models.Model):
    """
    A chunk of a document with vector embedding for semantic search.

    Documents are split into chunks to:
    1. Fit within AI context windows
    2. Enable fine-grained retrieval
    3. Improve search relevance
    """

    # Source document reference
    document = models.ForeignKey(
        'ingest.Document',
        on_delete=models.CASCADE,
        related_name='chunks'
    )

    # Chunk metadata
    chunk_index = models.IntegerField(
        help_text="Sequential index of this chunk within the document"
    )

    # Content
    content = models.TextField(
        help_text="The actual text content of this chunk"
    )

    # Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)
    embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        help_text="Vector embedding of the chunk content"
    )

    # Chunk statistics
    token_count = models.IntegerField(
        default=0,
        help_text="Approximate number of tokens in this chunk"
    )

    char_count = models.IntegerField(
        default=0,
        help_text="Number of characters in this chunk"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
        ]
        unique_together = [['document', 'chunk_index']]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.filename}"


class SearchQuery(models.Model):
    """
    Log of semantic search queries for analytics and caching.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="User who performed the search (null for anonymous)"
    )

    query_text = models.TextField(
        help_text="The search query text"
    )

    # Query vector embedding
    query_embedding = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        help_text="Vector embedding of the query"
    )

    # Results metadata
    results_count = models.IntegerField(
        default=0,
        help_text="Number of results returned"
    )

    # Performance metrics
    search_time_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Search execution time in milliseconds"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.query_text[:50]}... ({self.results_count} results)"


class SearchResult(models.Model):
    """
    Individual search result linking queries to document chunks.
    """

    search_query = models.ForeignKey(
        SearchQuery,
        on_delete=models.CASCADE,
        related_name='results'
    )

    chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.CASCADE,
        related_name='search_results'
    )

    # Similarity score (cosine similarity: -1 to 1, higher is better)
    similarity_score = models.FloatField(
        help_text="Cosine similarity score between query and chunk"
    )

    rank = models.IntegerField(
        help_text="Rank of this result in the search results (1-indexed)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['search_query', 'rank']
        indexes = [
            models.Index(fields=['search_query', 'rank']),
        ]

    def __str__(self):
        return f"Result #{self.rank} for query {self.search_query.id}"
