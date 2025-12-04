"""
Document Processing Service - handles file upload, parsing, and database operations.
Coordinates between file handling, AI parsing, and data persistence.
"""

import logging
import os
import tempfile
from typing import Any, Dict, Optional

from django.contrib.auth.models import User
from django.db import transaction

from ingest.models import Document, FinancialStatement
from .parser_service import PDFParserService

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """Service for processing uploaded financial documents."""

    def __init__(self, ai_provider: str = "openai"):
        """
        Initialize document processing service.

        Args:
            ai_provider: AI provider to use ("openai" or "claude")
        """
        self.ai_provider = ai_provider
        self.parser = PDFParserService(provider=ai_provider)
        logger.info(f"Initialized DocumentProcessingService with provider: {ai_provider}")

    def process_uploaded_file(self, user: User, uploaded_file) -> Dict[str, Any]:
        """
        Process an uploaded PDF file: save temporarily, parse, and store in database.

        Args:
            user: User who uploaded the file
            uploaded_file: Django UploadedFile object

        Returns:
            Dict with processing result:
            {
                "file": str,
                "success": bool,
                "error": str | None,
                "year": int | None,
                "doc_type": str | None,
                "document_id": int | None,
                "statement_id": int | None,
                "parsed_data": dict | None
            }
        """
        result = {
            "file": getattr(uploaded_file, "name", "unknown"),
            "success": False,
            "error": None,
            "year": None,
            "doc_type": None,
            "document_id": None,
            "statement_id": None,
            "parsed_data": None
        }

        tmp_path = None

        try:
            # Step 1: Save file temporarily
            logger.info(f"Processing file: {uploaded_file.name}")
            tmp_path = self._save_temp_file(uploaded_file)

            # Step 2: Parse PDF with AI
            parsed = self.parser.parse_pdf(tmp_path)

            if not parsed.get("success"):
                result["error"] = parsed.get("error") or "Parsing failed"
                logger.warning(f"Parsing failed for {uploaded_file.name}: {result['error']}")
                return result

            doc_type = parsed.get("doc_type")
            year = parsed.get("year")
            data = parsed.get("data") or {}
            scale = parsed.get("scale", "units")

            # Validate critical fields
            if not doc_type or not isinstance(year, int):
                result["error"] = f"Invalid parsing result: doc_type={doc_type}, year={year}"
                logger.warning(result["error"])
                return result

            # Step 3: Save to database (atomic transaction)
            doc, fs = self._save_to_database(
                user=user,
                uploaded_file=uploaded_file,
                year=year,
                doc_type=doc_type,
                scale=scale,
                data=data
            )

            # Step 4: Build success result
            result.update({
                "success": True,
                "year": year,
                "doc_type": doc_type,
                "document_id": doc.id,
                "statement_id": fs.id,
                "parsed_data": data,
                "scale": scale
            })

            logger.info(
                f"Successfully processed {uploaded_file.name}: "
                f"doc_id={doc.id}, year={year}, type={doc_type}"
            )

            return result

        except Exception as e:
            error_msg = f"Error processing {uploaded_file.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result["error"] = error_msg
            return result

        finally:
            # Cleanup temporary file
            if tmp_path:
                self._cleanup_temp_file(tmp_path)

    def reprocess_document(self, document_id: int, user: User) -> Dict[str, Any]:
        """
        Re-parse an existing document.

        Args:
            document_id: ID of the document to reprocess
            user: User who owns the document

        Returns:
            Dict with processing result
        """
        try:
            doc = Document.objects.get(id=document_id, owner=user)

            if not doc.file or not os.path.exists(doc.file.path):
                return {
                    "success": False,
                    "error": "Document file not found"
                }

            # Parse the file
            parsed = self.parser.parse_pdf(doc.file.path)

            if not parsed.get("success"):
                return {
                    "success": False,
                    "error": parsed.get("error") or "Parsing failed"
                }

            doc_type = parsed.get("doc_type")
            year = parsed.get("year")
            data = parsed.get("data") or {}
            scale = parsed.get("scale", "units")

            if not doc_type or not isinstance(year, int):
                return {
                    "success": False,
                    "error": f"Invalid parsing result: doc_type={doc_type}, year={year}"
                }

            # Update document and financial statement
            with transaction.atomic():
                doc.doc_type = doc_type
                doc.year = year
                doc.analyzed = True
                doc.save()

                fs, _ = FinancialStatement.objects.get_or_create(
                    user=user,
                    year=year,
                    defaults={"document": doc}
                )

                fs.document = doc
                fs.scale = scale

                if doc_type == "income_statement":
                    fs.income = data
                elif doc_type == "balance_sheet":
                    fs.balance = data

                fs.save()

            logger.info(f"Successfully reprocessed document {document_id}")

            return {
                "success": True,
                "year": year,
                "doc_type": doc_type,
                "document_id": doc.id,
                "statement_id": fs.id,
                "parsed_data": data
            }

        except Document.DoesNotExist:
            return {
                "success": False,
                "error": "Document not found"
            }
        except Exception as e:
            logger.error(f"Error reprocessing document {document_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _save_temp_file(self, uploaded_file) -> str:
        """Save uploaded file to temporary location."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            return tmp.name

    def _cleanup_temp_file(self, path: str):
        """Remove temporary file."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            logger.warning(f"Failed to remove temp file {path}: {e}")

    @transaction.atomic
    def _save_to_database(
        self,
        user: User,
        uploaded_file,
        year: int,
        doc_type: str,
        scale: str,
        data: Dict[str, Any]
    ) -> tuple:
        """
        Save document and financial statement to database atomically.

        Returns:
            Tuple of (Document, FinancialStatement)
        """
        # Create Document record
        doc = Document.objects.create(
            owner=user,
            file=uploaded_file,
            year=year,
            doc_type=doc_type,
            analyzed=True
        )

        # Get or create FinancialStatement for this year
        fs, created = FinancialStatement.objects.get_or_create(
            user=user,
            year=year,
            defaults={"document": doc}
        )

        # Update financial statement
        fs.document = doc
        fs.scale = scale

        # Save data based on document type
        if doc_type == "income_statement":
            fs.income = data
        elif doc_type == "balance_sheet":
            fs.balance = data

        fs.save()

        logger.debug(
            f"Saved to DB: Document(id={doc.id}), "
            f"FinancialStatement(id={fs.id}, created={created})"
        )

        return doc, fs
