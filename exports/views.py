import os
import io
import json
import base64
from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet


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
    """Generuje PDF s grafy uloženými v MEDIA_ROOT."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("📊 Financial Dashboard", styles["Title"]))
    elements.append(Spacer(1, 12))

    if os.path.exists(settings.MEDIA_ROOT):
        for fname in sorted(os.listdir(settings.MEDIA_ROOT)):
            if fname.startswith("chart_") and fname.endswith(".png"):
                chart_path = os.path.join(settings.MEDIA_ROOT, fname)
                elements.append(Image(chart_path, width=400, height=250))
                elements.append(Spacer(1, 24))

    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="financial_dashboard.pdf")
