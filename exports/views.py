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


@csrf_exempt
def upload_chart(request):
    """Uloží base64 obrázek (graf z dashboardu) do MEDIA_ROOT."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method."}, status=405)

    img_data = None

    # 🧩 1️⃣ Zkus JSON payload
    if request.content_type == "application/json":
        try:
            body = json.loads(request.body.decode("utf-8"))
            img_data = body.get("image")
        except Exception as e:
            return JsonResponse({"error": f"Invalid JSON: {str(e)}"}, status=400)

    # 🧩 2️⃣ Fallback – zkus běžné POST pole
    if not img_data:
        img_data = request.POST.get("image")

    if not img_data:
        return JsonResponse({"error": "No image data provided."}, status=400)

    try:
        format, imgstr = img_data.split(";base64,")
        ext = format.split("/")[-1]
        filename = f"chart_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        file_data = ContentFile(base64.b64decode(imgstr), name=filename)
        file_path = os.path.join(settings.MEDIA_ROOT, filename)
        with open(file_path, "wb") as f:
            f.write(file_data.read())

        return JsonResponse({"status": "ok", "filename": filename})
    except Exception as e:
        return JsonResponse({"error": f"Failed to save image: {str(e)}"}, status=500)


@login_required
def export_form(request):
    return render(request, "exports/export_form.html")


@login_required
def export_pdf(request):
    """Generuje profesionální PDF report."""
    user = request.user
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    selected_sections = request.POST.getlist("sections") or ["charts", "tables", "survey", "suropen"]

    # 🧱 Font a styly
    pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
    styles = getSampleStyleSheet()
    for s in styles.byName.values():
        s.fontName = "DejaVu"
    styles.add(ParagraphStyle(name="WrapText", fontName="DejaVu", leading=14, fontSize=10))

    # Pomocná funkce pro vyčištění textu (bez markdown znaků)
    def clean_text(text):
        if not text:
            return ""
        txt = re.sub(r"[\*\#\_]+", "", str(text))
        txt = txt.replace("•", "-")
        return txt.strip()

    story = []

    # 🏢 HLAVIČKA
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

        # Názvy grafů (v češtině, stejné jako v dashboardu)
        chart_titles = [
            "Váš příběh zisku",
            "Trend ziskovosti",
            "Růst tržeb vs. růst nákladů na prodané zboží",
            "Růst tržeb vs. růst provozních nákladů",
            "Meziroční přehled hlavních metrik"
        ]

        # 🔹 Vložíme grafy
        if "charts" in selected_sections:
            chart_dir = settings.MEDIA_ROOT
            charts = [f for f in os.listdir(chart_dir) if f.startswith("chart_") and f.endswith(".png")]
            if charts:
                for i, ch in enumerate(sorted(charts)):
                    img_path = os.path.join(chart_dir, ch)
                    title = chart_titles[i] if i < len(chart_titles) else f"Graf {i+1}"
                    story.append(Paragraph(title, styles["Heading2"]))
                    story.append(Image(img_path, width=460, height=210))
                    story.append(Spacer(1, 10))
            else:
                story.append(Paragraph("Žádné grafy nebyly nalezeny.", styles["Normal"]))
            story.append(Spacer(1, 15))

        # 🔹 Tabulka – české názvy sloupců
        if "tables" in selected_sections:
            statements = FinancialStatement.objects.filter(owner=user).order_by("year")
            if statements.exists():
                story.append(Paragraph("Přehled finančních ukazatelů", styles["Heading2"]))
                data = [
                    ["Rok", "Tržby", "Náklady na prodané zboží", "EBIT", "Čistý zisk", "Aktiva", "Vlastní kapitál"]
                ]
                for s in statements:
                    d = s.data or {}
                    data.append([
                        s.year,
                        f"{d.get('Revenue', 0):,.0f}".replace(",", " "),
                        f"{d.get('COGS', 0):,.0f}".replace(",", " "),
                        f"{d.get('EBIT', 0):,.0f}".replace(",", " "),
                        f"{d.get('NetProfit', 0):,.0f}".replace(",", " "),
                        f"{d.get('TotalAssets', 0):,.0f}".replace(",", " "),
                        f"{d.get('Equity', 0):,.0f}".replace(",", " ")
                    ])
                t = Table(data, hAlign="LEFT", colWidths=[50, 80, 100, 70, 70, 70, 80])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ]))
                story.append(t)
            else:
                story.append(Paragraph("Žádné finanční výsledky nebyly nalezeny.", styles["Normal"]))
        story.append(PageBreak())

    # 🧭 SCORE MOJÍ FIRMY
    if "survey" in selected_sections:
        from survey.views import QUESTIONS  # načteme mapu otázek s textovými popisy

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
                story.append(Spacer(1, 6))
                story.append(Paragraph("AI analýza zatím nebyla provedena.", styles["Italic"]))
        else:
            story.append(Paragraph("Zatím nebyl vyplněn žádný dotazník.", styles["Normal"]))
        story.append(PageBreak())

    # 💬 BARIÉRY ŠKÁLOVÁNÍ FIRMY
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
