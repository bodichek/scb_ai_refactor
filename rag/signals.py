"""
Django signals for automatic RAG processing.

Triggers document processing after upload based on processing mode.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from ingest.models import Document
from rag.config import RAGProcessingConfig

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Document)
def set_rag_processing_mode(sender, instance, **kwargs):
    """
    Set RAG processing mode based on config rules before saving.

    This runs before the document is saved to determine the appropriate
    processing mode based on file size, doc type, etc.

    Args:
        sender: Document model class
        instance: Document instance being saved
        **kwargs: Additional signal parameters
    """
    # Only set mode if not explicitly set and this is a new document
    if not instance.pk and not instance.rag_processing_mode:
        RAGProcessingConfig.update_document_processing_mode(instance)
        logger.info(
            f"Auto-set processing mode for new document: {instance.rag_processing_mode}"
        )


@receiver(post_save, sender=Document)
def auto_process_document_rag(sender, instance, created, **kwargs):
    """
    Automatically trigger RAG processing after document upload.

    Processing behavior based on rag_processing_mode:
    - "immediate": Process immediately in background (Celery task)
    - "batch": Mark as pending, will be processed nightly
    - "manual": Do nothing, admin must trigger manually

    Args:
        sender: Document model class
        instance: Document instance that was saved
        created: True if this is a new document
        **kwargs: Additional signal parameters
    """
    # Only process newly created documents
    if not created:
        return

    logger.info(
        f"Document {instance.id} created: {instance.filename} "
        f"(mode: {instance.rag_processing_mode})"
    )

    # Check processing mode
    if instance.rag_processing_mode == "immediate":
        # Trigger immediate processing
        _trigger_immediate_processing(instance)

    elif instance.rag_processing_mode == "batch":
        # Just log, will be processed by nightly cron
        logger.info(f"Document {instance.id} scheduled for batch processing")

    elif instance.rag_processing_mode == "manual":
        # Do nothing
        logger.info(f"Document {instance.id} set to manual mode, skipping auto-processing")

    else:
        # Unknown mode, default to immediate
        logger.warning(
            f"Unknown processing mode '{instance.rag_processing_mode}' "
            f"for document {instance.id}, defaulting to immediate"
        )
        _trigger_immediate_processing(instance)


def _trigger_immediate_processing(document: Document):
    """
    Trigger immediate RAG processing via Celery task.

    Falls back to synchronous processing if Celery is not available.

    Args:
        document: Document instance to process
    """
    try:
        # Try to import and use Celery task
        from rag.tasks import process_document_rag

        # Trigger async task
        task = process_document_rag.delay(document.id)

        logger.info(
            f"Triggered async RAG processing for document {document.id} "
            f"(task ID: {task.id})"
        )

    except ImportError:
        # Celery not available, fall back to synchronous processing
        logger.warning(
            f"Celery not available, processing document {document.id} synchronously"
        )
        _process_synchronously(document)

    except Exception as e:
        # Celery task failed to queue
        logger.error(
            f"Failed to queue RAG processing for document {document.id}: {e}",
            exc_info=True
        )

        # Update document status to failed
        document.rag_status = "failed"
        document.rag_error_message = f"Failed to queue processing: {str(e)}"
        document.save(update_fields=["rag_status", "rag_error_message"])


def _process_synchronously(document: Document):
    """
    Process document synchronously (fallback when Celery unavailable).

    WARNING: This blocks the request! Only use in development.

    Args:
        document: Document instance to process
    """
    try:
        from django.db import transaction
        from ingest.extraction.pdf_processor import PDFProcessor
        from rag.models import DocumentChunk
        from rag.services import ChunkingService, EmbeddingService

        # Update status
        document.rag_status = "processing"
        document.save(update_fields=["rag_status"])

        # Initialize services
        chunking_service = ChunkingService()
        embedding_service = EmbeddingService()

        # Extract text
        processor = PDFProcessor()
        text_content = processor.extract_text(document.file.path)

        if not text_content:
            raise ValueError("No text extracted from document")

        # Chunk
        chunks = chunking_service.chunk_text(text_content)

        # Create chunk objects
        chunk_objects = []
        for chunk in chunks:
            chunk_objects.append(
                DocumentChunk(
                    document=document,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    token_count=chunk.token_count,
                    char_count=chunk.char_count,
                )
            )

        # Save chunks
        with transaction.atomic():
            DocumentChunk.objects.bulk_create(chunk_objects)

        # Generate embeddings
        texts = [chunk.content for chunk in chunk_objects]
        embeddings = embedding_service.embed_texts(texts)

        for chunk, embedding_result in zip(chunk_objects, embeddings):
            if embedding_result:
                chunk.embedding = embedding_result.embedding
                chunk.save(update_fields=["embedding"])

        # Update status
        from django.utils import timezone
        document.rag_status = "completed"
        document.rag_processed_at = timezone.now()
        document.save(update_fields=["rag_status", "rag_processed_at"])

        logger.info(f"Successfully processed document {document.id} synchronously")

    except Exception as e:
        logger.error(
            f"Synchronous processing failed for document {document.id}: {e}",
            exc_info=True
        )

        document.rag_status = "failed"
        document.rag_error_message = str(e)
        document.save(update_fields=["rag_status", "rag_error_message"])
