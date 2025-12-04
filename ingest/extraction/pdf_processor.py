"""
PDF to PNG conversion using PyMuPDF (fitz)
Converts PDF pages to PNG images for Claude vision API
"""
import os
import uuid
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF to PNG conversion"""

    def __init__(self, dpi: int = 300):
        """
        Initialize PDF processor

        Args:
            dpi: Resolution for PNG conversion (default: 300)
        """
        self.dpi = dpi

    def pdf_to_png(self, pdf_path: str, page_num: int = 0) -> bytes:
        """
        Convert PDF page to PNG bytes

        Args:
            pdf_path: Path to PDF file
            page_num: Page number to convert (0-indexed)

        Returns:
            PNG image as bytes

        Raises:
            Exception: If PDF conversion fails
        """
        try:
            doc = fitz.open(pdf_path)

            if page_num >= doc.page_count:
                logger.warning(f"Page {page_num} not found, using page 0")
                page_num = 0

            page = doc.load_page(page_num)

            # Convert to pixmap with specified DPI
            # zoom factor = dpi / 72 (72 is default DPI)
            zoom = self.dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            png_bytes = pix.tobytes("png")

            doc.close()

            logger.info(f"Converted PDF page {page_num} to PNG ({len(png_bytes)} bytes)")
            return png_bytes

        except Exception as e:
            logger.error(f"Failed to convert PDF to PNG: {e}")
            raise

    def save_png_local(
        self,
        png_bytes: bytes,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Save PNG bytes to local file system

        Args:
            png_bytes: PNG image as bytes
            output_dir: Directory to save PNG (default: ingest/media/extracted_tables/)

        Returns:
            Path to saved PNG file (relative to project root)
        """
        if output_dir is None:
            # Default to ingest/media/extracted_tables/
            from django.conf import settings
            base_dir = Path(settings.BASE_DIR)
            output_dir = base_dir / "ingest" / "media" / "extracted_tables"
        else:
            output_dir = Path(output_dir)

        # Ensure directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        filename = f"{uuid.uuid4()}.png"
        file_path = output_dir / filename

        # Write PNG bytes
        with open(file_path, 'wb') as f:
            f.write(png_bytes)

        # Return relative path
        relative_path = str(file_path.relative_to(Path(settings.BASE_DIR)))
        logger.info(f"Saved PNG to {relative_path}")

        return relative_path

    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        Get basic PDF information

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with PDF metadata
        """
        try:
            doc = fitz.open(pdf_path)
            info = {
                "page_count": doc.page_count,
                "metadata": doc.metadata,
            }
            doc.close()
            return info
        except Exception as e:
            logger.error(f"Failed to get PDF info: {e}")
            return {"page_count": 0, "metadata": {}}
