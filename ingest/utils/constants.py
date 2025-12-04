"""
Constants and configuration for financial PDF extraction
"""
import os
from pathlib import Path

# ================================================================
# API Configuration
# ================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
MAX_TOKENS = 2048

# ================================================================
# PDF Processing Configuration
# ================================================================

PDF_DPI = 300  # Resolution for PNG conversion
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10MB max file size

# ================================================================
# File Paths
# ================================================================

# Directory for extracted table images (relative to BASE_DIR)
EXTRACTED_TABLES_DIR = "ingest/media/extracted_tables"

# ================================================================
# Field Mappings
# ================================================================

# Income Statement Fields
INCOME_STATEMENT_FIELDS = [
    'revenue_products_services',  # Tržby za prodej vlastních výrobků a služeb
    'revenue_goods',              # Tržby za prodej zboží
    'cogs_goods',                 # Náklady vynaložené na prodané zboží
    'cogs_materials',             # Spotřeba materiálu a energie
    'services',                   # Služby
    'personnel_wages',            # Mzdové náklady / Osobní náklady
    'personnel_insurance',        # Náklady na sociální zabezpečení
    'taxes_fees',                 # Daně a poplatky
    'depreciation',               # Odpisy dlouhodobého majetku
    'other_operating_costs',      # Ostatní provozní náklady
    'other_operating_revenue',    # Ostatní provozní výnosy
    'financial_revenue',          # Finanční výnosy
    'financial_costs',            # Finanční náklady
    'income_tax',                 # Daň z příjmů
]

# Balance Sheet Fields
BALANCE_SHEET_FIELDS = [
    'receivables',                # Pohledávky / Krátkodobé pohledávky
    'inventory',                  # Zásoby
    'short_term_liabilities',     # Krátkodobé závazky
    'cash',                       # Peníze / Peněžní prostředky
    'tangible_assets',            # Dlouhodobý hmotný majetek (DHM)
    'total_assets',               # Aktiva celkem
    'equity',                     # Vlastní kapitál
    'total_liabilities',          # Závazky celkem / Cizí zdroje
    'trade_payables',             # Závazky z obchodních vztahů
    'short_term_loans',           # Krátkodobé bankovní úvěry
    'long_term_loans',            # Dlouhodobé bankovní úvěry
]

# All financial fields
ALL_FINANCIAL_FIELDS = INCOME_STATEMENT_FIELDS + BALANCE_SHEET_FIELDS

# ================================================================
# Document Types
# ================================================================

DOC_TYPE_INCOME_STATEMENT = "income_statement"
DOC_TYPE_BALANCE_SHEET = "balance_sheet"

DOC_TYPES = [
    (DOC_TYPE_INCOME_STATEMENT, "Income Statement"),
    (DOC_TYPE_BALANCE_SHEET, "Balance Sheet"),
]

# ================================================================
# Scale Types
# ================================================================

SCALE_UNITS = "units"
SCALE_THOUSANDS = "thousands"

SCALE_CHOICES = [
    (SCALE_UNITS, "Units"),
    (SCALE_THOUSANDS, "Thousands"),
]

# ================================================================
# Czech Accounting Row Mappings (for reference)
# ================================================================

# Income Statement row mappings (Czech → English field names)
INCOME_STATEMENT_ROW_MAPPING = {
    # Revenue
    "tržby za prodej zboží": "revenue_goods",
    "tržby za prodej vlastních výrobků a služeb": "revenue_products_services",

    # COGS
    "náklady vynaložené na prodané zboží": "cogs_goods",
    "spotřeba materiálu a energie": "cogs_materials",

    # Operating costs
    "služby": "services",
    "mzdové náklady": "personnel_wages",
    "osobní náklady": "personnel_wages",
    "náklady na sociální zabezpečení": "personnel_insurance",
    "zákonné sociální pojištění": "personnel_insurance",
    "daně a poplatky": "taxes_fees",
    "odpisy dlouhodobého majetku": "depreciation",
    "ostatní provozní náklady": "other_operating_costs",
    "ostatní provozní výnosy": "other_operating_revenue",

    # Financial
    "finanční výnosy": "financial_revenue",
    "výnosové úroky": "financial_revenue",
    "finanční náklady": "financial_costs",
    "nákladové úroky": "financial_costs",

    # Tax
    "daň z příjmů": "income_tax",
}

# Balance Sheet row mappings (Czech → English field names)
BALANCE_SHEET_ROW_MAPPING = {
    # Assets
    "pohledávky": "receivables",
    "krátkodobé pohledávky": "receivables",
    "zásoby": "inventory",
    "peníze": "cash",
    "peněžní prostředky": "cash",
    "krátkodobý finanční majetek": "cash",
    "dlouhodobý hmotný majetek": "tangible_assets",
    "dhm": "tangible_assets",
    "aktiva celkem": "total_assets",
    "aktiva": "total_assets",

    # Liabilities & Equity
    "vlastní kapitál": "equity",
    "závazky celkem": "total_liabilities",
    "cizí zdroje": "total_liabilities",
    "krátkodobé závazky": "short_term_liabilities",
    "závazky z obchodních vztahů": "trade_payables",
    "krátkodobé bankovní úvěry": "short_term_loans",
    "dlouhodobé bankovní úvěry": "long_term_loans",
}
