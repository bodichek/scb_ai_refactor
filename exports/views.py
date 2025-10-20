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

    # 📑 Brand fonty a styly
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
    font_name = "DejaVu"
    try:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        else:
            font_name = "Helvetica"
    except Exception:
        font_name = "Helvetica"

    brand_primary = colors.HexColor("#0a58f5")
    brand_secondary = colors.HexColor("#041434")
    brand_accent = colors.HexColor("#6eb9ff")
    brand_light = colors.HexColor("#f5f7ff")
    brand_muted = colors.HexColor("#64748b")

    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name
        style.textColor = brand_secondary
    styles["Normal"].fontSize = 10
    styles["Normal"].leading = 14
    styles["Heading1"].fontName = font_name
    styles["Heading1"].fontSize = 18
    styles["Heading1"].leading = 22
    styles["Heading1"].textColor = brand_primary
    styles["Heading1"].spaceAfter = 8
    styles["Heading2"].fontName = font_name
    styles["Heading2"].fontSize = 13
    styles["Heading2"].leading = 18
    styles["Heading2"].textColor = brand_secondary
    styles["Heading2"].spaceAfter = 6
    styles["Italic"].fontName = font_name

    styles.add(ParagraphStyle(name="WrapText", fontName=font_name, leading=14, fontSize=10))
    styles.add(ParagraphStyle(name="Muted", fontName=font_name, fontSize=9, leading=13, textColor=brand_muted))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading1"], fontSize=16, leading=20, textColor=brand_primary, spaceBefore=6, spaceAfter=8))
    styles.add(ParagraphStyle(name="SectionSubheading", parent=styles["Heading2"], fontSize=12, leading=16, textColor=brand_secondary, spaceAfter=6))
    styles.add(ParagraphStyle(name="ReportSubtitleStyle", parent=styles["Heading2"], fontSize=11, leading=14, textColor=brand_muted, spaceAfter=4))
    styles.add(ParagraphStyle(name="ReportTitleStyle", parent=styles["Heading1"], fontSize=22, leading=28, textColor=brand_secondary, spaceAfter=4))

    def clean_text(text):
        if not text:
            return ""
        txt = re.sub(r"[\*\#\_]+", "", str(text))
        txt = txt.replace("•", "-")
        return txt.strip()

    story = []

    company = CompanyProfile.objects.filter(user=user).first()
    header_rows = []
    header_rows.append(Paragraph("SCB Fin assistant", styles["ReportSubtitleStyle"]))
    header_rows.append(Paragraph("Výroční finanční report", styles["ReportTitleStyle"]))
    header_rows.append(Paragraph(f"Datum exportu: {timezone.localtime().strftime('%d.%m.%Y %H:%M')}", styles["Muted"]))
    header_rows.append(Spacer(1, 6))
    if company:
        header_rows.append(Paragraph(f"Firma: {clean_text(company.company_name)}", styles["Normal"]))
        header_rows.append(Paragraph(f"IČO: {company.ico or '—'}", styles["Normal"]))
        header_rows.append(Paragraph(f"Kontaktní osoba: {clean_text(company.contact_person) or '—'}", styles["Normal"]))
    else:
        header_rows.append(Paragraph(f"Uživatel: {user.get_full_name() or user.username}", styles["Normal"]))

    header_table = Table(
        [[item] for item in header_rows],
        colWidths=[doc.width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), brand_light),
            ("BOX", (0, 0), (-1, -1), 0.9, brand_accent),
            ("INNERGRID", (0, 0), (-1, -1), 0, colors.transparent),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
            ("TOPPADDING", (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ]),
    )
    story.append(header_table)
    story.append(Spacer(1, 18))
    year_label = year if year else "všechny dostupné"
    story.append(Paragraph(f"Vybraný rok analýzy: <b>{year_label}</b>", styles["Muted"]))
    story.append(Spacer(1, 12))

    def add_card(target_story, items, background=colors.white, border=brand_accent, padding=16):
        rows = [[item] for item in items]
        card = Table(
            rows,
            colWidths=[doc.width],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.8, border),
                ("INNERGRID", (0, 0), (-1, -1), 0, colors.transparent),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ]),
        )
        target_story.append(card)

    def add_page_number(canvas, doc_instance):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(brand_muted)
        canvas.drawString(42, 28, timezone.localtime().strftime("%d.%m.%Y"))
        canvas.drawRightString(doc_instance.pagesize[0] - 42, 28, f"Strana {doc_instance.page}")
        canvas.restoreState()

    # 📊 GRAFY A TABULKY
    if "charts" in selected_sections or "tables" in selected_sections:
        story.append(Paragraph("Finanční přehled", styles["SectionHeading"]))
        story.append(Paragraph("Klíčové grafy a tabulková data zachycující vývoj firmy.", styles["Muted"]))
        story.append(Spacer(1, 12))

        chart_titles = [
            "Váš příběh zisku",
            "Trend ziskovosti",
            "Růst tržeb vs. růst nákladů na prodané zboží",
            "Růst tržeb vs. růst provozních nákladů",
            "Meziroční přehled hlavních metrik",
        ]

        if "charts" in selected_sections:
            chart_dir = os.path.join(settings.MEDIA_ROOT, "charts")
            if os.path.isdir(chart_dir):
                chart_files = sorted(f for f in os.listdir(chart_dir) if f.startswith("chart_") and f.endswith(".png"))
                if chart_files:
                    for idx, chart_name in enumerate(chart_files):
                        chart_path = os.path.join(chart_dir, chart_name)
                        title = chart_titles[idx] if idx < len(chart_titles) else f"Graf {idx + 1}"
                        chart_card = Table(
                            [
                                [Paragraph(title, styles["SectionSubheading"])],
                                [Spacer(1, 8)],
                                [Image(chart_path, width=doc.width, height=doc.width * 0.42)],
                            ],
                            colWidths=[doc.width],
                            style=TableStyle([
                                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                                ("BOX", (0, 0), (-1, -1), 0.8, brand_accent),
                                ("INNERGRID", (0, 0), (-1, -1), 0, colors.transparent),
                                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                                ("TOPPADDING", (0, 0), (-1, -1), 16),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                            ]),
                        )
                        story.append(chart_card)
                        story.append(Spacer(1, 14))
                else:
                    story.append(Paragraph("Grafy se zatím nepodařilo uložit. Na dashboardu klikni na „Připravit grafy pro export“ a spusť export PDF znovu.", styles["Muted"]))
                    story.append(Spacer(1, 12))
            else:
                story.append(Paragraph("Složka s grafy neexistuje. Ulož grafy v dashboardu a poté export opakuj.", styles["Muted"]))
                story.append(Spacer(1, 12))

        statements = FinancialStatement.objects.filter(owner=user).order_by("year")
        if "tables" in selected_sections:
            if statements.exists():
                rows = []
                for stmt in statements:
                    data = stmt.data or {}
                    revenue = data.get("Revenue", 0) or 0
                    cogs = data.get("COGS", 0) or 0
                    gross_margin = revenue - cogs
                    overheads = data.get("Overheads", 0) or 0
                    depreciation = data.get("Depreciation", 0) or 0
                    ebit = data.get("EBIT", gross_margin - overheads - depreciation)
                    net_profit = data.get("NetProfit", 0) or 0
                    gm_pct = (gross_margin / revenue * 100) if revenue else 0
                    op_pct = (ebit / revenue * 100) if revenue else 0
                    np_pct = (net_profit / revenue * 100) if revenue else 0
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

                for idx, row in enumerate(rows):
                    if idx == 0:
                        row["revenue_growth"] = None
                        row["cogs_growth"] = None
                        row["overheads_growth"] = None
                    else:
                        prev = rows[idx - 1]
                        def growth(cur, prev_value):
                            if prev_value not in (None, 0):
                                return (cur - prev_value) / abs(prev_value) * 100
                            return None
                        row["revenue_growth"] = growth(row["revenue"], prev["revenue"])
                        row["cogs_growth"] = growth(row["cogs"], prev["cogs"])
                        row["overheads_growth"] = growth(row["overheads"], prev["overheads"])

                data_table = [[
                    "Rok", "Tržby", "COGS", "Hrubá marže",
                    "Provozní náklady", "EBIT", "Čistý zisk",
                    "Hrubá marže %", "Provozní marže %", "Čistá marže %",
                    "Růst tržeb %", "Růst COGS %", "Růst nákladů %"
                ]]

                for row in rows:
                    data_table.append([
                        str(row["year"]),
                        f"{row['revenue']:,.0f}".replace(",", "\u00a0"),
                        f"{row['cogs']:,.0f}".replace(",", "\u00a0"),
                        f"{row['gross_margin']:,.0f}".replace(",", "\u00a0"),
                        f"{row['overheads']:,.0f}".replace(",", "\u00a0"),
                        f"{row['ebit']:,.0f}".replace(",", "\u00a0"),
                        f"{row['net_profit']:,.0f}".replace(",", "\u00a0"),
                        f"{row['gm_pct']:.1f}%", f"{row['op_pct']:.1f}%", f"{row['np_pct']:.1f}%",
                        f"{row['revenue_growth']:.1f}%" if row["revenue_growth"] is not None else "—",
                        f"{row['cogs_growth']:.1f}%" if row["cogs_growth"] is not None else "—",
                        f"{row['overheads_growth']:.1f}%" if row["overheads_growth"] is not None else "—",
                    ])

                metrics_table = Table(
                    data_table,
                    colWidths=[doc.width * 0.07, doc.width * 0.11, doc.width * 0.11, doc.width * 0.11,
                               doc.width * 0.11, doc.width * 0.10, doc.width * 0.10, doc.width * 0.07,
                               doc.width * 0.07, doc.width * 0.07, doc.width * 0.07, doc.width * 0.08, doc.width * 0.08],
                    repeatRows=1,
                )
                metrics_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), brand_primary),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), font_name),
                    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3ff")]),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (1, 1), (6, -1), "RIGHT"),
                    ("ALIGN", (7, 1), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0dcff")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#b7c7ff")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))

                metrics_card = Table(
                    [[metrics_table]],
                    colWidths=[doc.width],
                    style=TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.8, brand_accent),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]),
                )
                story.append(Paragraph("📑 Přehled dat", styles["SectionSubheading"]))
                story.append(metrics_card)
                story.append(Spacer(1, 18))

                if calculate_cashflow:
                    try:
                        selected_year = year if year else statements.last().year
                        cf = calculate_cashflow(user, selected_year)
                    except Exception:
                        cf = None
                    if cf:
                        story.append(Paragraph(f"💰 Zisk vs Peněžní tok ({selected_year})", styles["SectionSubheading"]))
                        cf_rows = [
                            ["", "Zisk (účetní)", "Peněžní tok (hotovost)", "Rozdíl"],
                            ["Tržby za prodej zboží a služeb", fmt_amount(cf["revenue"]), fmt_amount(cf["revenue"] * 0.93), format_variance((cf["revenue"] * 0.93) - cf["revenue"])],
                            ["Náklady na prodané zboží", fmt_amount(cf["cogs"]), fmt_amount(cf["cogs"] * 0.98), format_variance((cf["cogs"] * 0.98) - cf["cogs"])],
                            ["Hrubá marže", fmt_amount(cf["gross_margin"]), fmt_amount(cf["gross_cash_profit"]), format_variance(cf["gross_cash_profit"] - cf["gross_margin"])],
                            ["Provozní náklady (bez odpisů)", fmt_amount(cf["overheads"]), fmt_amount(cf["overheads"]), "—"],
                            ["Provozní zisk", fmt_amount(cf["operating_cash_profit"]), fmt_amount(cf["operating_cash_flow"]), format_variance(cf["operating_cash_flow"] - cf["operating_cash_profit"])],
                            ["", "Ostatní peněžní výdaje", "", ""],
                            ["Nákladové úroky", fmt_amount(-cf["interest"]), fmt_amount(-cf["interest"]), "—"],
                            ["Daň z příjmů", fmt_amount(cf["taxation"]), fmt_amount(cf["taxation"]), "—"],
                            ["Mimořádné výnosy", fmt_amount(cf["extraordinary"]), fmt_amount(cf["extraordinary"]), "—"],
                            ["Podíly na zisku/Dividendy", fmt_amount(-cf["dividends"]), fmt_amount(-cf["dividends"]), "—"],
                            ["Odpisy dlouhodobého majetku", fmt_amount(-cf["depreciation"]), fmt_amount(-cf["fixed_assets"]), format_variance(-cf["fixed_assets"] + cf["depreciation"])],
                            ["", Paragraph(f"Nárůst ostatních aktiv: {fmt_amount(-cf['other_assets'], '')}", styles["Muted"]), "", ""],
                            ["", Paragraph(f"Výběr základního kapitálu: {fmt_amount(-cf['capital_withdrawn'], '')}", styles["Muted"]), "", ""],
                            ["CELKEM", fmt_amount(cf["retained_profit"]), fmt_amount(cf["net_cash_flow"]), format_variance(cf["net_cash_flow"] - cf["retained_profit"])],
                        ]
                        cf_table = Table(cf_rows, colWidths=[doc.width * 0.32, doc.width * 0.24, doc.width * 0.24, doc.width * 0.2])
                        cf_table.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), brand_primary),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), font_name),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("BACKGROUND", (0, 6), (-1, 6), brand_light),
                            ("BACKGROUND", (0, -1), (-1, -1), brand_primary),
                            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                            ("ALIGN", (0, 0), (0, -1), "LEFT"),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0dcff")),
                            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#b7c7ff")),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]))
                        cf_card = Table([[cf_table]], colWidths=[doc.width], style=TableStyle([
                            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                            ("BOX", (0, 0), (-1, -1), 0.8, brand_accent),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                            ("TOPPADDING", (0, 0), (-1, -1), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ]))
                        story.append(cf_card)
                        story.append(Spacer(1, 18))
                    else:
                        story.append(Paragraph("Analýzu peněžního toku se nepodařilo spočítat pro zadaný rok.", styles["Muted"]))
                        story.append(Spacer(1, 12))
            else:
                story.append(Paragraph("Žádné finanční údaje nebyly nalezeny.", styles["Muted"]))
                story.append(Spacer(1, 12))

        if any(section in selected_sections for section in ("survey", "suropen")):
            story.append(PageBreak())

    if "survey" in selected_sections:
        from survey.views import QUESTIONS

        story.append(Paragraph("Score mojí firmy", styles["Heading1"]))
        story.append(Paragraph("Souhrn posledního vyplněného interního dotazníku.", styles["Muted"]))
        story.append(Spacer(1, 10))

        last_submission = SurveySubmission.objects.filter(user=user).order_by("-created_at").first()
        if last_submission:
            responses = Response.objects.filter(submission=last_submission).order_by("id")
            if responses.exists():
                table_rows = [[
                    Paragraph("<b>Oblast</b>", styles["Normal"]),
                    Paragraph("<b>Stav / hodnocení</b>", styles["Normal"]),
                ]]
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
                    table_rows.append([
                        Paragraph(clean_text(r.question), styles["WrapText"]),
                        Paragraph(clean_text(description), styles["WrapText"]),
                    ])

                survey_table = Table(table_rows, colWidths=[doc.width * 0.52, doc.width * 0.48], repeatRows=1)
                survey_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), brand_primary),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), font_name),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3ff")]),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0dcff")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                survey_card = Table([[survey_table]], colWidths=[doc.width], style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.8, brand_accent),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]))
                story.append(survey_card)
                story.append(Spacer(1, 14))

            if last_submission.ai_response:
                ai_lines = [line.strip() for line in clean_text(last_submission.ai_response).split("\n") if line.strip()]
                ai_flow = [Paragraph("AI shrnutí", styles["SectionSubheading"]), Spacer(1, 6)]
                for line in ai_lines:
                    ai_flow.append(Paragraph(line, styles["WrapText"]))
                add_card(story, ai_flow, background=colors.white, border=brand_accent, padding=16)
                story.append(Spacer(1, 12))
        else:
            story.append(Paragraph("Zatím nebyl vyplněn žádný dotazník.", styles["Muted"]))
            story.append(Spacer(1, 12))

        if "suropen" in selected_sections:
            story.append(PageBreak())

    if "suropen" in selected_sections:
        story.append(Paragraph("Bariéry škálování firmy", styles["Heading1"]))
        story.append(Paragraph("Odpovědi z otevřeného dotazníku a shrnutí AI kouče.", styles["Muted"]))
        story.append(Spacer(1, 10))

        last_batch = OpenAnswer.objects.filter(user=user).order_by("-created_at").first()
        if last_batch:
            answers = list(OpenAnswer.objects.filter(user=user, batch_id=last_batch.batch_id).order_by("id"))
            if answers:
                for block in SUROPEN_QUESTIONS:
                    block_answers = [a for a in answers if a.section == block["section"]]
                    if not block_answers:
                        continue
                    flow = [Paragraph(block["section"].title(), styles["SectionSubheading"]), Spacer(1, 6)]
                    for ans in block_answers:
                        flow.append(Paragraph(f"<b>{clean_text(ans.question)}</b>", styles["Normal"]))
                        flow.append(Paragraph(clean_text(ans.answer) or "—", styles["WrapText"]))
                        flow.append(Spacer(1, 6))
                    if isinstance(flow[-1], Spacer):
                        flow.pop()
                    add_card(story, flow, background=colors.white, border=brand_accent, padding=16)
                    story.append(Spacer(1, 12))

            ai_summary = next((a.ai_response for a in answers if a.ai_response), None)
            if ai_summary:
                ai_lines = [line.strip() for line in clean_text(ai_summary).split("\n") if line.strip()]
                ai_flow = [Paragraph("AI shrnutí a doporučení", styles["SectionSubheading"]), Spacer(1, 6)]
                for line in ai_lines:
                    ai_flow.append(Paragraph(line, styles["WrapText"]))
                add_card(story, ai_flow, background=colors.white, border=brand_accent, padding=16)
        else:
            story.append(Paragraph("Žádná osobní analýza zatím nebyla nalezena.", styles["Muted"]))

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    filename = f"SCB_report_{timezone.localtime().strftime('%Y%m%d_%H%M')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

@login_required
def export_config_api(request):
    """Vraci data pro React export stranku."""
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    years = [s.year for s in statements]
    return JsonResponse({"years": years})
