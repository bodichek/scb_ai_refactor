"""
Tests for vision-based financial PDF extraction
"""
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from ingest.extraction.pdf_processor import PDFProcessor
from ingest.extraction.claude_extractor import FinancialExtractor
from ingest.models import Document, FinancialStatement


class PDFProcessorTestCase(TestCase):
    """Tests for PDFProcessor"""

    def setUp(self):
        self.processor = PDFProcessor(dpi=300)

    def test_processor_initialization(self):
        """Test PDFProcessor initializes with correct DPI"""
        self.assertEqual(self.processor.dpi, 300)

    @patch('ingest.extraction.pdf_processor.fitz')
    def test_pdf_to_png_conversion(self, mock_fitz):
        """Test PDF to PNG conversion"""
        # Mock PyMuPDF
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pix = MagicMock()

        mock_fitz.open.return_value = mock_doc
        mock_doc.page_count = 1
        mock_doc.load_page.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pix
        mock_pix.tobytes.return_value = b'PNG_BYTES_HERE'

        # Test conversion
        result = self.processor.pdf_to_png("test.pdf", page_num=0)

        # Assertions
        mock_fitz.open.assert_called_once_with("test.pdf")
        mock_doc.load_page.assert_called_once_with(0)
        self.assertEqual(result, b'PNG_BYTES_HERE')
        mock_doc.close.assert_called_once()

    @patch('ingest.extraction.pdf_processor.Path')
    @patch('ingest.extraction.pdf_processor.settings')
    def test_save_png_local(self, mock_settings, mock_path_class):
        """Test saving PNG to local filesystem"""
        # Mock settings
        mock_settings.BASE_DIR = Path("/fake/base/dir")

        # Mock file operations
        mock_output_dir = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.relative_to.return_value = Path("ingest/media/extracted_tables/test.png")

        with patch('builtins.open', create=True) as mock_open:
            with patch('ingest.extraction.pdf_processor.uuid') as mock_uuid:
                mock_uuid.uuid4.return_value = "test-uuid"

                png_bytes = b'PNG_DATA'
                result = self.processor.save_png_local(png_bytes)

                # Should have tried to write file
                self.assertIsInstance(result, str)


class FinancialExtractorTestCase(TestCase):
    """Tests for FinancialExtractor"""

    def setUp(self):
        self.extractor = FinancialExtractor()

    def test_extractor_initialization(self):
        """Test FinancialExtractor initializes correctly"""
        self.assertEqual(self.extractor.model, "claude-3-5-sonnet-20241022")
        self.assertEqual(self.extractor.max_tokens, 2048)

    def test_clean_json_response_with_markdown(self):
        """Test cleaning JSON from markdown code blocks"""
        response = '```json\n{"key": "value"}\n```'
        result = self.extractor._clean_json_response(response)
        self.assertEqual(result, '{"key": "value"}')

    def test_clean_json_response_without_markdown(self):
        """Test cleaning JSON without markdown"""
        response = '{"key": "value"}'
        result = self.extractor._clean_json_response(response)
        self.assertEqual(result, '{"key": "value"}')

    @patch('ingest.extraction.claude_extractor.anthropic.Anthropic')
    def test_extract_from_png_success(self, mock_anthropic):
        """Test successful extraction from PNG"""
        # Mock Claude API response
        mock_client = Mock()
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = '''```json
        {
            "doc_type": "income_statement",
            "year": 2023,
            "scale": "thousands",
            "extracted_data": {
                "revenue_products_services": 20037,
                "revenue_goods": 330
            },
            "confidence": 0.92
        }
        ```'''

        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.return_value = mock_client

        # Create new extractor with mocked client
        extractor = FinancialExtractor()
        extractor.client = mock_client

        # Test extraction
        png_bytes = b'FAKE_PNG_BYTES'
        result = extractor.extract_from_png(png_bytes)

        # Assertions
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("doc_type"), "income_statement")
        self.assertEqual(result.get("year"), 2023)
        self.assertEqual(result.get("confidence"), 0.92)
        self.assertIsNotNone(result.get("extracted_data"))

    @patch('ingest.extraction.claude_extractor.anthropic.Anthropic')
    def test_extract_from_png_json_error(self, mock_anthropic):
        """Test extraction with invalid JSON response"""
        # Mock Claude API response with invalid JSON
        mock_client = Mock()
        mock_message = Mock()
        mock_content = Mock()
        mock_content.text = 'INVALID JSON'

        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.return_value = mock_client

        # Create new extractor with mocked client
        extractor = FinancialExtractor()
        extractor.client = mock_client

        # Test extraction
        png_bytes = b'FAKE_PNG_BYTES'
        result = extractor.extract_from_png(png_bytes)

        # Assertions
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)


class IntegrationTestCase(TestCase):
    """Integration tests for the full extraction pipeline"""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_document_creation(self):
        """Test creating a Document"""
        doc = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("test.pdf", b"file_content"),
            year=2023,
            doc_type="income_statement",
            analyzed=True
        )

        self.assertEqual(doc.year, 2023)
        self.assertEqual(doc.doc_type, "income_statement")
        self.assertTrue(doc.analyzed)

    def test_financial_statement_creation(self):
        """Test creating a FinancialStatement"""
        doc = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("test.pdf", b"file_content"),
            year=2023,
            doc_type="income_statement",
            analyzed=True
        )

        fs = FinancialStatement.objects.create(
            user=self.user,
            year=2023,
            document=doc,
            income={"revenue_products_services": 20037},
            scale="thousands",
            confidence=0.92,
            local_image_path="ingest/media/extracted_tables/test.png"
        )

        self.assertEqual(fs.year, 2023)
        self.assertEqual(fs.scale, "thousands")
        self.assertEqual(fs.confidence, 0.92)
        self.assertIsNotNone(fs.local_image_path)
        self.assertEqual(fs.income["revenue_products_services"], 20037)

    def test_unique_constraint_per_user_year(self):
        """Test that only one FinancialStatement per user/year is allowed"""
        doc1 = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("test1.pdf", b"file_content"),
            year=2023,
            doc_type="income_statement",
            analyzed=True
        )

        fs1 = FinancialStatement.objects.create(
            user=self.user,
            year=2023,
            document=doc1
        )

        # Try to create another for same user/year
        doc2 = Document.objects.create(
            owner=self.user,
            file=SimpleUploadedFile("test2.pdf", b"file_content"),
            year=2023,
            doc_type="income_statement",
            analyzed=True
        )

        # Should raise IntegrityError
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            FinancialStatement.objects.create(
                user=self.user,
                year=2023,
                document=doc2
            )
