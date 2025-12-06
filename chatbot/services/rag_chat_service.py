"""
RAG-Enhanced Chat Service

Integrates semantic search into chatbot responses for context-aware answers.
"""

import logging
from typing import List, Dict, Any, Optional
from django.contrib.auth.models import User

from rag.services import SemanticSearchService
from rag.models import DocumentChunk

logger = logging.getLogger(__name__)


class RAGChatService:
    """
    Service for RAG-enhanced chatbot responses.

    Workflow:
    1. User asks a question
    2. Perform semantic search to find relevant document chunks
    3. Build context from search results
    4. Include context in LLM prompt
    5. Generate response with source citations
    """

    def __init__(
        self,
        search_service: Optional[SemanticSearchService] = None,
        max_context_chunks: int = 5,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize RAG chat service.

        Args:
            search_service: Semantic search service
            max_context_chunks: Maximum number of chunks to include in context
            similarity_threshold: Minimum similarity score for relevant chunks
        """
        self.search_service = search_service or SemanticSearchService()
        self.max_context_chunks = max_context_chunks
        self.similarity_threshold = similarity_threshold

    def retrieve_context(
        self,
        query: str,
        user: User,
        section: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for a user query using RAG.

        Args:
            query: User's question/query
            user: User making the query
            section: Optional section context (e.g., "dashboard", "ingest")

        Returns:
            Dict with:
            {
                "chunks": [DocumentChunk objects],
                "context_text": str (formatted context for LLM),
                "sources": [source metadata],
                "has_context": bool
            }
        """
        try:
            # Perform semantic search
            hits = self.search_service.search_by_user(
                query=query,
                user=user,
                limit=self.max_context_chunks,
            )

            # Filter by similarity threshold
            relevant_hits = [
                hit for hit in hits
                if hit.score >= self.similarity_threshold
            ]

            if not relevant_hits:
                return {
                    "chunks": [],
                    "context_text": "",
                    "sources": [],
                    "has_context": False,
                }

            # Build context text
            context_parts = []
            sources = []

            for i, hit in enumerate(relevant_hits, 1):
                # Add chunk content
                context_parts.append(
                    f"[Dokument {i}: {hit.chunk.document.filename} ({hit.chunk.document.year})]\n"
                    f"{hit.chunk.content}\n"
                )

                # Track source
                sources.append({
                    "document_id": hit.chunk.document.id,
                    "document_name": hit.chunk.document.filename,
                    "year": hit.chunk.document.year,
                    "doc_type": hit.chunk.document.doc_type,
                    "chunk_id": hit.chunk.id,
                    "similarity": hit.score,
                    "rank": hit.rank,
                })

            context_text = "\n---\n".join(context_parts)

            return {
                "chunks": [hit.chunk for hit in relevant_hits],
                "context_text": context_text,
                "sources": sources,
                "has_context": True,
            }

        except Exception as e:
            logger.error(f"Error retrieving RAG context: {e}", exc_info=True)
            return {
                "chunks": [],
                "context_text": "",
                "sources": [],
                "has_context": False,
            }

    def build_rag_prompt(
        self,
        query: str,
        context_text: str,
        section: Optional[str] = None,
    ) -> str:
        """
        Build enhanced prompt with RAG context.

        Args:
            query: User's question
            context_text: Retrieved context from documents
            section: Optional section context

        Returns:
            Formatted prompt for LLM
        """
        section_info = f"Sekce: {section}\n" if section else ""

        prompt = f"""{section_info}Dotaz uživatele: {query}

Relevantní kontext z dokumentů:
{context_text}

Na základě výše uvedeného kontextu z dokumentů zodpověz dotaz uživatele.
Pokud odpověď najdeš v kontextu, uveď konkrétní informace a cituj zdroj (dokument a rok).
Pokud kontext neobsahuje odpověď, upřimně to přiznej a nabídni obecnou radu."""

        return prompt

    def format_response_with_sources(
        self,
        response: str,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Format chatbot response with source citations.

        Args:
            response: LLM response text
            sources: List of source metadata dicts

        Returns:
            Dict with formatted response and sources
        """
        if not sources:
            return {
                "response": response,
                "has_sources": False,
                "sources": [],
            }

        # Build source citations
        citations = []
        for source in sources:
            citations.append(
                f"📄 {source['document_name']} "
                f"({source['year']}, {source['doc_type']}) "
                f"[skóre: {source['similarity']:.2f}]"
            )

        # Append citations to response
        formatted_response = response

        if citations:
            formatted_response += "\n\n**Zdroje:**\n" + "\n".join(citations)

        return {
            "response": formatted_response,
            "has_sources": True,
            "sources": sources,
            "citations": citations,
        }

    def generate_rag_response(
        self,
        query: str,
        user: User,
        section: Optional[str] = None,
        existing_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete RAG-enhanced response.

        This is the main method to use for chatbot integration.

        Args:
            query: User's question
            user: User making the query
            section: Optional section context
            existing_context: Optional existing context data from chatbot

        Returns:
            Dict with:
            {
                "rag_context": {...},  # RAG retrieval results
                "prompt": str,  # Enhanced prompt for LLM
                "sources": [...],  # Source metadata
                "has_rag_context": bool,
            }
        """
        # Retrieve RAG context
        rag_context = self.retrieve_context(
            query=query,
            user=user,
            section=section,
        )

        # Build enhanced prompt
        if rag_context["has_context"]:
            prompt = self.build_rag_prompt(
                query=query,
                context_text=rag_context["context_text"],
                section=section,
            )
        else:
            # No RAG context, use original query
            section_prefix = f"[Sekce: {section}]\n" if section else ""
            prompt = f"{section_prefix}{query}"

        return {
            "rag_context": rag_context,
            "prompt": prompt,
            "sources": rag_context["sources"],
            "has_rag_context": rag_context["has_context"],
        }
