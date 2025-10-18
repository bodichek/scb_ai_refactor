import os
import base64
import json
import re
from io import BytesIO
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ingest.models import FinancialStatement
from survey.models import SurveySubmission, Response
from suropen.models import OpenAnswer
from accounts.models import CompanyProfile

# ✅ import výpočtu Cash Flow (nový modul)
try:
    from dashboard.cashflow import calculate_cashflow
except ImportError:
    calculate_cashflow = None


# 🧩 Grafy z dashboardu
@csrf_exempt
def upload_chart(request):
    """Uloží base64 obrázek (graf z dashboardu) do MEDIA_ROOT/charts/."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method."}, status=405)

    try:
        body = json.loads(request.body.decode("utf-8"))
        image_data = body.get("image")
        chart_id = body.get("chart_id", "unknown")

        if not image_data:
            return JsonResponse({"error": "Missing image data."}, status=400)

        chart_dir = os.path.join(settings.MEDIA_ROOT, "charts")
        os.makedirs(chart_dir, exist_ok=True)

        image_data = re.sub("^data:image/[^;]+;base64,", "", image_data)
        image_bytes = base64.b64decode(image_data)

        filename = f"chart_{chart_id}.png"
        file_path = os.path.join(chart_dir, filename)

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        return JsonResponse({"success": True, "file": filename})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# 🧾 Formulář pro export PDF
@login_required
def export_form(request):
    """Formulář s volbou sekcí + nově i výběrem roku."""
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    available_years = [s.year for s in statements]
    return render(request, "exports/export_form.html", {"years": available_years})


# 📘 Generování PDF exportu
@login_required
def export_pdf(request):
    """Generuje profesionální PDF report s možností výběru roku a Profit vs Cash Flow."""
    user = request.user
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    selected_sections = request.POST.getlist("sections") or ["charts", "tables", "survey", "suropen"]
    year = int(request.POST.get("year", 0)) or None

    # 📑 Fonty a styly
        # 📑 Fonty a styly (DejaVuSans z /static/fonts)
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")

    try:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("DejaVu", font_path))
            print(f"✅ Font DejaVuSans načten z: {font_path}")
        else:
            print(f"⚠️ Font DejaVuSans nenalezen na cestě: {font_path}")
            # Fallback — použije vestavěný font, aby PDF nespadlo
            pdfmetrics.registerFont(TTFont("Helvetica", "Helvetica"))
    except Exception as e:
        print(f"❌ Chyba při načítání fontu DejaVuSans: {e}")

    styles = getSampleStyleSheet()
    for s in styles.byName.values():
        s.fontName = "DejaVu"
    styles.add(ParagraphStyle(name="WrapText", fontName="DejaVu", leading=14, fontSize=10))

    def clean_text(text):
        if not text:
            return ""
        txt = re.sub(r"[\*\#\_]+", "", str(text))
        txt = txt.replace("•", "-")
        return txt.strip()

    story = []
    

    # 🏢 HLAVIČKA (beze změn)
    company = CompanyProfile.objects.filter(user=user).first()
    story.append(Paragraph("Firemní přehled", styles["Heading1"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Datum exportu: {timezone.localtime().strftime('%d.%m.%Y %H:%M')}", styles["Normal"]))
    if company:
        story.append(Paragraph(f"Firma: {clean_text(company.company_name)}", styles["Normal"]))
        story.append(Paragraph(f"IČO: {company.ico or '—'}", styles["Normal"]))
        story.append(Paragraph(f"Kontaktní osoba: {clean_text(company.contact_person) or '—'}", styles["Normal"]))
    else:
        story.append(Paragraph(f"Uživatel: {user.get_full_name() or user.username}", styles["Normal"]))
    story.append(PageBreak())

    # 📊 GRAFY A TABULKY
    if "charts" in selected_sections or "tables" in selected_sections:
        story.append(Paragraph("Finanční přehled", styles["Heading1"]))
        story.append(Spacer(1, 8))

        chart_titles = [
            "Váš příběh zisku",
            "Trend ziskovosti",
            "Růst tržeb vs. růst nákladů na prodané zboží",
            "Růst tržeb vs. růst provozních nákladů",
            "Meziroční přehled hlavních metrik",
        ]

        # 🧩 Grafy (beze změn)
        if "charts" in selected_sections:
            chart_dir = os.path.join(settings.MEDIA_ROOT, "charts")
            if os.path.exists(chart_dir):
                charts = [f for f in os.listdir(chart_dir) if f.startswith("chart_") and f.endswith(".png")]
                if charts:
                    for i, ch in enumerate(sorted(charts)):
                        img_path = os.path.join(chart_dir, ch)
                        title = chart_titles[i] if i < len(chart_titles) else f"Graf {i+1}"
                        story.append(Paragraph(title, styles["Heading2"]))
                        story.append(Image(img_path, width=460, height=210))
                        story.append(Spacer(1, 10))
                else:
                    story.append(Paragraph("❗ Nebyly nalezeny žádné uložené grafy.", styles["Normal"]))
            else:
                story.append(Paragraph("❗ Složka s grafy neexistuje.", styles["Normal"]))
            story.append(Spacer(1, 15))

        # 🧾 Kompletní finanční tabulky (jako v dashboardu)
        statements = FinancialStatement.objects.filter(owner=user).order_by("year")
        if statements.exists():
            # 📊 PŘEHLED DAT - kompletní tabulka jako v dashboardu
            story.append(Paragraph("📑 Přehled dat", styles["Heading2"]))
            
            # Sestavíme data pro tabulku
            rows = []
            for s in statements:
                d = s.data or {}
                revenue = d.get("Revenue", 0)
                cogs = d.get("COGS", 0)
                gross_margin = revenue - cogs
                overheads = d.get("Overheads", 0)
                depreciation = d.get("Depreciation", 0)
                ebit = d.get("EBIT", gross_margin - overheads - depreciation)
                net_profit = d.get("NetProfit", 0)
                
                # Profitability %
                gm_pct = (gross_margin / revenue * 100) if revenue else 0
                op_pct = (ebit / revenue * 100) if revenue else 0
                np_pct = (net_profit / revenue * 100) if revenue else 0
                
                rows.append({
                    "year": s.year,
                    "revenue": revenue,
                    "cogs": cogs,
                    "gross_margin": gross_margin,
                    "overheads": overheads,
                    "ebit": ebit,
                    "net_profit": net_profit,
                    "gm_pct": gm_pct,
                    "op_pct": op_pct,
                    "np_pct": np_pct
                })
            
            # Meziroční růsty
            for i, r in enumerate(rows):
                if i == 0:
                    r["revenue_growth"] = 0
                    r["cogs_growth"] = 0
                    r["overheads_growth"] = 0
                else:
                    prev = rows[i - 1]
                    r["revenue_growth"] = ((r["revenue"] - prev["revenue"]) / prev["revenue"] * 100) if prev["revenue"] else 0
                    r["cogs_growth"] = ((r["cogs"] - prev["cogs"]) / prev["cogs"] * 100) if prev["cogs"] else 0
                    r["overheads_growth"] = ((r["overheads"] - prev["overheads"]) / prev["overheads"] * 100) if prev["overheads"] else 0

            # Vytvoření tabulky
            data = [[
                "Rok", "Tržby (Kč)", "Náklady na prodané zboží (Kč)", "Hrubá marže (Kč)",
                "Provozní náklady (Kč)", "EBIT (Kč)", "Čistý zisk (Kč)",
                "Hrubá marže %", "Provozní marže %", "Čistá marže %",
                "Růst tržeb %", "Růst nákladů na prodané zboží %", "Růst provozních nákladů %"
            ]]
            
            for r in rows:
                data.append([
                    str(r["year"]),
                    f"{r['revenue']:,.0f}".replace(",", " "),
                    f"{r['cogs']:,.0f}".replace(",", " "),
                    f"{r['gross_margin']:,.0f}".replace(",", " "),
                    f"{r['overheads']:,.0f}".replace(",", " "),
                    f"{r['ebit']:,.0f}".replace(",", " "),
                    f"{r['net_profit']:,.0f}".replace(",", " "),
                    f"{r['gm_pct']:.1f}%",
                    f"{r['op_pct']:.1f}%",
                    f"{r['np_pct']:.1f}%",
                    f"{r['revenue_growth']:.1f}%",
                    f"{r['cogs_growth']:.1f}%",
                    f"{r['overheads_growth']:.1f}%"
                ])
            
            t = Table(data, colWidths=[30, 40, 40, 40, 40, 40, 40, 35, 35, 35, 35, 45, 45])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),  # Rok - center
                ("ALIGN", (1, 1), (6, -1), "RIGHT"),   # Číselné hodnoty - vpravo
                ("ALIGN", (7, 1), (-1, -1), "CENTER"), # Procenta - center
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Střídavé pozadí řádků pro lepší čitelnost
                ("BACKGROUND", (0, 2), (-1, 2), colors.lightgrey),
            ]))
            story.append(t)
            story.append(Spacer(1, 20))

            # 💰 ZISK VS PENĚŽNÍ TOK - kompletní tabulka
            if calculate_cashflow:
                try:
                    selected_year = year if year else statements.last().year
                    cf = calculate_cashflow(user, selected_year)
                    if cf:
                        story.append(Paragraph(f"💰 Zisk vs Peněžní tok ({selected_year})", styles["Heading2"]))
                        
                        def format_variance(value):
                            if value > 0:
                                return f"+{value:,.0f}".replace(",", " ")
                            elif value < 0:
                                return f"{value:,.0f}".replace(",", " ")
                            else:
                                return "-"
                        
                        # Kompletní tabulka jako v aplikaci
                        cf_data = [
                            ["", "Zisk (účetní)", "Peněžní tok (hotovost)", "Rozdíl"],
                            ["Tržby za prodej zboží a služeb", f"{cf['revenue']:,.0f} Kč".replace(",", " "), 
                             f"{cf['revenue'] * 0.93:,.0f} Kč".replace(",", " "), 
                             format_variance((cf['revenue'] * 0.93) - cf['revenue'])],
                            ["Náklady na prodané zboží", f"{cf['cogs']:,.0f} Kč".replace(",", " "), 
                             f"{cf['cogs'] * 0.98:,.0f} Kč".replace(",", " "), 
                             format_variance((cf['cogs'] * 0.98) - cf['cogs'])],
                            ["Hrubá marže", f"{cf['gross_margin']:,.0f} Kč".replace(",", " "), 
                             f"{cf['gross_cash_profit']:,.0f} Kč".replace(",", " "), 
                             format_variance(cf['gross_cash_profit'] - cf['gross_margin'])],
                            ["Provozní náklady (bez odpisů)", f"{cf['overheads']:,.0f} Kč".replace(",", " "), 
                             f"{cf['overheads']:,.0f} Kč".replace(",", " "), "-"],
                            ["Provozní zisk", f"{cf['operating_cash_profit']:,.0f} Kč".replace(",", " "), 
                             f"{cf['operating_cash_flow']:,.0f} Kč".replace(",", " "), 
                             format_variance(cf['operating_cash_flow'] - cf['operating_cash_profit'])],
                            ["", "Ostatní peněžní výdaje", "", ""],
                            ["Nákladové úroky", f"-{cf['interest']:,.0f} Kč".replace(",", " "), 
                             f"-{cf['interest']:,.0f} Kč".replace(",", " "), "-"],
                            ["Daň z příjmů", f"{cf['taxation']:,.0f} Kč".replace(",", " "), 
                             f"{cf['taxation']:,.0f} Kč".replace(",", " "), "-"],
                            ["Mimořádné výnosy", f"+{cf['extraordinary']:,.0f} Kč".replace(",", " "), 
                             f"+{cf['extraordinary']:,.0f} Kč".replace(",", " "), "-"],
                            ["Podíly na zisku/Dividendy", f"{cf['dividends']:,.0f} Kč".replace(",", " "), 
                             f"{cf['dividends']:,.0f} Kč".replace(",", " "), "-"],
                            ["Odpisy dlouhodobého majetku", f"-{cf['depreciation']:,.0f} Kč".replace(",", " "), 
                             f"-{cf['fixed_assets']:,.0f} Kč".replace(",", " "), 
                             format_variance(-cf['fixed_assets'] + cf['depreciation'])],
                            ["", f"Nárůst ostatních aktiv: -{cf['other_assets']:,.0f} Kč".replace(",", " "), "", ""],
                            ["", f"Výběr základního kapitálu: -{cf['capital_withdrawn']:,.0f} Kč".replace(",", " "), "", ""],
                            ["CELKEM", f"{cf['retained_profit']:,.0f} Kč".replace(",", " "), 
                             f"{cf['net_cash_flow']:,.0f} Kč".replace(",", " "), 
                             format_variance(cf['net_cash_flow'] - cf['retained_profit'])]
                        ]
                        
                        tcf = Table(cf_data, colWidths=[120, 80, 80, 60])
                        tcf.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.darkgrey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("BACKGROUND", (0, 6), (-1, 6), colors.lightgrey),  # Ostatní peněžní výdaje
                            ("BACKGROUND", (0, -1), (-1, -1), colors.darkgrey),  # Celkem
                            ("TEXTCOLOR", (0, -1), (-1, -1), colors.whitesmoke),
                            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                            ("ALIGN", (0, 0), (0, -1), "LEFT"),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                            ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            # Zvýrazněné klíčové řádky
                            ("BACKGROUND", (0, 3), (-1, 3), colors.lightblue),  # Hrubá marže
                            ("BACKGROUND", (0, 5), (-1, 5), colors.lightblue),  # Provozní zisk
                        ]))
                        story.append(tcf)
                        story.append(Spacer(1, 20))
                except Exception as e:
                    story.append(Paragraph(f"⚠️ Nepodařilo se spočítat analýzu Zisk vs Peněžní tok: {e}", styles["Italic"]))

        else:
            story.append(Paragraph("❗ Žádné finanční údaje nebyly nalezeny.", styles["Normal"]))

        story.append(PageBreak())

    # 🧭 SCORE MOJÍ FIRMY (beze změn)
    if "survey" in selected_sections:
        from survey.views import QUESTIONS

        last_submission = SurveySubmission.objects.filter(user=user).order_by("-created_at").first()
        story.append(Paragraph("Score mojí firmy", styles["Heading1"]))
        story.append(Spacer(1, 8))

        if last_submission:
            responses = Response.objects.filter(submission=last_submission).order_by("id")
            for r in responses:
                description = None
                for q in QUESTIONS:
                    if q["question"] == r.question:
                        for score_range, label_text in q["labels"].items():
                            low, high = map(int, score_range.split("-"))
                            if low <= r.score <= high:
                                description = label_text
                                break
                        break
                if not description:
                    description = f"Hodnocení: {r.score}/10"

                story.append(Paragraph(f"<b>{r.question}</b>", styles["Normal"]))
                story.append(Paragraph(description, styles["WrapText"]))
                story.append(Spacer(1, 4))

            if last_submission.ai_response:
                story.append(Spacer(1, 10))
                story.append(Paragraph("AI shrnutí", styles["Heading2"]))
                for line in clean_text(last_submission.ai_response).split("\n"):
                    if line.strip():
                        story.append(Paragraph(line.strip(), styles["WrapText"]))
            else:
                story.append(Paragraph("AI analýza zatím nebyla provedena.", styles["Italic"]))
        else:
            story.append(Paragraph("Zatím nebyl vyplněn žádný dotazník.", styles["Normal"]))
        story.append(PageBreak())

    # 💬 BARIÉRY ŠKÁLOVÁNÍ FIRMY (beze změn)
    if "suropen" in selected_sections:
        last_batch = OpenAnswer.objects.filter(user=user).order_by("-created_at").first()
        story.append(Paragraph("Bariéry škálování firmy", styles["Heading1"]))
        story.append(Spacer(1, 8))

        if last_batch:
            batch_answers = OpenAnswer.objects.filter(user=user, batch_id=last_batch.batch_id).order_by("id")
            ai_summary = None
            for a in batch_answers:
                story.append(Paragraph(f"<b>{clean_text(a.question)}</b>", styles["Normal"]))
                try:
                    parsed = json.loads(a.answer)
                    if isinstance(parsed, dict):
                        for k, v in parsed.items():
                            story.append(Paragraph(f"- {clean_text(k)}: {clean_text(v)}", styles["WrapText"]))
                    elif isinstance(parsed, list):
                        for item in parsed:
                            story.append(Paragraph(f"- {clean_text(item)}", styles["WrapText"]))
                    else:
                        story.append(Paragraph(clean_text(parsed), styles["WrapText"]))
                except Exception:
                    story.append(Paragraph(clean_text(a.answer), styles["WrapText"]))
                story.append(Spacer(1, 3))
                if a.ai_response:
                    ai_summary = a.ai_response

            story.append(Spacer(1, 8))
            if ai_summary:
                story.append(Paragraph("AI shrnutí a doporučení", styles["Heading2"]))
                for line in clean_text(ai_summary).split("\n"):
                    if line.strip():
                        story.append(Paragraph(line.strip(), styles["WrapText"]))
            else:
                story.append(Paragraph("AI analýza zatím nebyla provedena.", styles["Italic"]))
        else:
            story.append(Paragraph("Žádná osobní analýza nebyla nalezena.", styles["Normal"]))

    # 📘 GENEROVÁNÍ PDF
    doc.build(story)
    buffer.seek(0)
    filename = f"Report_{timezone.localtime().strftime('%Y%m%d_%H%M')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

@login_required
def export_config_api(request):
    """Vraci data pro React export stranku."""
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    years = [s.year for s in statements]
    return JsonResponse({"years": years})
