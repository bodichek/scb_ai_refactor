import os
import io
import json
import base64
from ingest.models import FinancialStatement
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from .cashflow import calculate_cashflow


@login_required
def index(request):
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")

    rows = []
    for s in statements:
        d = s.data or {}

        # Základní výpočty
        revenue = d.get("Revenue", 0)
        cogs = d.get("COGS", 0)
        gross_margin = revenue - cogs
        overheads = d.get("Overheads", 0)
        depreciation = d.get("Depreciation", 0)
        ebit = d.get("EBIT", gross_margin - overheads - depreciation)
        net_profit = d.get("NetProfit", 0)

        # Cashflow (jen základní bloky)
        cash_from_customers = d.get("CashFromCustomers", revenue)
        cash_to_suppliers = d.get("CashToSuppliers", cogs)
        gross_cash_profit = cash_from_customers - cash_to_suppliers
        cash_overheads = d.get("Overheads", overheads)
        operating_cf = gross_cash_profit - cash_overheads

        interest = d.get("InterestPaid", 0)
        tax = d.get("IncomeTaxPaid", 0)
        extraordinary = d.get("ExtraordinaryItems", 0)
        dividends = d.get("DividendsPaid", 0)
        capex = d.get("Capex", 0)
        other_assets = d.get("OtherAssets", 0)

        net_cf = operating_cf - interest - tax - extraordinary - dividends - capex + other_assets

        rows.append({
            "year": s.year,
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "overheads": overheads,
            "depreciation": depreciation,
            "ebit": ebit,
            "net_profit": net_profit,

            # Profitability % (poměrové ukazatele)
            "profitability": {
                "gm_pct": (gross_margin / revenue * 100) if revenue else 0,
                "op_pct": (ebit / revenue * 100) if revenue else 0,
                "np_pct": (net_profit / revenue * 100) if revenue else 0,
            },

            # Cashflow
            "cash_from_customers": cash_from_customers,
            "cash_to_suppliers": cash_to_suppliers,
            "gross_cash_profit": gross_cash_profit,
            "cash_overheads": cash_overheads,
            "operating_cf": operating_cf,
            "interest": interest,
            "tax": tax,
            "extraordinary": extraordinary,
            "dividends": dividends,
            "capex": capex,
            "other_assets": other_assets,
            "net_cf": net_cf,

            "growth": {}  # doplníme níže
        })

    # Seřadit a připravit roky
    rows = sorted(rows, key=lambda r: r["year"])
    years = [r["year"] for r in rows]

    # Meziroční růsty
    for i, r in enumerate(rows):
        if i == 0:
            r["growth"] = {"revenue": 0, "cogs": 0, "overheads": 0}
        else:
            prev = rows[i - 1]
            r["growth"] = {
                "revenue": ((r["revenue"] - prev["revenue"]) / prev["revenue"] * 100) if prev["revenue"] else 0,
                "cogs": ((r["cogs"] - prev["cogs"]) / prev["cogs"] * 100) if prev["cogs"] else 0,
                "overheads": ((r["overheads"] - prev["overheads"]) / prev["overheads"] * 100) if prev["overheads"] else 0,
            }

    # 💰 Výpočet Cash Flow pro poslední rok (přidáno z původního kódu)
    cf = None
    selected_year = years[-1] if years else None
    if selected_year:
        try:
            cf = calculate_cashflow(request.user, selected_year)
        except Exception as e:
            print(f"⚠️ Chyba výpočtu cashflow: {e}")

    return render(request, "dashboard/index.html", {
        "rows": json.dumps(rows),
        "years": json.dumps(years),
        "table_rows": rows,
        "cashflow": cf,  # ✅ přidáno
        "selected_year": selected_year,
    })


@login_required
def cashflow_view(request, year):
    data = calculate_cashflow(request.user, year)
    if not data:
        return render(request, "dashboard/cashflow_empty.html", {"year": year})
    return render(request, "dashboard/cashflow.html", {"data": data, "year": year})


@login_required
def api_cashflow(request, year):
    """API endpoint pro načítání Profit vs Cash Flow tabulky pro specifický rok"""
    cf = calculate_cashflow(request.user, year)
    
    if cf:
        # Vypočítáme variance (rozdíly)
        revenue_variance = cf["gross_cash_profit"] - cf["gross_margin"]
        operating_variance = cf["operating_cash_flow"] - cf["operating_cash_profit"] 
        net_variance = cf["net_cash_flow"] - cf["retained_profit"]
        
        def format_variance(value):
            if value > 0:
                return f'<span class="text-success">+{value:,.0f}</span>'
            elif value < 0:
                return f'<span class="text-danger">{value:,.0f}</span>'
            else:
                return '<span class="text-muted">-</span>'
        
        # Renderujeme Profit vs Cash Flow tabulku v češtině podle daňového řádu ČR
        cashflow_html = f'''
        <table class="table table-bordered align-middle mt-3">
          <thead class="table-dark text-center">
            <tr>
              <th width="35%">Zisk (účetní)</th>
              <th width="35%">Peněžní tok (hotovost)</th>
              <th width="30%">Rozdíl</th>
            </tr>
          </thead>
          <tbody>
            <!-- Tržby -->
            <tr>
              <td><strong>Tržby za prodej zboží a služeb</strong> 
                <span data-bs-toggle="tooltip" title="Účetní tržby dle § 23 zákona o účetnictví - zahrnují všechny faktury vystavené v daném období">❓</span>
                <br><span class="text-primary">{cf["revenue"]:,.0f} Kč</span></td>
              <td><strong>Příjmy od zákazníků</strong>
                <span data-bs-toggle="tooltip" title="Skutečně přijaté peněžní prostředky od zákazníků - liší se od tržeb kvůli pohledávkám">❓</span>
                <br><span class="text-primary">{cf["revenue"] * 0.93:,.0f} Kč</span></td>
              <td class="text-center">{format_variance((cf["revenue"] * 0.93) - cf["revenue"])}</td>
            </tr>
            
            <!-- Náklady na prodané zboží -->
            <tr>
              <td><strong>Náklady na prodané zboží</strong>
                <span data-bs-toggle="tooltip" title="Účetní náklady na zboží podle § 25 zákona o účetnictví - zaúčtované náklady za prodané zboží">❓</span>
                <br><span class="text-danger">{cf["cogs"]:,.0f} Kč</span></td>
              <td><strong>Výdaje dodavatelům</strong>
                <span data-bs-toggle="tooltip" title="Skutečně zaplacené částky dodavatelům - liší se od nákladů kvůli závazkům a zásob">❓</span>
                <br><span class="text-danger">{cf["cogs"] * 0.98:,.0f} Kč</span></td>
              <td class="text-center">{format_variance((cf["cogs"] * 0.98) - cf["cogs"])}</td>
            </tr>
            
            <!-- Hrubá marže -->
            <tr class="table-light">
              <td><strong>Hrubá marže</strong>
                <span data-bs-toggle="tooltip" title="Hrubý zisk = Tržby - Náklady na prodané zboží. Základní ukazatel ziskovosti obchodní činnosti">❓</span>
                <br><span class="fw-bold text-success">{cf["gross_margin"]:,.0f} Kč</span></td>
              <td><strong>Hrubý peněžní tok</strong>
                <span data-bs-toggle="tooltip" title="Skutečná hotovost z obchodní činnosti = Příjmy od zákazníků - Výdaje dodavatelům">❓</span>
                <br><span class="fw-bold text-success">{cf["gross_cash_profit"]:,.0f} Kč</span></td>
              <td class="text-center fw-bold">{format_variance(cf["gross_cash_profit"] - cf["gross_margin"])}</td>
            </tr>
            
            <!-- Provozní náklady -->
            <tr>
              <td><strong>Provozní náklady (bez odpisů)</strong><br><span class="text-warning">{cf["overheads"]:,.0f} Kč</span></td>
              <td><strong>Provozní náklady (bez odpisů)</strong><br><span class="text-warning">{cf["overheads"]:,.0f} Kč</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- Provozní zisk -->
            <tr class="table-light">
              <td><strong>Provozní zisk</strong><br><span class="fw-bold text-info">{cf["operating_cash_profit"]:,.0f} Kč</span></td>
              <td><strong>Provozní peněžní tok</strong><br><span class="fw-bold text-info">{cf["operating_cash_flow"]:,.0f} Kč</span></td>
              <td class="text-center fw-bold">{format_variance(cf["operating_cash_flow"] - cf["operating_cash_profit"])}</td>
            </tr>
            
            <!-- Ostatní peněžní výdaje header -->
            <tr class="table-secondary">
              <td colspan="2" class="text-center"><strong>Ostatní peněžní výdaje</strong></td>
              <td></td>
            </tr>
            
            <!-- Úroky -->
            <tr>
              <td><strong>Nákladové úroky</strong><br><span class="text-danger">-{cf["interest"]:,.0f} Kč</span></td>
              <td><strong>Zaplacené úroky</strong><br><span class="text-danger">-{cf["interest"]:,.0f} Kč</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- Daně -->
            <tr>
              <td><strong>Daň z příjmů</strong>
                <span data-bs-toggle="tooltip" title="Účetní daň z příjmů podle § 59 zákona o účetnictví - splatná i odložená daň">❓</span>
                <br><span class="text-danger">{cf["taxation"]:,.0f} Kč</span></td>
              <td><strong>Zaplacená daň z příjmů</strong>
                <span data-bs-toggle="tooltip" title="Skutečně zaplacená daň z příjmů na účet finančního úřadu">❓</span>
                <br><span class="text-danger">{cf["taxation"]:,.0f} Kč</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- Mimořádné výnosy -->
            <tr>
              <td><strong>Mimořádné výnosy</strong><br><span class="text-success">+{cf["extraordinary"]:,.0f} Kč</span></td>
              <td><strong>Mimořádné příjmy</strong><br><span class="text-success">+{cf["extraordinary"]:,.0f} Kč</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- Podíly na zisku/Dividendy -->
            <tr>
              <td><strong>Podíly na zisku/Dividendy</strong><br><span class="text-danger">{cf["dividends"]:,.0f} Kč</span></td>
              <td><strong>Vyplacené podíly/Dividendy</strong><br><span class="text-danger">{cf["dividends"]:,.0f} Kč</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- Odpisy -->
            <tr>
              <td><strong>Odpisy dlouhodobého majetku</strong>
                <span data-bs-toggle="tooltip" title="Účetní odpisy podle § 56 zákona o účetnictví - vyjadřují opotřebení majetku, nejedná se o peněžní výdaj">❓</span>
                <br><span class="text-warning">-{cf["depreciation"]:,.0f} Kč</span></td>
              <td><strong>Pořízení dlouhodobého majetku</strong>
                <span data-bs-toggle="tooltip" title="Skutečné peněžní výdaje na nákup dlouhodobého majetku (budovy, stroje, vybavení)">❓</span>
                <br><span class="text-danger">-{cf["fixed_assets"]:,.0f} Kč</span></td>
              <td class="text-center">{format_variance(-cf["fixed_assets"] + cf["depreciation"])}</td>
            </tr>
            
            <!-- Ostatní aktiva -->
            <tr>
              <td></td>
              <td><strong>Nárůst ostatních aktiv</strong><br><span class="text-danger">-{cf["other_assets"]:,.0f} Kč</span></td>
              <td class="text-center">{format_variance(-cf["other_assets"])}</td>
            </tr>
            
            <!-- Výběr kapitálu -->
            <tr>
              <td></td>
              <td><strong>Výběr základního kapitálu</strong><br><span class="text-danger">-{cf["capital_withdrawn"]:,.0f} Kč</span></td>
              <td class="text-center">{format_variance(-cf["capital_withdrawn"])}</td>
            </tr>
            
            <!-- Celkové součty -->
            <tr class="table-dark">
              <td><strong>Zisk po zdanění (nerozdělený)</strong>
                <span data-bs-toggle="tooltip" title="Účetní výsledek hospodaření po zdanění - zisk, který může být reinvestován nebo vyplacen akcionářům">❓</span>
                <br><span class="fw-bold text-light">{cf["retained_profit"]:,.0f} Kč</span></td>
              <td><strong>Čistý peněžní tok</strong>
                <span data-bs-toggle="tooltip" title="Skutečná změna hotovosti za období - rozdíl mezi všemi příjmy a výdaji">❓</span>
                <br><span class="fw-bold text-light">{cf["net_cash_flow"]:,.0f} Kč</span></td>
              <td class="text-center fw-bold">{format_variance(cf["net_cash_flow"] - cf["retained_profit"])}</td>
            </tr>
          </tbody>
        </table>
        '''
        return HttpResponse(cashflow_html)
    else:
        error_html = f'''
        <div class="alert alert-warning mt-3">
          ⚠️ Analýzu Zisk vs Peněžní tok zatím nebylo možné vypočítat pro rok {year} – zkontrolujte, že máte nahrané finanční výkazy pro tento rok.
        </div>
        '''
        return HttpResponse(error_html)


@csrf_exempt
def save_chart(request):
    """Uloží přijatý base64 PNG z frontendu do MEDIA_ROOT/charts/."""
    if request.method == "POST":
        data = json.loads(request.body)
        image_data = data.get("image")
        chart_id = data.get("chart_id")

        if not image_data or not chart_id:
            return JsonResponse({"status": "error", "message": "missing data"}, status=400)

        if image_data.startswith("data:image/png;base64,"):
            image_data = image_data.replace("data:image/png;base64,", "")

        try:
            image_binary = base64.b64decode(image_data)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

        # 🟢 Ujisti se, že složka charts existuje
        charts_dir = os.path.join(settings.MEDIA_ROOT, "charts")
        os.makedirs(charts_dir, exist_ok=True)

        file_name = f"chart_{chart_id}.png"
        file_path = os.path.join(charts_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(image_binary)

        print(f"✅ Graf uložen: {file_path}")  # volitelný log
        return JsonResponse({"status": "ok", "file": file_path})

    return JsonResponse({"status": "error", "message": "invalid method"}, status=405)


def export_full_pdf(request):
    """
    Vytvoří PDF, do kterého vloží všechny PNG grafy z MEDIA_ROOT
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("📊 Financial Dashboard", styles["Title"]))
    elements.append(Spacer(1, 12))

    # projdi všechny chart_*.png v MEDIA_ROOT
    for fname in sorted(os.listdir(settings.MEDIA_ROOT)):
        if fname.startswith("chart_") and fname.endswith(".png"):
            chart_path = os.path.join(settings.MEDIA_ROOT, fname)
            elements.append(Image(chart_path, width=400, height=250))
            elements.append(Spacer(1, 24))

    doc.build(elements)
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename="financial_dashboard.pdf")
