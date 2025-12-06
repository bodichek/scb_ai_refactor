"""
RAG Processing Configuration

Defines rules for when documents should be processed immediately vs. in batch.
"""

from ingest.models import Document


class RAGProcessingConfig:
    """
    Configuration for automatic RAG processing.

    Determines processing mode based on document properties.
    """

    # File size threshold in bytes (default: 2 MB)
    # Files larger than this will always go to batch
    IMMEDIATE_PROCESSING_MAX_SIZE = 2 * 1024 * 1024

    # Document types that should be processed immediately
    # Only critical financial statements
    IMMEDIATE_PROCESSING_DOC_TYPES = [
        "income_statement",
        "balance_sheet",
    ]

    # Document types that should be processed in batch (default)
    BATCH_PROCESSING_DOC_TYPES = [
        "other",
        "cashflow",
        "income",  # legacy
        "balance",  # legacy
        "rozvaha",  # legacy
        "vysledovka",  # legacy
    ]

    # Enable/disable automatic processing
    AUTO_PROCESSING_ENABLED = True

    @classmethod
    def get_processing_mode(cls, document: Document) -> str:
        """
        Determine processing mode for a document based on rules.

        Rules (in priority order):
        1. If auto-processing disabled → "manual"
        2. If file size > threshold → "batch"
        4. If doc_type in immediate list → "immediate"
        2. If doc_type in batch list → "batch"
        1. Default → "batch" (conservative approach)

        Args:
            document: Document instance

        Returns:
            Processing mode: "immediate", "batch", or "manual"
        """
        # Check if auto-processing is enabled
        if not cls.AUTO_PROCESSING_ENABLED:
            return "manual"

        # Check file size - large files always go to batch
        max_size = cls.IMMEDIATE_PROCESSING_MAX_SIZE
        if document.file and document.file.size > max_size:
            return "batch"

        # Check if doc type is in immediate list (high priority)
        if document.doc_type in cls.IMMEDIATE_PROCESSING_DOC_TYPES:
            return "immediate"

        # Check if doc type is in batch list
        if document.doc_type in cls.BATCH_PROCESSING_DOC_TYPES:
            return "batch"

        # Default to batch (conservative - process during off-hours)
        return "batch"

    @classmethod
    def should_process_immediately(cls, document: Document) -> bool:
        """
        Check if document should be processed immediately.

        Args:
            document: Document instance

        Returns:
            True if should process immediately
        """
        return cls.get_processing_mode(document) == "immediate"

    @classmethod
    def update_document_processing_mode(cls, document: Document) -> None:
        """
        Update document's processing mode based on config rules.

        This is called before save in signal to set the mode automatically.

        Args:
            document: Document instance (not yet saved)
        """
        if not document.rag_processing_mode:  # Only set if not explicitly set
            document.rag_processing_mode = cls.get_processing_mode(document)


# Admin-configurable settings (can be overridden in Django admin)
class RAGSettings:
    """
    Runtime settings for RAG processing.

    These can be changed via environment variables or Django settings.
    """

    @staticmethod
    def get_embedding_batch_size() -> int:
        """Get batch size for embedding generation."""
        from django.conf import settings
        return getattr(settings, "RAG_EMBEDDING_BATCH_SIZE", 10)

    @staticmethod
    def get_max_retries() -> int:
        """Get maximum retry attempts for failed processing."""
        from django.conf import settings
        return getattr(settings, "RAG_MAX_RETRIES", 3)

    @staticmethod
    def get_retry_delay() -> int:
        """Get retry delay in seconds."""
        from django.conf import settings
        return getattr(settings, "RAG_RETRY_DELAY", 300)  # 5 minutes

    @staticmethod
    def get_chunk_size() -> int:
        """Get chunk size for text splitting."""
        from django.conf import settings
        return getattr(settings, "RAG_CHUNK_SIZE", 2000)

    @staticmethod
    def get_chunk_overlap() -> int:
        """Get chunk overlap size."""
        from django.conf import settings
        return getattr(settings, "RAG_CHUNK_OVERLAP", 200)

    @staticmethod
    def is_email_notifications_enabled() -> bool:
        """Check if email notifications are enabled."""
        from django.conf import settings
        return getattr(settings, "RAG_EMAIL_NOTIFICATIONS", True)

    @staticmethod
    def get_admin_emails() -> list:
        """Get admin emails for notifications."""
        from django.conf import settings
        return getattr(settings, "ADMINS", [])
