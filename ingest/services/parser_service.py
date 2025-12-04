"""
PDF Parser Service - orchestrates PDF rendering and AI parsing.
Uses AI providers (OpenAI or Claude) to extract structured financial data.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from .ai_providers import get_ai_provider

logger = logging.getLogger(__name__)


class PDFParserService:
    """Service for parsing financial PDF documents."""

    # Default parsing prompt
    DEFAULT_PROMPT = """
You are an AI parser for Czech financial PDF statements.
Your ONLY job is to return valid JSON that conforms exactly to this schema:

{
  "doc_type": "income_statement" | "balance_sheet",
  "year": number,
  "scale": "units" | "thousands",
  "data": {
      "revenue_products_services": number|null,
      "revenue_goods": number|null,
      "revenue": number|null,

      "cogs_goods": number|null,
      "cogs_materials": number|null,
      "cogs": number|null,
      "services": number|null,

      "personnel_wages": number|null,
      "personnel_insurance": number|null,
      "taxes_fees": number|null,
      "depreciation": number|null,
      "other_operating_costs": number|null,
      "other_operating_revenue": number|null,

      "financial_revenue": number|null,
      "financial_costs": number|null,
      "income_tax": number|null,
      "ebit": number|null,
      "net_profit": number|null,

      "receivables": number|null,
      "inventory": number|null,
      "short_term_liabilities": number|null,
      "cash": number|null,
      "tangible_assets": number|null,
      "total_assets": number|null,
      "equity": number|null,
      "total_liabilities": number|null,
      "trade_payables": number|null,
      "short_term_loans": number|null,
      "long_term_loans": number|null
  }
}

RULES:
- Read ONLY values from the "běžné období" (current period) column
- Ignore "minulé období" (previous period)
- Use EXACT visible layout of the tables (not OCR guesses)
- If a value cannot be read with confidence → return null
- Do not compute or calculate anything
- Return ONLY valid JSON, no explanation or markdown
- All numeric values should be numbers, not strings
"""

    def __init__(
        self,
        provider: str = "openai",
        max_pages: int = 3,
        render_dpi: int = 220,
        prompt: Optional[str] = None
    ):
        """
        Initialize parser service.

        Args:
            provider: AI provider to use ("openai" or "claude")
            max_pages: Maximum number of PDF pages to process
            render_dpi: DPI for PDF rendering
            prompt: Custom parsing prompt (uses default if None)
        """
        self.provider_name = provider
        self.max_pages = max_pages
        self.render_dpi = render_dpi
        self.prompt = prompt or self.DEFAULT_PROMPT

        logger.info(f"Initialized PDFParserService with provider: {provider}")

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse a financial PDF document.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dict with structure:
            {
                "doc_type": str,
                "year": int,
                "scale": str,
                "data": dict,
                "success": bool,
                "error": str | None
            }
        """
        default_result = {
            "doc_type": None,
            "year": None,
            "scale": "units",
            "data": {},
            "success": False,
            "error": None
        }

        try:
            # Step 1: Render PDF to images
            logger.info(f"Starting PDF parsing: {pdf_path}")
            images = self._render_pdf(pdf_path)

            if not images:
                error_msg = "No images produced from PDF"
                logger.error(error_msg)
                default_result["error"] = error_msg
                return default_result

            # Step 2: Get AI provider and parse
            provider = get_ai_provider(self.provider_name)
            parsed_data = provider.parse_document(images, self.prompt)

            # Step 3: Validate and normalize
            result = self._validate_response(parsed_data)
            result["success"] = True

            logger.info(f"Successfully parsed PDF: {pdf_path} - Year: {result['year']}, Type: {result['doc_type']}")
            return result

        except Exception as e:
            error_msg = f"Failed to parse PDF: {str(e)}"
            logger.error(error_msg, exc_info=True)
            default_result["error"] = error_msg
            return default_result

    def _render_pdf(self, pdf_path: str) -> list:
        """Render PDF pages to PNG images."""
        try:
            import fitz
        except ImportError:
            raise ImportError("PyMuPDF (fitz) is required. Install with: pip install pymupdf")

        images = []
        try:
            doc = fitz.open(pdf_path)
            page_count = min(doc.page_count, self.max_pages)

            logger.debug(f"Rendering {page_count} pages from PDF")

            for i in range(page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=self.render_dpi)
                images.append(pix.tobytes("png"))

            doc.close()

        except Exception as e:
            logger.error(f"Failed to render PDF: {e}", exc_info=True)
            raise

        return images

    def _validate_response(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize the parsed response."""
        # Validate document type
        doc_type = parsed.get("doc_type")
        if doc_type not in ("income_statement", "balance_sheet"):
            doc_type = None
            logger.warning(f"Invalid doc_type: {parsed.get('doc_type')}")

        # Validate year
        year = parsed.get("year")
        if not isinstance(year, int) or not (1900 <= year <= 2100):
            year = None
            logger.warning(f"Invalid year: {parsed.get('year')}")

        # Validate scale
        scale = parsed.get("scale", "units")
        if scale not in ("units", "thousands"):
            scale = "units"
            logger.warning(f"Invalid scale: {parsed.get('scale')}, defaulting to 'units'")

        # Get data
        data = parsed.get("data") or {}

        return {
            "doc_type": doc_type,
            "year": year,
            "scale": scale,
            "data": data,
            "success": True,
            "error": None
        }
