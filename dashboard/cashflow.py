from ingest.models import FinancialStatement

def calculate_cashflow(user, year):
    """
    Vypočítá Profit vs Cash Flow tabulku z FinancialStatement.data
    """
    fs = FinancialStatement.objects.filter(owner=user, year=year).first()
    if not fs or not fs.data:
        return None

    d = fs.data

    # Mapování názvů podle dat z OpenAI (velká písmena)
    revenue = float(d.get("Revenue", 0))
    cogs = float(d.get("COGS", 0))
    overheads = float(d.get("Overheads", 0))
    depreciation = float(d.get("Depreciation", 0))
    interest = float(d.get("Interest", 0))
    extraordinary = float(d.get("Extraordinary", 0))
    taxation = float(d.get("Tax", 0))
    dividends = float(d.get("Dividends", 0))
    fixed_assets = float(d.get("FixedAssets", 0))
    other_assets = float(d.get("OtherAssets", 0))
    capital_withdrawn = float(d.get("CapitalWithdrawn", 0))

    # --- Profit výpočty ---
    gross_margin = revenue - cogs
    operating_cash_profit = gross_margin - overheads
    retained_profit = (
        operating_cash_profit - interest - taxation
        + extraordinary - depreciation
    )

    # --- Cash Flow výpočty (zjednodušený model) ---
    cash_from_customers = revenue * 0.93
    cash_to_suppliers = cogs * 0.98
    gross_cash_profit = cash_from_customers - cash_to_suppliers
    operating_cash_flow = gross_cash_profit - overheads
    net_cash_flow = (
        operating_cash_flow - interest - taxation
        + extraordinary - fixed_assets
        - other_assets - capital_withdrawn
    )

    return {
        "revenue": revenue,
        "cogs": cogs,
        "overheads": overheads,
        "depreciation": depreciation,
        "interest": interest,
        "extraordinary": extraordinary,
        "taxation": taxation,
        "dividends": dividends,
        "fixed_assets": fixed_assets,
        "other_assets": other_assets,
        "capital_withdrawn": capital_withdrawn,
        "gross_margin": gross_margin,
        "operating_cash_profit": operating_cash_profit,
        "retained_profit": retained_profit,
        "gross_cash_profit": gross_cash_profit,
        "operating_cash_flow": operating_cash_flow,
        "net_cash_flow": net_cash_flow,
        "variance": {
            "gross": gross_margin - gross_cash_profit,
            "operating": operating_cash_profit - operating_cash_flow,
            "net": retained_profit - net_cash_flow,
        },
    }
