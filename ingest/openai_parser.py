import json
import re
from openai import OpenAI
from django.conf import settings

# Inicializace OpenAI klienta
client = OpenAI(api_key=settings.OPENAI_API_KEY)
MODEL = settings.OPENAI_MODEL or "gpt-4.1-mini"

# Prompt pro Income Statement
PROMPT_INCOME = """
You are an expert in Czech accounting.
You receive an INCOME STATEMENT (výkaz zisku a ztráty).
Extract the following metrics and return ONLY valid JSON:

{
  "Revenue": number,
  "GrossMargin": number,
  "NetProfit": number,
  "Depreciation": number,
  "InterestPaid": number,
  "IncomeTaxPaid": number,
  "ExtraordinaryItems": number,
  "DividendsPaid": number,
  "COGS": number,
  "EBIT": number
}

Rules:
- If a value is missing, set it to 0.
- No extra text, just JSON.
"""

# Prompt pro Balance Sheet
PROMPT_BALANCE = """
You are an expert in Czech accounting.
You receive a BALANCE SHEET (rozvaha).
Extract the following metrics and return ONLY valid JSON:

{
  "TotalAssets": number,
  "Cash": number,
  "Receivables": number,
  "Inventory": number,
  "CurrentAssets": number,
  "TangibleAssets": number,
  "TotalLiabilities": number,
  "TradePayables": number,
  "ShortTermLiabilities": number,
  "ShortTermLoans": number,
  "LongTermLoans": number,
  "Equity": number
}

Rules:
- If a value is missing, set it to 0.
- No extra text, just JSON.
"""

# Prompt pro autodetekci typu dokumentu
PROMPT_DETECT = """
You are an expert in Czech accounting.
Decide if the uploaded PDF is an Income Statement (výkaz zisku a ztráty) or a Balance Sheet (rozvaha).
Respond ONLY with one word: 'income' or 'balance'.
"""


def _call_openai(prompt: str, pdf_path: str) -> dict:
    """
    📩 Nahraje PDF → pošle do OpenAI Responses API → vrátí JSON.
    """
    # 1️⃣ nahraj PDF jako asset
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    # 2️⃣ zavolej Responses API s file_id
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

    # 3️⃣ validace JSON
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            return json.loads(match.group(0))
    return {}


def analyze_income(pdf_path: str) -> dict:
    """Analyzuje výsledovku (Income Statement)."""
    data = _call_openai(PROMPT_INCOME, pdf_path)
    return {
        "Revenue": data.get("Revenue", 0),
        "GrossMargin": data.get("GrossMargin", 0),
        "NetProfit": data.get("NetProfit", 0),
        "Depreciation": data.get("Depreciation", 0),
        "InterestPaid": data.get("InterestPaid", 0),
        "IncomeTaxPaid": data.get("IncomeTaxPaid", 0),
        "ExtraordinaryItems": data.get("ExtraordinaryItems", 0),
        "DividendsPaid": data.get("DividendsPaid", 0),
        "COGS": data.get("COGS", 0),
        "EBIT": data.get("EBIT", 0),
    }


def analyze_balance(pdf_path: str) -> dict:
    """Analyzuje rozvahu (Balance Sheet)."""
    data = _call_openai(PROMPT_BALANCE, pdf_path)
    return {
        "TotalAssets": data.get("TotalAssets", 0),
        "Cash": data.get("Cash", 0),
        "Receivables": data.get("Receivables", 0),
        "Inventory": data.get("Inventory", 0),
        "CurrentAssets": data.get("CurrentAssets", 0),
        "TangibleAssets": data.get("TangibleAssets", 0),
        "TotalLiabilities": data.get("TotalLiabilities", 0),
        "TradePayables": data.get("TradePayables", 0),
        "ShortTermLiabilities": data.get("ShortTermLiabilities", 0),
        "ShortTermLoans": data.get("ShortTermLoans", 0),
        "LongTermLoans": data.get("LongTermLoans", 0),
        "Equity": data.get("Equity", 0),
    }


def detect_doc_type(pdf_path: str) -> str:
    """Rozpozná, zda je dokument Income Statement nebo Balance Sheet."""
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
