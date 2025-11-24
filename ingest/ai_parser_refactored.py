"""
Refaktorovaný AI parser pro finanční výkazy
Parsuje pouze nezbytná data podle zadaných vzorců
"""
import json
from django.conf import settings
from openai import OpenAI
from .openai_parser import _extract_output_text, _parse_json

client = OpenAI(api_key=settings.OPENAI_API_KEY)
MODEL = settings.OPENAI_MODEL or "gpt-4o-mini"

# ============================================================================
# PROMPTY PRO AI PARSOVÁNÍ
# ============================================================================

PROMPT_INCOME = """
Jsi expert na české účetnictví.
Dostáváš VÝKAZ ZISKU A ZTRÁTY (Income Statement).

DŮLEŽITÉ - Normalizace částek:
- Zjisti, zda dokument uvádí hodnoty v tisících Kč (fráze jako "v tis. Kč", "tisíce Kč" apod.)
- Pokud ANO: všechny hodnoty vynásob 1000, aby JSON obsahoval absolutní částky v Kč
- Pokud už dokument používá plné částky v Kč: ponech hodnoty beze změny

KRITICKÉ - Služby (Services):
- Služby NEJSOU součástí COGS
- Služby patří do režijních nákladů (Overheads)
- Vrať je samostatně v klíči "services"

Extrahuj následující hodnoty a vrať POUZE validní JSON:
{
  "revenue_products_services": number,
  "revenue_goods": number,
  "cogs_goods": number,
  "cogs_materials": number,
  "services": number,
  "personnel_wages": number,
  "personnel_insurance": number,
  "taxes_fees": number,
  "depreciation": number,
  "other_operating_costs": number,
  "other_operating_revenue": number,
  "financial_revenue": number,
  "financial_costs": number,
  "income_tax": number
}

Mapování českých účetních položek:
- revenue_products_services: "Tržby za prodej vlastních výrobků a služeb" (obvykle I.)
- revenue_goods: "Tržby z prodeje zboží" (obvykle II.)
- cogs_goods: "Náklady na prodané zboží" (v sekci A)
- cogs_materials: "Spotřeba materiálu a energie" (v sekci A, Výkonová spotřeba)
- services: "Služby" (v sekci A, Výkonová spotřeba) - SAMOSTATNĚ!
- personnel_wages: "Mzdové náklady" (v sekci D, Osobní náklady)
- personnel_insurance: "Zákonné sociální a zdravotní pojištění" (v sekci D)
- taxes_fees: "Daně a poplatky" (obvykle před Odpisy)
- depreciation: "Odpisy dlouhodobého nehmotného a hmotného majetku"
- other_operating_costs: "Ostatní provozní náklady"
- other_operating_revenue: "Ostatní provozní výnosy"
- financial_revenue: "Finanční výnosy"
- financial_costs: "Finanční náklady"
- income_tax: "Daň z příjmů"

Vrať pouze čísla, ne stringy. Pokud položka chybí, vrať 0.
"""

PROMPT_BALANCE = """
Jsi expert na české účetnictví.
Dostáváš ROZVAHU (Balance Sheet).

DŮLEŽITÉ - Normalizace částek:
- Zjisti, zda dokument uvádí hodnoty v tisících Kč (fráze jako "v tis. Kč", "tisíce Kč" apod.)
- Pokud ANO: všechny hodnoty vynásob 1000, aby JSON obsahoval absolutní částky v Kč
- Pokud už dokument používá plné částky v Kč: ponech hodnoty beze změny

Extrahuj následující hodnoty a vrať POUZE validní JSON:
{
  "receivables": number,
  "inventory": number,
  "short_term_liabilities": number,
  "cash": number
}

Mapování:
- receivables: "Krátkodobé pohledávky" nebo "Pohledávky z obchodních vztahů"
- inventory: "Zásoby"
- short_term_liabilities: "Krátkodobé závazky" (celkem)
- cash: "Krátkodobý finanční majetek" nebo "Peníze"

Vrať pouze čísla, ne stringy. Pokud položka chybí, vrať 0.
"""

PROMPT_DETECT = """
You are an expert in Czech accounting.
Decide if the uploaded PDF is an Income Statement (výkaz zisku a ztráty) or a Balance Sheet (rozvaha).
Respond ONLY with one word: 'income' or 'balance'.
"""

PROMPT_DETECT_TYPE_YEAR = """
Jsi expert na české účetnictví.
Uživatel nahrává český finanční výkaz (PDF).

Tvůj úkol:
1. Urči, zda je dokument Výkaz zisku a ztráty (income) nebo Rozvaha (balance)
2. Zjisti, kterého roku se dokument týká (obvykle "Rok 2023", "2022" apod.)
3. Odpověz POUZE ve striktním JSON formátu:

{ "type": "income" nebo "balance", "year": 2020-2025 (integer) }
"""


# ============================================================================
# ZÁKLADNÍ VOLÁNÍ OPENAI API
# ============================================================================

def _call_openai(prompt: str, pdf_path: str) -> dict:
    """Základní volání OpenAI pro analýzu PDF."""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    response = client.responses.create_and_poll(
        model=MODEL,
        input=[
            {"role": "system", "content": "Jsi parser finančních výkazů. Vždy vracíš JSON."},
            {"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_file", "file_id": file_obj.id}
            ]}
        ],
        temperature=0,
    )

    content = _extract_output_text(response)
    return _parse_json(content)


# ============================================================================
# PARSOVÁNÍ VÝSLEDOVKY
# ============================================================================

def analyze_income(pdf_path: str) -> dict:
    """
    Parsuje výsledovku a vrací surová data z PDF.
    Výpočty se dělají později v kalkulačních funkcích.
    """
    data = _call_openai(PROMPT_INCOME, pdf_path)
    
    # Vrať pouze parsovaná pole (bez výpočtů)
    fields = [
        "revenue_products_services",
        "revenue_goods", 
        "cogs_goods",
        "cogs_materials",
        "services",
        "personnel_wages",
        "personnel_insurance",
        "taxes_fees",
        "depreciation",
        "other_operating_costs",
        "other_operating_revenue",
        "financial_revenue",
        "financial_costs",
        "income_tax"
    ]
    
    return {k: float(data.get(k, 0)) for k in fields}


# ============================================================================
# PARSOVÁNÍ ROZVAHY
# ============================================================================

def analyze_balance(pdf_path: str) -> dict:
    """Parsuje rozvahu a vrací základní položky pro cash flow výpočty"""
    data = _call_openai(PROMPT_BALANCE, pdf_path)
    
    fields = [
        "receivables",
        "inventory", 
        "short_term_liabilities",
        "cash"
    ]
    
    return {k: float(data.get(k, 0)) for k in fields}


# ============================================================================
# DETEKCE TYPU A ROKU
# ============================================================================

def detect_doc_type(pdf_path: str) -> str:
    """
    Původní detekce typu (fallback).
    Vrací 'income' nebo 'balance'.
    """
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
    """Rozpozná typ dokumentu a rok"""
    with open(pdf_path, "rb") as f:
        file_obj = client.files.create(file=f, purpose="assistants")

    response = client.responses.create_and_poll(
        model=MODEL,
        input=[
            {"role": "system", "content": "Jsi expert na české účetnictví."},
            {"role": "user", "content": [
                {"type": "input_text", "text": PROMPT_DETECT_TYPE_YEAR},
                {"type": "input_file", "file_id": file_obj.id}
            ]}
        ],
        temperature=0,
    )

    result = _extract_output_text(response)
    data = _parse_json(result)

    return {
        "type": data.get("type", "income"),
        "year": int(data.get("year", 2025)),
    }


# ============================================================================
# VÝPOČETNÍ FUNKCE (používají parsovaná data)
# ============================================================================

def calculate_metrics(income_data: dict, balance_data: dict = None) -> dict:
    """
    Počítá všechny odvozené metriky podle zadaných vzorců.
    
    Vstupy:
    - income_data: dict s parsovanými hodnotami z výsledovky
    - balance_data: dict s parsovanými hodnotami z rozvahy (volitelné)
    
    Výstupy:
    - dict se všemi metrikami (parsované + vypočítané)
    """
    
    # Základní parsované hodnoty
    rev_products = income_data.get("revenue_products_services", 0)
    rev_goods = income_data.get("revenue_goods", 0)
    cogs_goods = income_data.get("cogs_goods", 0)
    cogs_materials = income_data.get("cogs_materials", 0)
    services = income_data.get("services", 0)
    personnel_wages = income_data.get("personnel_wages", 0)
    personnel_insurance = income_data.get("personnel_insurance", 0)
    taxes_fees = income_data.get("taxes_fees", 0)
    depreciation = income_data.get("depreciation", 0)
    other_op_costs = income_data.get("other_operating_costs", 0)
    other_op_revenue = income_data.get("other_operating_revenue", 0)
    fin_revenue = income_data.get("financial_revenue", 0)
    fin_costs = income_data.get("financial_costs", 0)
    income_tax = income_data.get("income_tax", 0)
    
    # 1.1 Revenue
    revenue = rev_products + rev_goods
    
    # 1.2 COGS (BEZ služeb!)
    cogs = cogs_goods + cogs_materials
    
    # 1.3 Gross Margin
    gross_margin = revenue - cogs
    
    # 1.4 Gross Margin %
    gross_margin_pct = (gross_margin / revenue * 100) if revenue > 0 else 0
    
    # 1.5 Overheads (včetně služeb!)
    overheads = (
        services +
        personnel_wages + 
        personnel_insurance +
        taxes_fees +
        depreciation +
        other_op_costs
    )
    
    # 1.6 Operating Profit (EBIT)
    ebit = gross_margin - overheads + other_op_revenue
    
    # 1.7 Net Profit
    ebt = ebit + fin_revenue - fin_costs
    net_profit = ebt - income_tax
    
    # Vrať kompletní dataset
    result = {
        # Parsovaná data
        **income_data,
        
        # Vypočítané metriky
        "revenue": revenue,
        "cogs": cogs,
        "gross_margin": gross_margin,
        "gross_margin_pct": gross_margin_pct,
        "overheads": overheads,
        "ebit": ebit,
        "ebt": ebt,
        "net_profit": net_profit,
        
        # Profitability pro template
        "profitability": {
            "gm_pct": gross_margin_pct,
            "op_pct": (ebit / revenue * 100) if revenue > 0 else 0,
            "np_pct": (net_profit / revenue * 100) if revenue > 0 else 0,
        }
    }
    
    # Přidej rozvahová data, pokud jsou k dispozici
    if balance_data:
        result.update(balance_data)
    
    return result


def calculate_yoy_growth(current_year_data: dict, previous_year_data: dict) -> dict:
    """
    Počítá meziroční růst (Year-over-Year)
    
    Vzorce:
    - Revenue Growth % = (Revenue_Y - Revenue_Y-1) / Revenue_Y-1 × 100
    - COGS Growth % = (COGS_Y - COGS_Y-1) / COGS_Y-1 × 100
    - Overheads Growth % = (Overheads_Y - Overheads_Y-1) / Overheads_Y-1 × 100
    """
    def growth(current, previous):
        if previous and previous != 0:
            return (current - previous) / abs(previous) * 100
        return None
    
    return {
        "revenue": growth(
            current_year_data.get("revenue", 0),
            previous_year_data.get("revenue", 0)
        ),
        "cogs": growth(
            current_year_data.get("cogs", 0),
            previous_year_data.get("cogs", 0)
        ),
        "overheads": growth(
            current_year_data.get("overheads", 0),
            previous_year_data.get("overheads", 0)
        ),
        "ebit": growth(
            current_year_data.get("ebit", 0),
            previous_year_data.get("ebit", 0)
        ),
        "net_profit": growth(
            current_year_data.get("net_profit", 0),
            previous_year_data.get("net_profit", 0)
        ),
    }


def calculate_cash_flow(current_year: dict, previous_year: dict = None) -> dict:
    """
    Počítá cash flow metriky
    
    3.1 Cash from Customers ≈ Revenue ± Δ(Pohledávky)
    3.2 Cash to Suppliers ≈ COGS ± Δ(Zásoby) + Δ(Závazky)
    3.3 Gross Cash Profit = Cash from Customers - Cash to Suppliers
    3.4 OCF = Net Profit + Odpisy ± ΔWorking Capital
    """
    revenue = current_year.get("revenue", 0)
    cogs = current_year.get("cogs", 0)
    services = current_year.get("services", 0)
    net_profit = current_year.get("net_profit", 0)
    depreciation = current_year.get("depreciation", 0)
    
    # Delta hodnoty (pokud máme předchozí rok)
    delta_receivables = 0
    delta_inventory = 0
    delta_liabilities = 0
    
    if previous_year:
        delta_receivables = (
            current_year.get("receivables", 0) - 
            previous_year.get("receivables", 0)
        )
        delta_inventory = (
            current_year.get("inventory", 0) - 
            previous_year.get("inventory", 0)
        )
        delta_liabilities = (
            current_year.get("short_term_liabilities", 0) - 
            previous_year.get("short_term_liabilities", 0)
        )
    
    # 3.1 Cash from Customers
    cash_from_customers = revenue - delta_receivables
    
    # 3.2 Cash to Suppliers
    cash_to_suppliers = cogs + services - delta_inventory - delta_liabilities
    
    # 3.3 Gross Cash Profit
    gross_cash_profit = cash_from_customers - cash_to_suppliers
    
    # 3.4 Operating Cash Flow
    working_capital_change = delta_inventory + delta_receivables - delta_liabilities
    operating_cf = net_profit + depreciation - working_capital_change
    
    return {
        "cash_from_customers": cash_from_customers,
        "cash_to_suppliers": cash_to_suppliers,
        "gross_cash_profit": gross_cash_profit,
        "operating_cf": operating_cf,
        "working_capital_change": working_capital_change,
        "delta_receivables": delta_receivables,
        "delta_inventory": delta_inventory,
        "delta_liabilities": delta_liabilities,
    }
