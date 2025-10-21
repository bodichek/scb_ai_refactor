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
from django.shortcuts import render, redirect
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
    """Generate a minimalist financial PDF snapshot for the current user."""
    if request.method != "POST":
        return redirect("exports:export_form")

    user = request.user

    year_value = request.POST.get("year")
    try:
        selected_year = int(year_value) if year_value else None
    except (TypeError, ValueError):
        selected_year = None

    statements_qs = (
        FinancialStatement.objects.filter(owner=user)
        .order_by("year")
    )
    if selected_year:
        statements_qs = statements_qs.filter(year=selected_year)
    statements = list(statements_qs)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=48,
        bottomMargin=48,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"].clone("ReportTitle")
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 20
    title_style.textColor = colors.HexColor("#041434")
    title_style.alignment = 0

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Heading2"],
        fontName="Helvetica",
        fontSize=12,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#041434"),
    )

    muted_style = ParagraphStyle(
        "ReportMuted",
        parent=body_style,
        textColor=colors.HexColor("#94a3b8"),
    )

    story = []

    story.append(Paragraph("ScaleupBoard Export", title_style))
    story.append(Paragraph("Minimalistický finanční report", subtitle_style))
    story.append(Paragraph(timezone.localtime().strftime("%d.%m.%Y %H:%M"), muted_style))
    story.append(Spacer(1, 12))

    company = CompanyProfile.objects.filter(user=user).select_related("assigned_coach").first()
    if company:
        company_rows = [
            Paragraph(f"Firma: {company.company_name}", body_style),
            Paragraph(f"IČO: {company.ico or '—'}", body_style),
        ]
        if company.contact_person:
            company_rows.append(Paragraph(f"Kontaktní osoba: {company.contact_person}", body_style))
    else:
        company_rows = [Paragraph(f"Uživatel: {user.get_full_name() or user.username}", body_style)]
    company_rows.append(Paragraph(f"Vybraný rok: {selected_year or 'všechna dostupná období'}", body_style))

    summary_table = Table(
        [[row] for row in company_rows],
        colWidths=[doc.width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5f5")),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]),
    )
    story.append(summary_table)
    story.append(Spacer(1, 16))

    placeholder_rows = [
        ("Celkové skóre", "— bude doplněno po automatické analýze"),
        ("Doporučení AI", "— čeká na další výstup asistenta"),
        ("Nálada týmu", "— poslední dotazník zatím nevyplněn"),
        ("Úkol do příště", "— definováno koučem během spolupráce"),
    ]
    story.append(Paragraph("Rychlý přehled", styles["Heading2"]))
    story.append(Table(
        placeholder_rows,
        colWidths=[doc.width * 0.32, doc.width * 0.68],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#eef2ff"), colors.white]),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#041434")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    ))
    story.append(Spacer(1, 16))

    def to_number(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace(' ', '').replace(' ', '').replace('Kč', '').replace('CZK', '').replace(',', '.')
            return float(cleaned)
        except (TypeError, ValueError):
            return None

    if statements:
        story.append(Paragraph("Finanční tabulka", styles["Heading2"]))
        table_header = [
            "Rok",
            "Tržby",
            "Náklady",
            "Hrubá marže",
            "EBIT",
            "Čistý zisk",
        ]
        table_data = [table_header]
        for stmt in statements:
            data = stmt.data or {}
            revenue = to_number(data.get("Revenue"))
            cogs = to_number(data.get("COGS"))
            gross_margin = revenue - cogs if revenue is not None and cogs is not None else to_number(data.get("GrossMargin"))
            ebit = to_number(data.get("EBIT"))
            net_profit = to_number(data.get("NetProfit"))
            table_data.append([
                stmt.year,
                f"{revenue:,.0f}" if revenue is not None else "—",
                f"{cogs:,.0f}" if cogs is not None else "—",
                f"{gross_margin:,.0f}" if gross_margin is not None else "—",
                f"{ebit:,.0f}" if ebit is not None else "—",
                f"{net_profit:,.0f}" if net_profit is not None else "—",
            ])

        story.append(Table(
            table_data,
            colWidths=[doc.width * 0.12, doc.width * 0.18, doc.width * 0.18, doc.width * 0.18, doc.width * 0.17, doc.width * 0.17],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#e2e8f0")),
            ])
        ))
    else:
        story.append(Paragraph("Pro zvolený rok nejsou dostupné finanční výkazy.", body_style))

    story.append(Spacer(1, 24))
    story.append(Paragraph("Poznámka: Všechna čísla jsou uvedena v českých korunách (Kč).", muted_style))

    doc.build(story)
    buffer.seek(0)
    filename = f"scb_export_{timezone.localtime().strftime('%Y%m%d_%H%M')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

@login_required
def export_config_api(request):
    """Vraci data pro React export stranku."""
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    years = [s.year for s in statements]
    return JsonResponse({"years": years})
