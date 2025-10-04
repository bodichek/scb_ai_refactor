import os
import io
import json
import base64
from ingest.models import FinancialStatement
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt   # ⬅️ TOTO ti chybělo
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet


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

    return render(request, "dashboard/index.html", {
        "rows": json.dumps(rows),   # JSON pro grafy
        "years": json.dumps(years),
        "table_rows": rows,         # pro tabulkový přehled
    })


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