from ingest.models import FinancialStatement

def calculate_cashflow(user, year):
    """
    Vypočítá Cash Flow výkaz z FinancialStatement.data
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
    
    # Použijeme data, která skutečně máme z parsingu
    interest = float(d.get("InterestPaid", d.get("Interest", 0)))
    taxation = float(d.get("IncomeTaxPaid", d.get("Tax", 0)))
    dividends = float(d.get("DividendsPaid", d.get("Dividends", 0)))
    extraordinary = float(d.get("ExtraordinaryItems", 0))
    
    # Bilance data pro odhad cash flow
    total_assets = float(d.get("TotalAssets", 0))
    cash = float(d.get("Cash", 0))
    receivables = float(d.get("Receivables", 0))
    inventory = float(d.get("Inventory", 0))
    tangible_assets = float(d.get("TangibleAssets", 0))
    trade_payables = float(d.get("TradePayables", 0))
    short_term_loans = float(d.get("ShortTermLoans", 0))
    long_term_loans = float(d.get("LongTermLoans", 0))
    
    # Odhady pro chybějící data
    loans_received = float(d.get("LoansReceived", 0))
    loans_repaid = float(d.get("LoansRepaid", 0))
    asset_sales = float(d.get("AssetSales", 0))
    
    # Odhad změny pracovního kapitálu (pokud chybí, odhadneme z bilance)
    working_capital_change = float(d.get("WorkingCapitalChange", 0))
    if working_capital_change == 0 and receivables > 0:
        # Jednoduchý odhad: 5-10% z tržeb jako změna pracovního kapitálu
        working_capital_change = revenue * 0.05
    
    # Počáteční stav hotovosti (pokud chybí, použijeme aktuální cash)
    cash_begin = float(d.get("CashBegin", cash * 0.8))  # odhad

    # --- Základní výpočty ---
    net_profit = float(d.get("NetProfit", revenue - cogs - overheads - depreciation - interest - taxation + extraordinary))
    
    # --- Cash Flow z provozní činnosti ---
    # Upravený výpočet: čistý zisk + odpisy - změna pracovního kapitálu
    operating_cf = net_profit + depreciation - working_capital_change
    
    # --- Cash Flow z investiční činnosti ---
    # CapEx odhadneme z tangible assets nebo jako % z tržeb
    capex = float(d.get("CapEx", d.get("FixedAssets", tangible_assets * 0.1)))
    if capex == 0 and revenue > 0:
        capex = revenue * 0.02  # 2% z tržeb jako průměrný CapEx
    
    investing_cf = asset_sales - capex
    
    # --- Cash Flow z finanční činnosti ---
    # Pokud nemáme explicitní data o úvěrech, odhadneme z bilance
    if loans_received == 0 and loans_repaid == 0:
        total_loans = short_term_loans + long_term_loans
        if total_loans > 0:
            # Odhad: pokud má firma úvěry, pravděpodobně část splatila
            loans_repaid = total_loans * 0.1  # 10% ročních splátek
            # A možná si vzala nové úvěry pro růst
            if revenue > 10000:  # pro větší firmy
                loans_received = revenue * 0.05  # 5% z tržeb jako nové úvěry
    
    financing_cf = loans_received - loans_repaid - dividends
    
    # --- Celková změna peněžních prostředků ---
    total_net_cash_flow = operating_cf + investing_cf + financing_cf
    cash_end = cash_begin + total_net_cash_flow

    return {
        # Pro template cashflow tabulku v index.html
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
        
        # Pro původní template cashflow.html (zachováváme kompatibilitu)
        "revenue": revenue,
        "cogs": cogs,
        "overheads": overheads,
        "interest": interest,
        "extraordinary": extraordinary,
        "taxation": taxation,
        "dividends": dividends,
        "fixed_assets": capex,  # použijeme capex jako fixed_assets
        "other_assets": 0,  # není v datech
        "capital_withdrawn": 0,  # není v datech
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
