"""
Celery tasks for asynchronous RAG processing.

Handles document chunking and embedding generation in background.
"""

import logging
from datetime import datetime
from typing import Optional

from django.core.mail import mail_admins
from django.db import transaction
from django.utils import timezone

try:
    from celery import shared_task
    HAS_CELERY = True
except ImportError:
    # Fallback decorator for development without Celery
    HAS_CELERY = False
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from ingest.models import Document
from ingest.extraction.pdf_processor import PDFProcessor
from rag.models import DocumentChunk
from rag.services import ChunkingService, EmbeddingService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)  # Retry after 5 minutes
def process_document_rag(self, document_id: int, skip_embeddings: bool = False):
    """
    Process a document for RAG: extract text, chunk, and generate embeddings.

    Args:
        document_id: ID of document to process
        skip_embeddings: If True, only chunk without generating embeddings

    Returns:
        Dict with processing results
    """
    try:
        document = Document.objects.get(id=document_id)

        # Update status to processing
        document.rag_status = "processing"
        document.save(update_fields=["rag_status"])

        logger.info(f"Starting RAG processing for document {document_id}: {document.filename}")

        # Initialize services
        chunking_service = ChunkingService()
        embedding_service = EmbeddingService() if not skip_embeddings else None

        # Extract text
        text_content = _extract_text(document)

        if not text_content:
            raise ValueError("No text extracted from document")

        # Chunk the text
        chunks = chunking_service.chunk_text(text_content)
        logger.info(f"Created {len(chunks)} chunks for document {document_id}")

        # Delete existing chunks (if reprocessing)
        DocumentChunk.objects.filter(document=document).delete()

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
        if embedding_service:
            logger.info(f"Generating embeddings for {len(chunk_objects)} chunks...")
            _generate_embeddings(chunk_objects, embedding_service, batch_size=10)

        # Update document status to completed
        document.rag_status = "completed"
        document.rag_processed_at = timezone.now()
        document.rag_error_message = ""
        document.save(update_fields=["rag_status", "rag_processed_at", "rag_error_message"])

        logger.info(f"Successfully processed document {document_id}")

        return {
            "success": True,
            "document_id": document_id,
            "chunks_created": len(chunk_objects),
            "embeddings_generated": len(chunk_objects) if embedding_service else 0,
        }

    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {"success": False, "error": "Document not found"}

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)

        # Update document status to failed
        try:
            document = Document.objects.get(id=document_id)
            document.rag_status = "failed"
            document.rag_error_message = str(e)
            document.rag_retry_count += 1
            document.save(update_fields=["rag_status", "rag_error_message", "rag_retry_count"])

            # Notify admins
            _notify_admin_on_failure(document, e)

        except Exception as save_error:
            logger.error(f"Failed to update document status: {save_error}")

        # Retry task if not max retries yet
        if document.rag_retry_count < 3:
            logger.info(f"Retrying document {document_id} (attempt {document.rag_retry_count + 1})")
            raise self.retry(exc=e)

        return {
            "success": False,
            "document_id": document_id,
            "error": str(e),
        }


@shared_task
def process_batch_documents(mode: str = "batch"):
    """
    Process all pending documents scheduled for batch processing.

    This task should be run nightly via cron.

    Args:
        mode: Processing mode filter ("batch" or "pending")

    Returns:
        Dict with batch processing results
    """
    logger.info(f"Starting batch RAG processing (mode: {mode})")

    # Get all pending documents scheduled for batch processing
    documents = Document.objects.filter(
        rag_status="pending",
        rag_processing_mode=mode
    )

    total = documents.count()
    logger.info(f"Found {total} documents to process")

    results = {
        "total": total,
        "success": 0,
        "failed": 0,
        "errors": [],
    }

    for doc in documents:
        try:
            # Process document (synchronously in this batch task)
            result = process_document_rag.apply(args=[doc.id], kwargs={"skip_embeddings": False})

            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "error": result.get("error"),
                })

        except Exception as e:
            logger.error(f"Error in batch processing document {doc.id}: {e}")
            results["failed"] += 1
            results["errors"].append({
                "document_id": doc.id,
                "filename": doc.filename,
                "error": str(e),
            })

    logger.info(
        f"Batch processing completed: {results['success']}/{total} successful, "
        f"{results['failed']} failed"
    )

    # Notify admins if there were failures
    if results["failed"] > 0:
        _notify_admin_batch_summary(results)

    return results


def _extract_text(document: Document) -> str:
    """Extract text from document file."""
    if not document.file:
        return ""

    try:
        processor = PDFProcessor()
        text = processor.extract_text(document.file.path)
        return text
    except Exception as e:
        logger.error(f"Error extracting text from {document.file.path}: {e}")
        raise


def _generate_embeddings(chunks: list, embedding_service: EmbeddingService, batch_size: int = 10):
    """Generate embeddings for chunks in batches."""
    texts = [chunk.content for chunk in chunks]

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_chunks = chunks[i:i + batch_size]

        logger.info(f"Processing embedding batch {i//batch_size + 1}: {len(batch)} chunks")

        embeddings = embedding_service.embed_texts(batch)

        # Update chunks with embeddings
        for chunk, embedding_result in zip(batch_chunks, embeddings):
            if embedding_result:
                chunk.embedding = embedding_result.embedding
                chunk.save(update_fields=["embedding"])
            else:
                logger.warning(f"Failed to generate embedding for chunk {chunk.chunk_index}")
                raise ValueError(f"Embedding generation failed for chunk {chunk.chunk_index}")


def _notify_admin_on_failure(document: Document, error: Exception):
    """Send email notification to admins when RAG processing fails."""
    subject = f"RAG Processing Failed: {document.filename}"

    message = f"""
RAG processing failed for document:

Document ID: {document.id}
Filename: {document.filename}
Owner: {document.owner.username} ({document.owner.email})
Upload date: {document.uploaded_at}
Retry count: {document.rag_retry_count}

Error:
{str(error)}

Document URL: /admin/ingest/document/{document.id}/change/

Please investigate and retry if necessary.
"""

    try:
        mail_admins(subject, message, fail_silently=False)
        logger.info(f"Admin notification sent for failed document {document.id}")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")


def _notify_admin_batch_summary(results: dict):
    """Send batch processing summary to admins."""
    subject = f"RAG Batch Processing Summary: {results['failed']} failures"

    errors_text = "\n".join([
        f"- Document {err['document_id']} ({err['filename']}): {err['error']}"
        for err in results["errors"]
    ])

    message = f"""
Nightly RAG batch processing completed with errors:

Total documents: {results['total']}
Successful: {results['success']}
Failed: {results['failed']}

Failed documents:
{errors_text}

Please review the failed documents in the admin interface.
"""

    try:
        mail_admins(subject, message, fail_silently=False)
        logger.info("Batch processing summary sent to admins")
    except Exception as e:
        logger.error(f"Failed to send batch summary: {e}")
