import io
import os
import base64
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from survey.models import SurveySubmission
from suropen.models import OpenAnswer

# složka pro uložené grafy
UPLOAD_DIR = "media/charts"


@login_required
def export_form(request):
    """
    Zobrazení formuláře s checkboxy.
    """
    return render(request, "exports/export_form.html")


@login_required
def export_pdf(request):
    """
    Sestavení PDF podle vybraných checkboxů.
    """
    buffer = io.BytesIO()

    # Registrace fontu pro češtinu
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "HeiseiMin-W3"
    heading = styles["Heading2"]
    heading.fontName = "HeiseiMin-W3"
    title = styles["Title"]
    title.fontName = "HeiseiMin-W3"

    elements = []

    # Hlavička s údaji o uživateli
    elements.append(Paragraph(f"Export pro: {request.user.username} ({request.user.email})", title))
    elements.append(Spacer(1, 20))

    # Co bylo zaškrtnuto
    selected = request.POST.getlist("sections")

    # 📊 Grafy
    if "charts" in selected:
        elements.append(Paragraph("📊 Grafy", heading))
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Pro jednoduchost vezmeme 1 uložený graf s ID 'myChart'
        chart_file = f"{UPLOAD_DIR}/{request.user.id}_myChart.png"
        if os.path.exists(chart_file):
            elements.append(Image(chart_file, width=400, height=250))
        else:
            elements.append(Paragraph("Žádný graf zatím nebyl uložen.", normal))
        elements.append(Spacer(1, 10))

    # 📑 Tabulky
    if "tables" in selected:
        elements.append(Paragraph("📑 Srovnávací tabulky", heading))
        data = [
            ["Metrika", "2023", "2024"],
            ["Revenue", "1 200 000", "1 450 000"],
            ["EBIT", "150 000", "200 000"],
        ]
        t = Table(data, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

    # 📝 Dotazník
    if "survey" in selected:
        elements.append(Paragraph("📝 Dotazník", heading))
        last_survey = SurveySubmission.objects.filter(user=request.user).order_by("-created_at").first()
        if last_survey:
            for r in last_survey.responses.all():
                elements.append(Paragraph(f"{r.question}: {r.score}/10", normal))
        else:
            elements.append(Paragraph("Žádný dotazník zatím nebyl vyplněn.", normal))
        elements.append(Spacer(1, 10))

    # 🔎 Osobní analýza
    if "suropen" in selected:
        elements.append(Paragraph("🔎 Osobní analýza", heading))
        last_batch = OpenAnswer.objects.filter(user=request.user).order_by("-created_at").first()
        if last_batch:
            elements.append(Paragraph("Odpovědi:", normal))
            for oa in OpenAnswer.objects.filter(batch_id=last_batch.batch_id):
                elements.append(Paragraph(f"[{oa.section}] {oa.question} → {oa.answer}", normal))
            if last_batch.ai_response:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("🧠 Shrnutí AI:", heading))
                elements.append(Paragraph(last_batch.ai_response, normal))
        else:
            elements.append(Paragraph("Žádná osobní analýza zatím není dostupná.", normal))
        elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="export.pdf")


@csrf_exempt
@login_required
def upload_chart(request):
    """
    Uloží graf z frontendu (Chart.js → base64 PNG).
    """
    if request.method == "POST":
        data = json.loads(request.body)
        image_data = data.get("image", "")
        chart_id = data.get("chart_id", "myChart")

        if image_data.startswith("data:image/png;base64,"):
            image_data = image_data.replace("data:image/png;base64,", "")
        img_bytes = base64.b64decode(image_data)

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = f"{UPLOAD_DIR}/{request.user.id}_{chart_id}.png"
        with open(filename, "wb") as f:
            f.write(img_bytes)

        return JsonResponse({"status": "ok", "file": filename})

    return JsonResponse({"status": "error"}, status=400)
