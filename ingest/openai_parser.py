import os
import openai
import pdfplumber
import json, re
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY
MODEL = settings.OPENAI_MODEL or "gpt-4o-mini"

# Prompt pro výsledovku (Profit & Loss)
PROMPT_INCOME = """
You are an expert in Czech accounting. 
Extract financial metrics from the provided INCOME STATEMENT (výkaz zisku a ztráty).
Map Czech line items to the following JSON structure (missing values as 0).
Return ONLY valid JSON.

{
  "Revenue": number,
  "GrossMargin": number,
  "NetProfit": number,
  "Depreciation": number,
  "InterestPaid": number,
  "IncomeTaxPaid": number,
  "ExtraordinaryItems": number,
  "DividendsPaid": number
}
"""

# Prompt pro rozvahu (Balance Sheet)
PROMPT_BALANCE = """
You are an expert in Czech accounting. 
Extract financial metrics from the provided BALANCE SHEET (rozvaha).
Map Czech line items to the following JSON structure (missing values as 0).
Return ONLY valid JSON.

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
  "LongTermLoans": number
}
"""

def extract_text_from_pdf(pdf_path: str) -> str:
    """Načte text z PDF souboru pomocí pdfplumber (fallback: binární načtení)."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception:
        with open(pdf_path, "rb") as f:
            text = f.read().decode(errors="ignore")
    return text


def _call_openai(prompt: str, text: str) -> dict:
    """Společný helper pro volání OpenAI a načtení JSON."""
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a financial statement parser."},
            {"role": "user", "content": prompt + "\n\nText:\n" + text[:12000]}
        ],
        temperature=0,
    )
    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            return json.loads(match.group(0))
    return {}


def analyze_income(pdf_path: str) -> dict:
    """Analyzuje výsledovku (výkaz zisku a ztráty)."""
    text = extract_text_from_pdf(pdf_path)
    data = _call_openai(PROMPT_INCOME, text)

    metrics = {
        "Revenue": 0,
        "GrossMargin": 0,
        "NetProfit": 0,
        "Depreciation": 0,
        "InterestPaid": 0,
        "IncomeTaxPaid": 0,
        "ExtraordinaryItems": 0,
        "DividendsPaid": 0,
    }
    metrics.update(data)
    return metrics


def analyze_balance(pdf_path: str) -> dict:
    """Analyzuje rozvahu (balance sheet)."""
    text = extract_text_from_pdf(pdf_path)
    data = _call_openai(PROMPT_BALANCE, text)

    metrics = {
        "TotalAssets": 0,
        "Cash": 0,
        "Receivables": 0,
        "Inventory": 0,
        "CurrentAssets": 0,
        "TangibleAssets": 0,
        "TotalLiabilities": 0,
        "TradePayables": 0,
        "ShortTermLiabilities": 0,
        "ShortTermLoans": 0,
        "LongTermLoans": 0,
    }
    metrics.update(data)
    return metrics
