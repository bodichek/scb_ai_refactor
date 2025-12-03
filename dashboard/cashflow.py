from ingest.models import FinancialStatement
from finance.utils import compute_overheads, first_number, to_number


def calculate_cashflow(user, year):
    """
    Vypočítá Cash Flow výkaz z FinancialStatement pro daný rok a uživatele.
    """
    fs = FinancialStatement.objects.filter(user=user, year=year).first()
    if not fs:
        return None

    income = fs.income or {}
    balance = fs.balance or {}

    def _income_value(keys, default=0.0):
        val = first_number(income, keys)
        return val if val is not None else default

    def _balance_value(keys, default=0.0):
        val = first_number(balance, keys)
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

    # Rozvaha
    total_assets = _balance_value(("TotalAssets", "total_assets"), 0.0)
    cash = _balance_value(("Cash", "cash"), 0.0)
    receivables = _balance_value(("Receivables", "receivables"), 0.0)
    inventory = _balance_value(("Inventory", "inventory"), 0.0)
    tangible_assets = _balance_value(("TangibleAssets", "tangible_assets"), 0.0)
    trade_payables = _balance_value(("TradePayables", "trade_payables"), 0.0)
    short_term_loans = _balance_value(("ShortTermLoans", "short_term_loans"), 0.0)
    long_term_loans = _balance_value(("LongTermLoans", "long_term_loans"), 0.0)

    loans_received = _balance_value(("LoansReceived", "loans_received"), 0.0)
    loans_repaid = _balance_value(("LoansRepaid", "loans_repaid"), 0.0)
    asset_sales = _balance_value(("AssetSales", "asset_sales"), 0.0)

    working_capital_change = _balance_value(("WorkingCapitalChange", "working_capital_change"), 0.0)
    if working_capital_change == 0 and receivables > 0:
        working_capital_change = revenue * 0.05

    cash_begin = (
        to_number(balance.get("CashBegin"))
        or to_number(income.get("CashBegin"))
        or cash * 0.8
    )

    # --- Základní výpočty ---
    net_profit = _income_value(
        ("NetProfit", "net_profit"),
        revenue - cogs - overheads - interest - taxation + extraordinary,
    )

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
        "net_profit": net_profit,
        "depreciation": depreciation,
        "working_capital_change": working_capital_change,
        "interest_paid": interest,
        "income_tax_paid": taxation,
        "operating_cf": operating_cf,
        "capex": capex,
        "asset_sales": asset_sales,
        "investing_cf": investing_cf,
        "loans_received": loans_received,
        "loans_repaid": loans_repaid,
        "dividends_paid": dividends,
        "financing_cf": financing_cf,
        "net_cash_flow": total_net_cash_flow,
        "cash_begin": cash_begin,
        "cash_end": cash_end,
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
        "gross_cash_profit": revenue * 0.93 - cogs * 0.98,
        "operating_cash_flow": operating_cf,
        "variance": {
            "gross": (revenue - cogs) - (revenue * 0.93 - cogs * 0.98),
            "operating": (revenue - cogs - overheads) - operating_cf,
            "net": net_profit - total_net_cash_flow,
        },
    }
