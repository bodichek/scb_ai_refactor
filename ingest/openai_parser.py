import json
import re
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)
MODEL = settings.OPENAI_MODEL or "gpt-4o-mini"

# Prompty
PROMPT_INCOME = """
You are an expert in Czech accounting.
You receive an INCOME STATEMENT (výkaz zisku a ztráty).
Extract the following metrics and return ONLY valid JSON:
{ "Revenue": number, "GrossMargin": number, "NetProfit": number, "Depreciation": number,
  "InterestPaid": number, "IncomeTaxPaid": number, "ExtraordinaryItems": number,
  "DividendsPaid": number, "COGS": number, "EBIT": number }
"""

PROMPT_BALANCE = """
You are an expert in Czech accounting.
You receive a BALANCE SHEET (rozvaha).
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


def _call_openai(prompt: str, pdf_path: str) -> dict:
    """Základní volání OpenAI pro analýzu PDF."""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    response = client.responses.create(
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

    content = response.output_text.strip()
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.S)
        return json.loads(match.group(0)) if match else {}


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

    resp = client.responses.create(
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

    result = resp.output_text.strip().lower()
    return "income" if "income" in result else "balance"


def detect_doc_type_and_year(pdf_path: str) -> dict:
    """Rozpozná typ a rok dokumentu pomocí OpenAI."""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    resp = client.responses.create(
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

    result = resp.output_text.strip()
    try:
        data = json.loads(result)
    except Exception:
        match = re.search(r"\{.*\}", result, re.S)
        data = json.loads(match.group(0)) if match else {}

    return {
        "type": data.get("type", "income"),
        "year": int(data.get("year", 2025)),
    }
