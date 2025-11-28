# ingest/ai_parser_refactored.py

"""
Universal AI parser for Czech financial PDF statements.

- Sends full PDF (OCR + layout) to OpenAI Responses API
- Detects doc_type, year, scale
- Extracts only the "bezne obdobi" (current period) column
- Returns unified dict: {"doc_type", "year", "scale", "data"}
"""

import json
import logging
from typing import Any, Dict

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
MODEL = getattr(settings, "OPENAI_MODEL", None) or "gpt-4o-mini"


# --------------------------------------------------------------------
# PROMPT – čistý text, bez diakritiky, aby nebyly potize s encodingem
# --------------------------------------------------------------------
PROMPT_UNIVERSAL = """
You are an AI parser for Czech financial PDF documents
("vykaz zisku a ztraty" = income statement, "rozvaha" = balance sheet).

Your task:

1) Read the entire PDF (OCR + layout).
2) Decide the document type:

   - "income_statement"  for "vykaz zisku a ztraty"
   - "balance_sheet"     for "rozvaha"

3) Detect the report year (for example 2019..2025).

4) Detect the scale:
   - If the document mentions "v tis. Kc", "v tisicich Kc"
     or similar phrase meaning "in thousands CZK", then:
       "scale": "thousands"
   - Otherwise:
       "scale": "units"

5) Extract ONLY values from the column for the current period
   ("bezne obdobi" or equivalent). Ignore any previous period columns.

6) Fill a JSON object with this structure:

{
  "doc_type": "income_statement" or "balance_sheet",
  "year": 2023,
  "scale": "units" or "thousands",
  "data": {
    ... numeric fields or null ...
  }
}

Allowed fields inside "data":

If doc_type = "income_statement", you MAY include some or all of:
- "revenue_products_services"
- "revenue_goods"
- "revenue"

- "cogs_goods"
- "cogs_materials"
- "cogs"

- "services"

- "personnel_wages"
- "personnel_insurance"

- "taxes_fees"
- "depreciation"
- "other_operating_costs"
- "other_operating_revenue"

- "financial_revenue"
- "financial_costs"

- "income_tax"
- "ebit"
- "net_profit"

If doc_type = "balance_sheet", you MAY include some or all of:
- "receivables"
- "inventory"
- "short_term_liabilities"
- "cash"

- "tangible_assets"
- "total_assets"
- "equity"
- "total_liabilities"

- "trade_payables"
- "short_term_loans"
- "long_term_loans"

RULES:

- Use ONLY numbers or null as values.
- Do NOT compute any derived metrics.
- Do NOT return percentages.
- Do NOT normalize or scale the values, just copy numbers as printed in
  the selected "current period" column.
- If a field cannot be found, use null or simply omit the field.
- The JSON must be syntactically valid.

VERY IMPORTANT:

- Return a SINGLE JSON object only.
- Do NOT include any explanation, comments, Markdown, or code fences.
- Do NOT wrap the JSON in ```json ... ``` or any other text.
"""


# --------------------------------------------------------------------
# Helper: extract text from Responses API
# --------------------------------------------------------------------
def _extract_output_text(resp) -> str:
    """
    Extract textual content from the Responses API result.

    For current openai>=1.x the shape is usually:
      resp.output[0].content[0].text.value
    We keep this defensive so that small API changes do not crash parsing.
    """
    out = getattr(resp, "output", None)
    if out:
        try:
            content = out[0].content[0].text
            return getattr(content, "value", content)
        except Exception:
            logger.warning("Failed to read resp.output[0].content[0].text", exc_info=True)

    # Fallback if the client exposes output_text directly
    if hasattr(resp, "output_text"):
        return resp.output_text

    raise ValueError("OpenAI response does not contain readable text.")




# --------------------------------------------------------------------
# Helper: clean JSON from Markdown / garbage
# --------------------------------------------------------------------
def _clean_json_text(raw: str) -> str:
    """
    Strip code fences and extra text so that json.loads() can work.

    - removes ```json ... ``` wrappers
    - trims everything outside the outermost { ... }
    """
    if not raw:
        return ""

    text = raw.strip()

    # remove ```json / ``` fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line if it is a fence
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        # drop last line if it is a fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # keep only from first '{' to last '}'
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return text.strip()


# --------------------------------------------------------------------
# Main entry point for the rest of the app
# --------------------------------------------------------------------
def parse_financial_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Send the given PDF path to OpenAI and return a dict:
    {
      "doc_type": "income_statement" | "balance_sheet" | None,
      "year": int | None,
      "scale": "units" | "thousands",
      "data": { ... }  # raw fields, no derived metrics
    }
    """
    try:
        # 1) Upload the PDF
        with open(pdf_path, "rb") as f:
            file_obj = client.files.create(file=f, purpose="user_data")

        # 2) Call Responses API synchronously (no poll, no wait)
        resp = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT_UNIVERSAL},
                        {"type": "input_file", "file_id": file_obj.id},
                    ],
                }
            ],
            temperature=0,
        )

        # 3) Extract raw text from the response
        raw_text = _extract_output_text(resp)

        # 4) Try to decode JSON (with cleaning)
        cleaned = _clean_json_text(raw_text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                "JSON decode error while parsing financial PDF: %s\nRAW OUTPUT:\n%s",
                e,
                raw_text,
                exc_info=True,
            )
            # fall through to general exception handler below
            raise
        print("\n================ PARSED JSON FROM OPENAI ================")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("=========================================================\n")

        doc_type = data.get("doc_type")
        year = data.get("year")
        scale = data.get("scale", "units")
        payload = data.get("data", {}) or {}

        # basic sanity check – at least doc_type + year must exist
        if doc_type not in ("income_statement", "balance_sheet") or not isinstance(
            year, int
        ):
            raise ValueError(f"Invalid doc_type/year in parsed data: {doc_type!r}/{year!r}")

        return {
            "doc_type": doc_type,
            "year": year,
            "scale": scale,
            "data": payload,
        }

    except Exception as e:
        # One central place, aby se neshazovala aplikace – jen log a fallback
        logger.error(f"PDF parsing failed: {e}", exc_info=True)
        return {"doc_type": None, "year": None, "scale": "units", "data": {}}
