import os
import io
import json
import base64
from io import BytesIO
from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

from ingest.models import FinancialStatement
from survey.models import SurveySubmission, Response
from suropen.models import OpenAnswer

# ✅ registrace fontu – jen jednou při načtení views.py
pdfmetrics.registerFont(
    TTFont("DejaVuSans", os.path.join(settings.BASE_DIR, "static/fonts/DejaVuSans.ttf"))
)


def export_form(request):
    """Jednoduchá stránka s tlačítkem pro export PDF."""
    return render(request, "exports/export_form.html")


@csrf_exempt
def upload_chart(request):
    """Příjem base64 PNG z frontendu a uložení do MEDIA_ROOT."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_data = data.get("image")
            chart_id = data.get("chart_id")
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        if not image_data or not chart_id:
            return JsonResponse({"status": "error", "message": "Missing data"}, status=400)

        if image_data.startswith("data:image/png;base64,"):
            image_data = image_data.replace("data:image/png;base64,", "")

        try:
            image_binary = base64.b64decode(image_data)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

        file_name = f"chart_{chart_id}.png"
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(image_binary)

        return JsonResponse({"status": "ok", "file": file_path})

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)


@login_required
def export_pdf(request):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    for style_name in styles.byName:
        styles[style_name].fontName = "DejaVuSans"

    # --- 1) GRAFY (původní generování)
    if os.path.exists(settings.MEDIA_ROOT):
        for fname in sorted(os.listdir(settings.MEDIA_ROOT)):
            if fname.startswith("chart_") and fname.endswith(".png"):
                file_path = os.path.join(settings.MEDIA_ROOT, fname)
                elements.append(Image(file_path, width=500, height=300))
                elements.append(Spacer(1, 12))

    # --- 2) TABULKA "Přehled dat"
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    if statements.exists():
        data = [["Rok", "Revenue", "COGS", "Gross Margin", "Overheads", "EBIT", "Net Profit"]]
        for s in statements:
            d = s.data or {}
            row = [
                s.year,
                d.get("Revenue", 0),
                d.get("COGS", 0),
                d.get("Revenue", 0) - d.get("COGS", 0),   # Gross Margin
                d.get("Overheads", 0),
                d.get("EBIT", 0),
                d.get("NetProfit", 0),
            ]
            data.append(row)
        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(Paragraph("📑 Přehled dat", styles["Heading2"]))
        elements.append(table)
        elements.append(Spacer(1, 24))

    # --- 3) POSLEDNÍ SURVEY
    last_submission = SurveySubmission.objects.filter(user=request.user).order_by("-created_at").first()
    if last_submission:
        elements.append(Paragraph("📝 Poslední survey odpovědi", styles["Heading2"]))
        responses = Response.objects.filter(submission=last_submission)
        data = [["Otázka", "Skóre"]]
        for r in responses:
            data.append([
                Paragraph(r.question, styles["Normal"]),
                Paragraph(str(r.score), styles["Normal"])
            ])
        survey_table = Table(data, colWidths=[350, 100])
        survey_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(survey_table)
        elements.append(Spacer(1, 24))

    # --- 4) VŠECHNY SUROPEN ODPOVĚDI
    open_answers = OpenAnswer.objects.filter(user=request.user).order_by("created_at")
    if open_answers.exists():
        elements.append(Paragraph("💡 Suropen – odpovědi", styles["Heading2"]))

        for oa in open_answers:
            elements.append(Paragraph(f"Sekce: {oa.section}", styles["Heading3"]))
            elements.append(Paragraph(f"Otázka: {oa.question}", styles["Normal"]))
            elements.append(Paragraph(f"Odpověď: {oa.answer}", styles["Normal"]))

            if oa.ai_response:
                elements.append(Paragraph("AI shrnutí:", styles["Italic"]))
                ai_clean = oa.ai_response.replace("###", "").replace("**", "")
                for line in ai_clean.split("\n"):
                    line = line.strip()
                    if line:
                        elements.append(Paragraph(f"• {line}", styles["Normal"]))

            elements.append(Spacer(1, 12))

    # --- build & return
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="report.pdf")
