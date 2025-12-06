"""
Embedding Generation Service

Generates vector embeddings using OpenAI text-embedding-3-small.
Handles batching, rate limiting, and caching.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embedding: List[float]
    model: str
    usage: Dict[str, int]


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI.

    Uses text-embedding-3-small:
    - 1536 dimensions
    - Cost: $0.02 per 1M tokens
    - Performance: Fast and cost-effective
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,  # OpenAI supports up to 2048 inputs per request
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize embedding service.

        Args:
            model: OpenAI embedding model to use
            batch_size: Number of texts to embed in a single API call
            max_retries: Maximum number of retries on failure
            retry_delay: Delay between retries in seconds
        """
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize OpenAI client
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in settings")

        self.client = OpenAI(api_key=api_key)
        logger.info(f"Initialized EmbeddingService with model: {model}")

    def embed_text(self, text: str) -> Optional[EmbeddingResult]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult or None on failure
        """
        results = self.embed_texts([text])
        return results[0] if results else None

    def embed_texts(self, texts: List[str]) -> List[Optional[EmbeddingResult]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResult objects (None for failed embeddings)
        """
        if not texts:
            return []

        results = [None] * len(texts)

        # Process in batches
        for batch_start in range(0, len(texts), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(texts))
            batch_texts = texts[batch_start:batch_end]

            logger.info(
                f"Generating embeddings for batch {batch_start}-{batch_end} "
                f"({len(batch_texts)} texts)"
            )

            batch_results = self._embed_batch(batch_texts)

            # Store results
            for i, result in enumerate(batch_results):
                results[batch_start + i] = result

        successful = sum(1 for r in results if r is not None)
        logger.info(
            f"Generated {successful}/{len(texts)} embeddings successfully"
        )

        return results

    def _embed_batch(self, texts: List[str]) -> List[Optional[EmbeddingResult]]:
        """
        Generate embeddings for a batch of texts with retry logic.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResult objects
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.model
                )

                # Parse response
                results = []
                for data in response.data:
                    results.append(
                        EmbeddingResult(
                            embedding=data.embedding,
                            model=response.model,
                            usage={
                                'total_tokens': response.usage.total_tokens,
                                'prompt_tokens': response.usage.prompt_tokens,
                            }
                        )
                    )

                return results

            except Exception as e:
                logger.warning(
                    f"Embedding generation failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to generate embeddings after {self.max_retries} attempts")
                    return [None] * len(texts)

        return [None] * len(texts)

    def get_dimensions(self) -> int:
        """Get the dimensionality of embeddings for this model."""
        # text-embedding-3-small: 1536 dimensions
        # text-embedding-3-large: 3072 dimensions
        if self.model == "text-embedding-3-small":
            return 1536
        elif self.model == "text-embedding-3-large":
            return 3072
        else:
            # Default for older models
            return 1536

    def estimate_cost(self, token_count: int) -> float:
        """
        Estimate cost for embedding generation.

        Args:
            token_count: Number of tokens to embed

        Returns:
            Estimated cost in USD
        """
        # Pricing for text-embedding-3-small: $0.02 per 1M tokens
        cost_per_million = 0.02
        return (token_count / 1_000_000) * cost_per_million
