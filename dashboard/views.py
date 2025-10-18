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

        # ZÃ¡kladnÃ­ vÃ½poÄty
        revenue = d.get("Revenue", 0)
        cogs = d.get("COGS", 0)
        gross_margin = revenue - cogs
        overheads = d.get("Overheads", 0)
        depreciation = d.get("Depreciation", 0)
        ebit = d.get("EBIT", gross_margin - overheads - depreciation)
        net_profit = d.get("NetProfit", 0)

        # Cashflow (jen zÃ¡kladnÃ­ bloky)
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

            # Profitability % (pomÄ›rovÃ© ukazatele)
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

            "growth": {}  # doplnÃ­me nÃ­Å¾e
        })

    # SeÅ™adit a pÅ™ipravit roky
    rows = sorted(rows, key=lambda r: r["year"])
    years = [r["year"] for r in rows]

    # MeziroÄnÃ­ rÅ¯sty
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

    # ðŸ’° VÃ½poÄet Cash Flow pro poslednÃ­ rok (pÅ™idÃ¡no z pÅ¯vodnÃ­ho kÃ³du)
    cf = None
    selected_year = years[-1] if years else None
    if selected_year:
        try:
            cf = calculate_cashflow(request.user, selected_year)
        except Exception as e:
            print(f"âš ï¸ Chyba vÃ½poÄtu cashflow: {e}")

    return render(request, "dashboard/index.html", {
        "rows": json.dumps(rows),
        "years": json.dumps(years),
        "table_rows": rows,
        "cashflow": cf,  # âœ… pÅ™idÃ¡no
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
    """API endpoint pro naÄÃ­tÃ¡nÃ­ Profit vs Cash Flow tabulky pro specifickÃ½ rok"""
    cf = calculate_cashflow(request.user, year)
    
    if cf:
        # VypoÄÃ­tÃ¡me variance (rozdÃ­ly)
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
        
        # Renderujeme Profit vs Cash Flow tabulku v ÄeÅ¡tinÄ› podle daÅˆovÃ©ho Å™Ã¡du ÄŒR
        cashflow_html = f'''
        <table class="table table-bordered align-middle mt-3">
          <thead class="table-dark text-center">
            <tr>
              <th width="35%">Zisk (ÃºÄetnÃ­)</th>
              <th width="35%">PenÄ›Å¾nÃ­ tok (hotovost)</th>
              <th width="30%">RozdÃ­l</th>
            </tr>
          </thead>
          <tbody>
            <!-- TrÅ¾by -->
            <tr>
              <td><strong>TrÅ¾by za prodej zboÅ¾Ã­ a sluÅ¾eb</strong> 
                <span data-bs-toggle="tooltip" title="ÃšÄetnÃ­ trÅ¾by dle Â§ 23 zÃ¡kona o ÃºÄetnictvÃ­ - zahrnujÃ­ vÅ¡echny faktury vystavenÃ© v danÃ©m obdobÃ­">â“</span>
                <br><span class="text-primary">{cf["revenue"]:,.0f} KÄ</span></td>
              <td><strong>PÅ™Ã­jmy od zÃ¡kaznÃ­kÅ¯</strong>
                <span data-bs-toggle="tooltip" title="SkuteÄnÄ› pÅ™ijatÃ© penÄ›Å¾nÃ­ prostÅ™edky od zÃ¡kaznÃ­kÅ¯ - liÅ¡Ã­ se od trÅ¾eb kvÅ¯li pohledÃ¡vkÃ¡m">â“</span>
                <br><span class="text-primary">{cf["revenue"] * 0.93:,.0f} KÄ</span></td>
              <td class="text-center">{format_variance((cf["revenue"] * 0.93) - cf["revenue"])}</td>
            </tr>
            
            <!-- NÃ¡klady na prodanÃ© zboÅ¾Ã­ -->
            <tr>
              <td><strong>NÃ¡klady na prodanÃ© zboÅ¾Ã­</strong>
                <span data-bs-toggle="tooltip" title="ÃšÄetnÃ­ nÃ¡klady na zboÅ¾Ã­ podle Â§ 25 zÃ¡kona o ÃºÄetnictvÃ­ - zaÃºÄtovanÃ© nÃ¡klady za prodanÃ© zboÅ¾Ã­">â“</span>
                <br><span class="text-danger">{cf["cogs"]:,.0f} KÄ</span></td>
              <td><strong>VÃ½daje dodavatelÅ¯m</strong>
                <span data-bs-toggle="tooltip" title="SkuteÄnÄ› zaplacenÃ© ÄÃ¡stky dodavatelÅ¯m - liÅ¡Ã­ se od nÃ¡kladÅ¯ kvÅ¯li zÃ¡vazkÅ¯m a zÃ¡sob">â“</span>
                <br><span class="text-danger">{cf["cogs"] * 0.98:,.0f} KÄ</span></td>
              <td class="text-center">{format_variance((cf["cogs"] * 0.98) - cf["cogs"])}</td>
            </tr>
            
            <!-- HrubÃ¡ marÅ¾e -->
            <tr class="table-light">
              <td><strong>HrubÃ¡ marÅ¾e</strong>
                <span data-bs-toggle="tooltip" title="HrubÃ½ zisk = TrÅ¾by - NÃ¡klady na prodanÃ© zboÅ¾Ã­. ZÃ¡kladnÃ­ ukazatel ziskovosti obchodnÃ­ Äinnosti">â“</span>
                <br><span class="fw-bold text-success">{cf["gross_margin"]:,.0f} KÄ</span></td>
              <td><strong>HrubÃ½ penÄ›Å¾nÃ­ tok</strong>
                <span data-bs-toggle="tooltip" title="SkuteÄnÃ¡ hotovost z obchodnÃ­ Äinnosti = PÅ™Ã­jmy od zÃ¡kaznÃ­kÅ¯ - VÃ½daje dodavatelÅ¯m">â“</span>
                <br><span class="fw-bold text-success">{cf["gross_cash_profit"]:,.0f} KÄ</span></td>
              <td class="text-center fw-bold">{format_variance(cf["gross_cash_profit"] - cf["gross_margin"])}</td>
            </tr>
            
            <!-- ProvoznÃ­ nÃ¡klady -->
            <tr>
              <td><strong>ProvoznÃ­ nÃ¡klady (bez odpisÅ¯)</strong><br><span class="text-warning">{cf["overheads"]:,.0f} KÄ</span></td>
              <td><strong>ProvoznÃ­ nÃ¡klady (bez odpisÅ¯)</strong><br><span class="text-warning">{cf["overheads"]:,.0f} KÄ</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- ProvoznÃ­ zisk -->
            <tr class="table-light">
              <td><strong>ProvoznÃ­ zisk</strong><br><span class="fw-bold text-info">{cf["operating_cash_profit"]:,.0f} KÄ</span></td>
              <td><strong>ProvoznÃ­ penÄ›Å¾nÃ­ tok</strong><br><span class="fw-bold text-info">{cf["operating_cash_flow"]:,.0f} KÄ</span></td>
              <td class="text-center fw-bold">{format_variance(cf["operating_cash_flow"] - cf["operating_cash_profit"])}</td>
            </tr>
            
            <!-- OstatnÃ­ penÄ›Å¾nÃ­ vÃ½daje header -->
            <tr class="table-secondary">
              <td colspan="2" class="text-center"><strong>OstatnÃ­ penÄ›Å¾nÃ­ vÃ½daje</strong></td>
              <td></td>
            </tr>
            
            <!-- Ãšroky -->
            <tr>
              <td><strong>NÃ¡kladovÃ© Ãºroky</strong><br><span class="text-danger">-{cf["interest"]:,.0f} KÄ</span></td>
              <td><strong>ZaplacenÃ© Ãºroky</strong><br><span class="text-danger">-{cf["interest"]:,.0f} KÄ</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- DanÄ› -->
            <tr>
              <td><strong>DaÅˆ z pÅ™Ã­jmÅ¯</strong>
                <span data-bs-toggle="tooltip" title="ÃšÄetnÃ­ daÅˆ z pÅ™Ã­jmÅ¯ podle Â§ 59 zÃ¡kona o ÃºÄetnictvÃ­ - splatnÃ¡ i odloÅ¾enÃ¡ daÅˆ">â“</span>
                <br><span class="text-danger">{cf["taxation"]:,.0f} KÄ</span></td>
              <td><strong>ZaplacenÃ¡ daÅˆ z pÅ™Ã­jmÅ¯</strong>
                <span data-bs-toggle="tooltip" title="SkuteÄnÄ› zaplacenÃ¡ daÅˆ z pÅ™Ã­jmÅ¯ na ÃºÄet finanÄnÃ­ho ÃºÅ™adu">â“</span>
                <br><span class="text-danger">{cf["taxation"]:,.0f} KÄ</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- MimoÅ™Ã¡dnÃ© vÃ½nosy -->
            <tr>
              <td><strong>MimoÅ™Ã¡dnÃ© vÃ½nosy</strong><br><span class="text-success">+{cf["extraordinary"]:,.0f} KÄ</span></td>
              <td><strong>MimoÅ™Ã¡dnÃ© pÅ™Ã­jmy</strong><br><span class="text-success">+{cf["extraordinary"]:,.0f} KÄ</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- PodÃ­ly na zisku/Dividendy -->
            <tr>
              <td><strong>PodÃ­ly na zisku/Dividendy</strong><br><span class="text-danger">{cf["dividends"]:,.0f} KÄ</span></td>
              <td><strong>VyplacenÃ© podÃ­ly/Dividendy</strong><br><span class="text-danger">{cf["dividends"]:,.0f} KÄ</span></td>
              <td class="text-center"><span class="text-muted">-</span></td>
            </tr>
            
            <!-- Odpisy -->
            <tr>
              <td><strong>Odpisy dlouhodobÃ©ho majetku</strong>
                <span data-bs-toggle="tooltip" title="ÃšÄetnÃ­ odpisy podle Â§ 56 zÃ¡kona o ÃºÄetnictvÃ­ - vyjadÅ™ujÃ­ opotÅ™ebenÃ­ majetku, nejednÃ¡ se o penÄ›Å¾nÃ­ vÃ½daj">â“</span>
                <br><span class="text-warning">-{cf["depreciation"]:,.0f} KÄ</span></td>
              <td><strong>PoÅ™Ã­zenÃ­ dlouhodobÃ©ho majetku</strong>
                <span data-bs-toggle="tooltip" title="SkuteÄnÃ© penÄ›Å¾nÃ­ vÃ½daje na nÃ¡kup dlouhodobÃ©ho majetku (budovy, stroje, vybavenÃ­)">â“</span>
                <br><span class="text-danger">-{cf["fixed_assets"]:,.0f} KÄ</span></td>
              <td class="text-center">{format_variance(-cf["fixed_assets"] + cf["depreciation"])}</td>
            </tr>
            
            <!-- OstatnÃ­ aktiva -->
            <tr>
              <td></td>
              <td><strong>NÃ¡rÅ¯st ostatnÃ­ch aktiv</strong><br><span class="text-danger">-{cf["other_assets"]:,.0f} KÄ</span></td>
              <td class="text-center">{format_variance(-cf["other_assets"])}</td>
            </tr>
            
            <!-- VÃ½bÄ›r kapitÃ¡lu -->
            <tr>
              <td></td>
              <td><strong>VÃ½bÄ›r zÃ¡kladnÃ­ho kapitÃ¡lu</strong><br><span class="text-danger">-{cf["capital_withdrawn"]:,.0f} KÄ</span></td>
              <td class="text-center">{format_variance(-cf["capital_withdrawn"])}</td>
            </tr>
            
            <!-- CelkovÃ© souÄty -->
            <tr class="table-dark">
              <td><strong>Zisk po zdanÄ›nÃ­ (nerozdÄ›lenÃ½)</strong>
                <span data-bs-toggle="tooltip" title="ÃšÄetnÃ­ vÃ½sledek hospodaÅ™enÃ­ po zdanÄ›nÃ­ - zisk, kterÃ½ mÅ¯Å¾e bÃ½t reinvestovÃ¡n nebo vyplacen akcionÃ¡Å™Å¯m">â“</span>
                <br><span class="fw-bold text-light">{cf["retained_profit"]:,.0f} KÄ</span></td>
              <td><strong>ÄŒistÃ½ penÄ›Å¾nÃ­ tok</strong>
                <span data-bs-toggle="tooltip" title="SkuteÄnÃ¡ zmÄ›na hotovosti za obdobÃ­ - rozdÃ­l mezi vÅ¡emi pÅ™Ã­jmy a vÃ½daji">â“</span>
                <br><span class="fw-bold text-light">{cf["net_cash_flow"]:,.0f} KÄ</span></td>
              <td class="text-center fw-bold">{format_variance(cf["net_cash_flow"] - cf["retained_profit"])}</td>
            </tr>
          </tbody>
        </table>
        '''
        return HttpResponse(cashflow_html)
    else:
        error_html = f'''
        <div class="alert alert-warning mt-3">
          âš ï¸ AnalÃ½zu Zisk vs PenÄ›Å¾nÃ­ tok zatÃ­m nebylo moÅ¾nÃ© vypoÄÃ­tat pro rok {year} â€“ zkontrolujte, Å¾e mÃ¡te nahranÃ© finanÄnÃ­ vÃ½kazy pro tento rok.
        </div>
        '''
        return HttpResponse(error_html)


@csrf_exempt
def save_chart(request):
    """UloÅ¾Ã­ pÅ™ijatÃ½ base64 PNG z frontendu do MEDIA_ROOT/charts/."""
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

        # ðŸŸ¢ Ujisti se, Å¾e sloÅ¾ka charts existuje
        charts_dir = os.path.join(settings.MEDIA_ROOT, "charts")
        os.makedirs(charts_dir, exist_ok=True)

        file_name = f"chart_{chart_id}.png"
        file_path = os.path.join(charts_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(image_binary)

        print(f"âœ… Graf uloÅ¾en: {file_path}")  # volitelnÃ½ log
        return JsonResponse({"status": "ok", "file": file_path})

    return JsonResponse({"status": "error", "message": "invalid method"}, status=405)


def export_full_pdf(request):
    """
    VytvoÅ™Ã­ PDF, do kterÃ©ho vloÅ¾Ã­ vÅ¡echny PNG grafy z MEDIA_ROOT
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("ðŸ“Š Financial Dashboard", styles["Title"]))
    elements.append(Spacer(1, 12))

    # projdi vÅ¡echny chart_*.png v MEDIA_ROOT
    for fname in sorted(os.listdir(settings.MEDIA_ROOT)):
        if fname.startswith("chart_") and fname.endswith(".png"):
            chart_path = os.path.join(settings.MEDIA_ROOT, fname)
            elements.append(Image(chart_path, width=400, height=250))
            elements.append(Spacer(1, 24))

    doc.build(elements)
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename="financial_dashboard.pdf")


def api_metrics_series(request):
    """
    VrÃ¡tÃ­ ÄasovÃ© Å™ady klÃ­ÄovÃ½ch metrik a YoY rÅ¯sty pro pÅ™ihlÃ¡Å¡enÃ©ho uÅ¾ivatele.
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": "PÅ™ihlaste se."}
        }, status=401)

    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    rows = []
    for s in statements:
        d = s.data or {}
        revenue = float(d.get("Revenue", 0))
        cogs = float(d.get("COGS", 0))
        overheads = float(d.get("Overheads", 0))
        depreciation = float(d.get("Depreciation", 0))
        ebit = float(d.get("EBIT", (revenue - cogs - overheads - depreciation)))
        net_profit = float(d.get("NetProfit", (revenue - cogs - overheads - depreciation)))
        rows.append({
            "year": int(s.year),
            "revenue": revenue,
            "cogs": cogs,
            "overheads": overheads,
            "ebit": ebit,
            "net_profit": net_profit,
        })

    rows = sorted(rows, key=lambda r: r["year"])
    years = [r["year"] for r in rows]

    margins = []
    for r in rows:
        rev = r["revenue"]
        gm = (r["revenue"] - r["cogs"]) if rev else 0
        op = (r["revenue"] - r["cogs"] - r["overheads"]) if rev else 0
        np = r["net_profit"]
        margins.append({
            "year": r["year"],
            "gm_pct": (gm / rev * 100) if rev else 0.0,
            "op_pct": (op / rev * 100) if rev else 0.0,
            "np_pct": (np / rev * 100) if rev else 0.0,
        })

    yoy = []
    for i, r in enumerate(rows):
        if i == 0:
            yoy.append({
                "year": r["year"],
                "revenue_yoy": None,
                "cogs_yoy": None,
                "overheads_yoy": None,
                "net_profit_yoy": None,
                "ebit_yoy": None,
            })
        else:
            p = rows[i-1]
            def growth(cur, prev):
                try:
                    if prev and prev != 0:
                        return (cur - prev) / abs(prev) * 100.0
                except Exception:
                    pass
                return None
            yoy.append({
                "year": r["year"],
                "revenue_yoy": growth(r["revenue"], p["revenue"]),
                "cogs_yoy": growth(r["cogs"], p["cogs"]),
                "overheads_yoy": growth(r["overheads"], p["overheads"]),
                "net_profit_yoy": growth(r["net_profit"], p["net_profit"]),
                "ebit_yoy": growth(r["ebit"], p["ebit"]),
            })

    return JsonResponse({
        "success": True,
        "years": years,
        "series": rows,
        "margins": margins,
        "yoy": yoy,
    })

@login_required
def api_profitability(request):
    """Vrací přehled ziskovosti (náhrada za templates/dashboard/profitability.html)."""
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    rows = []
    for stmt in statements:
        data = stmt.data or {}
        revenue = float(data.get("Revenue", 0))
        cogs = float(data.get("COGS", 0))
        overheads = float(data.get("Overheads", 0))
        depreciation = float(data.get("Depreciation", 0))
        gross_margin = float(data.get("GrossMargin", revenue - cogs))
        ebit = float(data.get("EBIT", revenue - cogs - overheads - depreciation))
        net_profit = float(data.get("NetProfit", revenue - cogs - overheads - depreciation))

        gm_pct = (gross_margin / revenue * 100) if revenue else 0.0
        op_pct = (ebit / revenue * 100) if revenue else 0.0
        np_pct = (net_profit / revenue * 100) if revenue else 0.0

        rows.append({
            "year": stmt.year,
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "overheads": overheads,
            "ebit": ebit,
            "net_profit": net_profit,
            "gm_pct": gm_pct,
            "op_pct": op_pct,
            "np_pct": np_pct,
        })

    return JsonResponse({"success": True, "rows": rows})


@login_required
def api_cashflow_summary(request):
    """
    Vrací souhrn pro stránku cashflow:
    - seznam dostupných roků
    - detailní výpočet pro vybraný rok (výchozí poslední dostupný nebo ?year=)
    """
    years = list(
        FinancialStatement.objects.filter(owner=request.user)
        .values_list("year", flat=True)
        .order_by("year")
    )
    if not years:
        return JsonResponse({"success": True, "years": [], "current_year": None, "cashflow": None})

    try:
        selected_year = int(request.GET.get("year", years[-1]))
    except (TypeError, ValueError):
        selected_year = years[-1]

    if selected_year not in years:
        selected_year = years[-1]

    cf = calculate_cashflow(request.user, selected_year) or {}

    return JsonResponse({
        "success": True,
        "years": years,
        "current_year": selected_year,
        "cashflow": cf,
    })
