"""
Semantic Search Service

Performs vector similarity search using pgvector.
Supports filtering, ranking, and result caching.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from django.db import connection
from django.contrib.auth.models import User

from rag.models import DocumentChunk, SearchQuery, SearchResult
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    """A single search result."""
    chunk: DocumentChunk
    score: float
    rank: int


class SemanticSearchService:
    """
    Service for semantic search over document chunks.

    Uses pgvector for efficient similarity search with cosine distance.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize search service.

        Args:
            embedding_service: Service for generating query embeddings
        """
        self.embedding_service = embedding_service or EmbeddingService()
        logger.info("Initialized SemanticSearchService")

    def search(
        self,
        query: str,
        user: Optional[User] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        log_query: bool = True,
    ) -> List[SearchHit]:
        """
        Perform semantic search.

        Args:
            query: Search query text
            user: Optional user performing the search
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            filters: Optional filters (e.g., {'document__owner': user})
            log_query: Whether to log the query

        Returns:
            List of SearchHit objects ordered by similarity
        """
        start_time = time.time()

        # Generate query embedding
        embedding_result = self.embedding_service.embed_text(query)

        if not embedding_result:
            logger.error("Failed to generate query embedding")
            return []

        query_embedding = embedding_result.embedding

        # Perform vector search
        results = self._vector_search(
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
            filters=filters,
        )

        # Log query if requested
        if log_query:
            search_time_ms = int((time.time() - start_time) * 1000)
            self._log_search(
                query_text=query,
                query_embedding=query_embedding,
                results=results,
                search_time_ms=search_time_ms,
                user=user,
            )

        logger.info(
            f"Search completed: '{query[:50]}...' "
            f"returned {len(results)} results in {search_time_ms}ms"
        )

        return results

    def _vector_search(
        self,
        query_embedding: List[float],
        limit: int,
        similarity_threshold: float,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchHit]:
        """
        Perform vector similarity search using pgvector.

        Uses cosine distance operator (<=>):
        - 0 = identical vectors
        - 2 = opposite vectors
        - Convert to similarity: similarity = 1 - (distance / 2)
        """
        # Build SQL query
        sql = """
            SELECT
                id,
                content,
                document_id,
                chunk_index,
                1 - (embedding <=> %s::vector) / 2 AS similarity
            FROM rag_documentchunk
            WHERE embedding IS NOT NULL
        """

        params = [query_embedding]

        # Add filters
        if filters:
            for key, value in filters.items():
                sql += f" AND {key} = %s"
                params.append(value)

        # Add similarity threshold
        sql += " AND (1 - (embedding <=> %s::vector) / 2) >= %s"
        params.extend([query_embedding, similarity_threshold])

        # Order by similarity and limit
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([query_embedding, limit])

        # Execute query
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        # Convert to SearchHit objects
        results = []
        for rank, row in enumerate(rows, start=1):
            chunk_id, content, document_id, chunk_index, similarity = row

            # Fetch chunk object
            try:
                chunk = DocumentChunk.objects.get(id=chunk_id)
                results.append(
                    SearchHit(
                        chunk=chunk,
                        score=float(similarity),
                        rank=rank,
                    )
                )
            except DocumentChunk.DoesNotExist:
                logger.warning(f"Chunk {chunk_id} not found")
                continue

        return results

    def search_by_document(
        self,
        query: str,
        document_id: int,
        limit: int = 5,
    ) -> List[SearchHit]:
        """
        Search within a specific document.

        Args:
            query: Search query
            document_id: ID of the document to search within
            limit: Maximum number of results

        Returns:
            List of SearchHit objects
        """
        return self.search(
            query=query,
            limit=limit,
            filters={'document_id': document_id},
            log_query=False,
        )

    def search_by_user(
        self,
        query: str,
        user: User,
        limit: int = 10,
    ) -> List[SearchHit]:
        """
        Search within user's documents only.

        Args:
            query: Search query
            user: User whose documents to search
            limit: Maximum number of results

        Returns:
            List of SearchHit objects
        """
        return self.search(
            query=query,
            user=user,
            limit=limit,
            filters={'document__owner_id': user.id},
            log_query=True,
        )

    def _log_search(
        self,
        query_text: str,
        query_embedding: List[float],
        results: List[SearchHit],
        search_time_ms: int,
        user: Optional[User] = None,
    ):
        """Log search query and results."""
        try:
            # Create search query log
            search_query = SearchQuery.objects.create(
                user=user,
                query_text=query_text,
                query_embedding=query_embedding,
                results_count=len(results),
                search_time_ms=search_time_ms,
            )

            # Log individual results
            for hit in results:
                SearchResult.objects.create(
                    search_query=search_query,
                    chunk=hit.chunk,
                    similarity_score=hit.score,
                    rank=hit.rank,
                )

            logger.debug(f"Logged search query {search_query.id}")

        except Exception as e:
            logger.warning(f"Failed to log search query: {e}")

    def get_similar_chunks(
        self,
        chunk: DocumentChunk,
        limit: int = 5,
        exclude_same_document: bool = True,
    ) -> List[SearchHit]:
        """
        Find chunks similar to a given chunk.

        Args:
            chunk: The chunk to find similar chunks for
            limit: Maximum number of results
            exclude_same_document: Whether to exclude chunks from the same document

        Returns:
            List of similar SearchHit objects
        """
        if not chunk.embedding:
            logger.warning(f"Chunk {chunk.id} has no embedding")
            return []

        filters = {}
        if exclude_same_document:
            # Use raw SQL to exclude same document
            sql = """
                SELECT
                    id,
                    content,
                    document_id,
                    chunk_index,
                    1 - (embedding <=> %s::vector) / 2 AS similarity
                FROM rag_documentchunk
                WHERE embedding IS NOT NULL
                  AND document_id != %s
                  AND id != %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """

            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    [chunk.embedding, chunk.document_id, chunk.id, chunk.embedding, limit]
                )
                rows = cursor.fetchall()

            results = []
            for rank, row in enumerate(rows, start=1):
                chunk_id, content, document_id, chunk_index, similarity = row

                try:
                    similar_chunk = DocumentChunk.objects.get(id=chunk_id)
                    results.append(
                        SearchHit(
                            chunk=similar_chunk,
                            score=float(similarity),
                            rank=rank,
                        )
                    )
                except DocumentChunk.DoesNotExist:
                    continue

            return results

        return self._vector_search(
            query_embedding=chunk.embedding,
            limit=limit + 1,  # +1 because we'll exclude the chunk itself
            similarity_threshold=0.0,
            filters=filters,
        )[:limit]
