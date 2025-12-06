"""
Management command to process documents for RAG.

Chunks existing documents and generates embeddings.
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction

from ingest.models import Document
from ingest.extraction.pdf_processor import PDFProcessor
from rag.models import DocumentChunk
from rag.services import ChunkingService, EmbeddingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process documents for RAG: extract text, chunk, and generate embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=int,
            help='Process specific document by ID',
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Reprocess documents that already have chunks',
        )
        parser.add_argument(
            '--skip-embeddings',
            action='store_true',
            help='Skip embedding generation (only chunk)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of chunks to process in one batch',
        )

    def handle(self, *args, **options):
        document_id = options.get('document_id')
        reprocess = options.get('reprocess')
        skip_embeddings = options.get('skip_embeddings')
        batch_size = options.get('batch_size')

        # Initialize services
        chunking_service = ChunkingService()
        embedding_service = EmbeddingService() if not skip_embeddings else None

        # Get documents to process
        if document_id:
            documents = Document.objects.filter(id=document_id)
            if not documents.exists():
                self.stdout.write(self.style.ERROR(f'Document {document_id} not found'))
                return
        else:
            documents = Document.objects.all()

            # Exclude documents that already have chunks (unless reprocessing)
            if not reprocess:
                processed_doc_ids = DocumentChunk.objects.values_list('document_id', flat=True).distinct()
                documents = documents.exclude(id__in=processed_doc_ids)

        total = documents.count()
        self.stdout.write(f'Processing {total} documents...')

        processed_count = 0
        error_count = 0

        for doc in documents:
            try:
                self.stdout.write(f'\nProcessing: {doc.filename} (ID: {doc.id})')

                # Extract text from document
                text_content = self._extract_text(doc)

                if not text_content:
                    self.stdout.write(self.style.WARNING('  No text extracted, skipping'))
                    continue

                # Chunk the text
                chunks = chunking_service.chunk_text(text_content)
                self.stdout.write(f'  Created {len(chunks)} chunks')

                # Delete existing chunks if reprocessing
                if reprocess:
                    deleted = DocumentChunk.objects.filter(document=doc).delete()[0]
                    if deleted > 0:
                        self.stdout.write(f'  Deleted {deleted} existing chunks')

                # Create chunk objects
                chunk_objects = []
                for chunk in chunks:
                    chunk_objects.append(
                        DocumentChunk(
                            document=doc,
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
                    self.stdout.write('  Generating embeddings...')
                    self._generate_embeddings(chunk_objects, embedding_service, batch_size)

                processed_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Processed successfully'))

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  ERROR: {str(e)}'))
                logger.error(f'Error processing document {doc.id}: {e}', exc_info=True)

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(f'Processed: {processed_count}/{total}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))

    def _extract_text(self, document: Document) -> str:
        """Extract text from document file."""
        if not document.file:
            return ""

        try:
            # Use PDF processor to extract text
            processor = PDFProcessor()
            text = processor.extract_text(document.file.path)
            return text
        except Exception as e:
            logger.error(f'Error extracting text from {document.file.path}: {e}')
            return ""

    def _generate_embeddings(self, chunks: list, embedding_service: EmbeddingService, batch_size: int):
        """Generate embeddings for chunks."""
        texts = [chunk.content for chunk in chunks]

        # Generate embeddings in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_chunks = chunks[i:i + batch_size]

            self.stdout.write(f'    Batch {i//batch_size + 1}: {len(batch)} chunks')

            embeddings = embedding_service.embed_texts(batch)

            # Update chunks with embeddings
            for chunk, embedding_result in zip(batch_chunks, embeddings):
                if embedding_result:
                    chunk.embedding = embedding_result.embedding
                    chunk.save(update_fields=['embedding'])
                else:
                    self.stdout.write(self.style.WARNING(f'      Failed to generate embedding for chunk {chunk.chunk_index}'))
