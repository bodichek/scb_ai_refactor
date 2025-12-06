"""
Document Chunking Service

Splits documents into smaller chunks for RAG processing.
Implements semantic chunking with overlap for better retrieval.
"""

import logging
import re
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a document chunk."""
    content: str
    index: int
    token_count: int
    char_count: int


class ChunkingService:
    """
    Service for splitting documents into chunks for RAG.

    Chunking strategy:
    1. Split by paragraphs/sections first
    2. If chunks are too large, split by sentences
    3. Maintain context with overlap between chunks
    4. Target chunk size: ~500 tokens (~2000 chars)
    """

    def __init__(
        self,
        chunk_size: int = 2000,  # characters
        chunk_overlap: int = 200,  # characters overlap
        min_chunk_size: int = 100,  # minimum chunk size
    ):
        """
        Initialize chunking service.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum chunk size in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str) -> List[Chunk]:
        """
        Split text into chunks.

        Args:
            text: The text to chunk

        Returns:
            List of Chunk objects
        """
        if not text or len(text.strip()) == 0:
            return []

        # Clean text
        text = self._clean_text(text)

        # Split into initial chunks
        chunks = self._split_text(text)

        # Convert to Chunk objects
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            chunk_objects.append(
                Chunk(
                    content=chunk_text,
                    index=i,
                    token_count=self._estimate_tokens(chunk_text),
                    char_count=len(chunk_text),
                )
            )

        logger.info(
            f"Chunked text into {len(chunk_objects)} chunks "
            f"(avg size: {sum(c.char_count for c in chunk_objects) / len(chunk_objects):.0f} chars)"
        )

        return chunk_objects

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove excessive newlines (keep paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _split_text(self, text: str) -> List[str]:
        """
        Split text into chunks using semantic boundaries.

        Strategy:
        1. Try to split by paragraphs first
        2. If paragraphs are too large, split by sentences
        3. Add overlap between chunks
        """
        chunks = []

        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')

        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) > self.chunk_size:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append(current_chunk.strip())

                    # Start new chunk with overlap
                    overlap = self._get_overlap(current_chunk)
                    current_chunk = overlap + " " + paragraph if overlap else paragraph
                else:
                    # Paragraph itself is too large, split by sentences
                    sentences = self._split_by_sentences(paragraph)
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > self.chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                overlap = self._get_overlap(current_chunk)
                                current_chunk = overlap + " " + sentence if overlap else sentence
                            else:
                                # Sentence itself is too large, hard split
                                current_chunk = sentence
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
            else:
                # Add paragraph to current chunk
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        # Add final chunk
        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences."""
        # Simple sentence splitter (can be improved with NLTK/spaCy)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_overlap(self, text: str) -> str:
        """Get overlap text from the end of a chunk."""
        if len(text) <= self.chunk_overlap:
            return text

        # Try to get overlap at sentence boundary
        overlap_text = text[-self.chunk_overlap:]
        sentences = self._split_by_sentences(overlap_text)

        if sentences and len(sentences) > 0:
            # Return last complete sentence(s) within overlap size
            return " ".join(sentences[-2:]) if len(sentences) > 1 else sentences[-1]

        return overlap_text

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.

        Rough estimation: 1 token ≈ 4 characters for English text.
        For more accurate counting, use tiktoken library.
        """
        return len(text) // 4

    def chunk_document_content(self, content: str, document_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk document content and return with metadata.

        Args:
            content: Document text content
            document_metadata: Optional metadata to attach to each chunk

        Returns:
            List of dicts with chunk data and metadata
        """
        chunks = self.chunk_text(content)

        result = []
        for chunk in chunks:
            chunk_data = {
                'content': chunk.content,
                'index': chunk.index,
                'token_count': chunk.token_count,
                'char_count': chunk.char_count,
            }

            # Add metadata if provided
            if document_metadata:
                chunk_data['metadata'] = document_metadata

            result.append(chunk_data)

        return result
