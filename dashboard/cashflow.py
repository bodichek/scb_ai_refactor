from ingest.models import FinancialStatement
from finance.utils import compute_overheads, first_number, to_number


def calculate_cashflow(user, year):
    """
    Vypočítá Cash Flow výkaz z FinancialStatement pro daný rok a uživatele.
    Používá přímou i nepřímou metodu podle dostupných dat.
    """
    fs = FinancialStatement.objects.filter(user=user, year=year).first()
    if not fs:
        return None

    # Získat data předchozího roku pro výpočet změn (Δ)
    fs_prev = FinancialStatement.objects.filter(user=user, year=year - 1).first()

    income = fs.income or {}
    balance = fs.balance or {}
    balance_prev = (fs_prev.balance or {}) if fs_prev else {}

    def _income_value(keys, default=0.0):
        val = first_number(income, keys)
        return val if val is not None else default

    def _balance_value(keys, default=0.0):
        val = first_number(balance, keys)
        return val if val is not None else default

    def _balance_prev_value(keys, default=0.0):
        val = first_number(balance_prev, keys)
        return val if val is not None else default

    # Výsledovka
    revenue = _income_value(("Revenue", "revenue"), 0.0)
    cogs = _income_value(("COGS", "cogs"), 0.0)
    overheads = compute_overheads(income)
    depreciation = _income_value(("depreciation", "Depreciation"), 0.0)

    interest = _income_value(("InterestPaid", "Interest", "interest_paid"), 0.0)
    taxation = _income_value(("IncomeTaxPaid", "Tax", "income_tax_paid"), 0.0)
    dividends = _income_value(("DividendsPaid", "Dividends", "dividends_paid"), 0.0)
    extraordinary = _income_value(("ExtraordinaryItems", "extraordinary_items"), 0.0)

    # Rozvaha (aktuální rok)
    total_assets = _balance_value(("TotalAssets", "total_assets", "assets_total"), 0.0)
    cash = _balance_value(("Cash", "cash"), 0.0)
    receivables = _balance_value(("Receivables", "receivables"), 0.0)
    inventory = _balance_value(("Inventory", "inventory"), 0.0)
    tangible_assets = _balance_value(("TangibleAssets", "tangible_assets", "fixed_assets_tangible"), 0.0)
    trade_payables = _balance_value(("TradePayables", "trade_payables"), 0.0)
    short_term_liabilities = _balance_value(("ShortTermLiabilities", "short_term_liabilities", "liabilities_short"), 0.0)
    short_term_loans = _balance_value(("ShortTermLoans", "short_term_loans"), 0.0)
    long_term_loans = _balance_value(("LongTermLoans", "long_term_loans"), 0.0)

    # Rozvaha (předchozí rok) - pro výpočet Δ
    receivables_prev = _balance_prev_value(("Receivables", "receivables"), 0.0)
    inventory_prev = _balance_prev_value(("Inventory", "inventory"), 0.0)
    trade_payables_prev = _balance_prev_value(("TradePayables", "trade_payables"), 0.0)
    short_term_liabilities_prev = _balance_prev_value(("ShortTermLiabilities", "short_term_liabilities", "liabilities_short"), 0.0)

    loans_received = _balance_value(("LoansReceived", "loans_received"), 0.0)
    loans_repaid = _balance_value(("LoansRepaid", "loans_repaid"), 0.0)
    asset_sales = _balance_value(("AssetSales", "asset_sales"), 0.0)

    # --- Změny v rozvaze (Δ) ---
    delta_receivables = receivables - receivables_prev
    delta_inventory = inventory - inventory_prev
    delta_payables = trade_payables - trade_payables_prev
    delta_short_term_liabilities = short_term_liabilities - short_term_liabilities_prev

    # Δ Pracovního kapitálu = Δ(Zásoby) + Δ(Pohledávky) - Δ(Krátkodobé závazky)
    # Pozor na znaménka: Vyšší zásoby/pohledávky = cash out (-)
    #                    Vyšší závazky = cash in (+)
    working_capital_change = (delta_inventory + delta_receivables - delta_short_term_liabilities)

    cash_begin = (
        to_number(balance.get("CashBegin"))
        or to_number(income.get("CashBegin"))
        or cash * 0.8
    )

    # --- Základní výpočty ---
    net_profit = _income_value(
        ("NetProfit", "net_profit", "net_income"),
        revenue - cogs - overheads - interest - taxation + extraordinary,
    )

    # --- Cash from Customers (přímá metoda) ---
    # Cash from Customers ≈ Revenue - Δ(Pohledávky)
    # Vyšší pohledávky = zákazníci platili méně než tržby
    cash_from_customers = revenue - delta_receivables

    # --- Cash to Suppliers (přímá metoda) ---
    # Cash to Suppliers ≈ COGS + část služeb - Δ(Zásoby) - Δ(Závazky vůči dodavatelům)
    # Vyšší zásoby = nákup navíc (cash out)
    # Vyšší závazky = zaplatili jsme méně (cash zůstalo)
    # Používáme cogs_services z overheads jako část služeb
    cogs_services = _income_value(("cogs_services", "services", "Services"), 0.0)
    cash_to_suppliers = (cogs + cogs_services) + delta_inventory - delta_payables

    # --- Gross Cash Profit ---
    gross_cash_profit = cash_from_customers - cash_to_suppliers

    # --- Cash Flow z provozní činnosti ---
    operating_cf = net_profit + depreciation - working_capital_change

    # --- Cash Flow z investiční činnosti ---
    capex = _balance_value(("CapEx", "FixedAssets", "capex"), tangible_assets * 0.1)
    if capex == 0 and revenue > 0:
        capex = revenue * 0.02
    investing_cf = asset_sales - capex

    # --- Cash Flow z finanční činnosti ---
    if loans_received == 0 and loans_repaid == 0:
        total_loans = short_term_loans + long_term_loans
        if total_loans > 0:
            loans_repaid = total_loans * 0.1
            if revenue > 10000:
                loans_received = revenue * 0.05

    financing_cf = loans_received - loans_repaid - dividends

    # --- Celková změna peněžních prostředků ---
    total_net_cash_flow = operating_cf + investing_cf + financing_cf
    cash_end = cash_begin + total_net_cash_flow

    return {
        # Operating Cash Flow components
        "net_profit": net_profit,
        "depreciation": depreciation,
        "working_capital_change": working_capital_change,
        "interest_paid": interest,
        "income_tax_paid": taxation,
        "operating_cf": operating_cf,

        # Investing Cash Flow components
        "capex": capex,
        "asset_sales": asset_sales,
        "investing_cf": investing_cf,

        # Financing Cash Flow components
        "loans_received": loans_received,
        "loans_repaid": loans_repaid,
        "dividends_paid": dividends,
        "financing_cf": financing_cf,

        # Net Cash Flow
        "net_cash_flow": total_net_cash_flow,
        "cash_begin": cash_begin,
        "cash_end": cash_end,

        # Direct method cash components
        "cash_from_customers": cash_from_customers,
        "cash_to_suppliers": cash_to_suppliers,
        "gross_cash_profit": gross_cash_profit,

        # Supporting metrics
        "revenue": revenue,
        "cogs": cogs,
        "overheads": overheads,
        "interest": interest,
        "extraordinary": extraordinary,
        "taxation": taxation,
        "dividends": dividends,
        "fixed_assets": capex,
        "other_assets": 0,
        "capital_withdrawn": 0,
        "gross_margin": revenue - cogs,
        "operating_cash_profit": revenue - cogs - overheads,
        "retained_profit": net_profit,
        "operating_cash_flow": operating_cf,

        # Balance sheet changes (Δ)
        "delta_receivables": delta_receivables,
        "delta_inventory": delta_inventory,
        "delta_payables": delta_payables,
        "delta_short_term_liabilities": delta_short_term_liabilities,

        # Variance analysis
        "variance": {
            "gross": (revenue - cogs) - gross_cash_profit,
            "operating": (revenue - cogs - overheads) - operating_cf,
            "net": net_profit - total_net_cash_flow,
        },
    }
