import json
import re
from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)
MODEL = settings.OPENAI_MODEL or "gpt-4o-mini"

# Prompty
PROMPT_INCOME = """
You are an expert in Czech accounting.
You receive an INCOME STATEMENT (výkaz zisku a ztráty).
Normalize the figures before returning them:
- Detect whether the report states that values are provided in thousands (phrases like "v tis. Kc", "tisice Kc", etc.). If yes, multiply every extracted value by 1_000 so the JSON contains absolute CZK amounts.
- If the report already uses full CZK amounts, keep the values unchanged.
- Return numbers only (no strings) and default to 0 when data is missing.
Extract the following metrics and return ONLY valid JSON:
{ "Revenue": number, "GrossMargin": number, "NetProfit": number, "Depreciation": number,
  "InterestPaid": number, "IncomeTaxPaid": number, "ExtraordinaryItems": number,
  "DividendsPaid": number, "COGS": number, "EBIT": number }
"""

PROMPT_BALANCE = """
You are an expert in Czech accounting.
You receive a BALANCE SHEET (rozvaha).
Normalize the figures before returning them:
- Detect whether the report states that values are provided in thousands (phrases like "v tis. Kc", "tisice Kc", etc.). If yes, multiply every extracted value by 1_000 so the JSON contains absolute CZK amounts.
- If the report already uses full CZK amounts, keep the values unchanged.
- Return numbers only (no strings) and default to 0 when data is missing.
Extract the following metrics and return ONLY valid JSON:
{ "TotalAssets": number, "Cash": number, "Receivables": number, "Inventory": number,
  "CurrentAssets": number, "TangibleAssets": number, "TotalLiabilities": number,
  "TradePayables": number, "ShortTermLiabilities": number, "ShortTermLoans": number,
  "LongTermLoans": number, "Equity": number }
"""

PROMPT_DETECT = """
You are an expert in Czech accounting.
Decide if the uploaded PDF is an Income Statement (výkaz zisku a ztráty) or a Balance Sheet (rozvaha).
Respond ONLY with one word: 'income' or 'balance'.
"""

PROMPT_DETECT_TYPE_YEAR = """
You are an expert in Czech accounting.
The user uploads a Czech financial statement (PDF).

Your task:
1. Determine if the document is an Income Statement (výkaz zisku a ztráty) or Balance Sheet (rozvaha).
2. Detect which year the document belongs to (usually shown as "Rok 2023", "2022", etc.).
3. Respond ONLY in strict JSON format:
{ "type": "income" or "balance", "year": 2020-2025 (integer) }
"""


def _extract_output_text(response) -> str:
    """
    Vrátí textový výstup z Responses API i v případech,
    kdy není k dispozici pomocný atribut `output_text`.
    """
    # Nejprve využij rychlou zkratku
    text = (getattr(response, "output_text", None) or "").strip()
    if text:
        return text

    # Fallback na strukturovaný výstup
    output = getattr(response, "output", None) or []
    for item in output:
        for content in getattr(item, "content", []):
            # `text` může být přímo string nebo objekt s hodnotou ve `value`
            value = getattr(content, "text", None)
            if hasattr(value, "value"):
                value = value.value
            if value:
                return str(value).strip()
    return ""


def _parse_json(content: str) -> dict:
    """Bezpečně naparsuje JSON, i když model přidal text okolo."""
    if not content:
        return {}
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
    return {}


def _call_openai(prompt: str, pdf_path: str) -> dict:
    """Základní volání OpenAI pro analýzu PDF."""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    response = client.responses.create_and_poll(
        model=MODEL,
        input=[
            {"role": "system", "content": "You are a financial statement parser. Always return JSON."},
            {"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_file", "file_id": file_obj.id}
            ]}
        ],
        temperature=0,
    )

    content = _extract_output_text(response)
    return _parse_json(content)


def analyze_income(pdf_path: str) -> dict:
    data = _call_openai(PROMPT_INCOME, pdf_path)
    return {k: data.get(k, 0) for k in [
        "Revenue", "GrossMargin", "NetProfit", "Depreciation",
        "InterestPaid", "IncomeTaxPaid", "ExtraordinaryItems",
        "DividendsPaid", "COGS", "EBIT"
    ]}


def analyze_balance(pdf_path: str) -> dict:
    data = _call_openai(PROMPT_BALANCE, pdf_path)
    return {k: data.get(k, 0) for k in [
        "TotalAssets", "Cash", "Receivables", "Inventory", "CurrentAssets",
        "TangibleAssets", "TotalLiabilities", "TradePayables",
        "ShortTermLiabilities", "ShortTermLoans", "LongTermLoans", "Equity"
    ]}


def detect_doc_type(pdf_path: str) -> str:
    """Původní detekce typu (fallback)."""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    resp = client.responses.create_and_poll(
        model=MODEL,
        input=[
            {"role": "system", "content": "You are an expert in Czech accounting."},
            {"role": "user", "content": [
                {"type": "input_text", "text": PROMPT_DETECT},
                {"type": "input_file", "file_id": file_obj.id}
            ]}
        ],
        temperature=0,
    )

    result = _extract_output_text(resp).lower()
    return "income" if "income" in result else "balance"


def detect_doc_type_and_year(pdf_path: str) -> dict:
    """Rozpozná typ a rok dokumentu pomocí OpenAI."""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    resp = client.responses.create_and_poll(
        model=MODEL,
        input=[
            {"role": "system", "content": "You are a Czech accounting expert."},
            {"role": "user", "content": [
                {"type": "input_text", "text": PROMPT_DETECT_TYPE_YEAR},
                {"type": "input_file", "file_id": file_obj.id}
            ]}
        ],
        temperature=0,
    )

    result = _extract_output_text(resp)
    data = _parse_json(result)

    return {
        "type": data.get("type", "income"),
        "year": int(data.get("year", 2025)),
    }
