import os
import base64
import json
import re
import textwrap
from io import BytesIO
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Avg

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
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
from coaching.models import UserCoachAssignment
from survey.views import QUESTIONS

# ✅ import výpočtu Cash Flow (nový modul)
try:
    from dashboard.cashflow import calculate_cashflow
except ImportError:
    calculate_cashflow = None


FONT_PATH = os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf")
try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))
    BASE_FONT = "DejaVuSans"
except Exception:
    BASE_FONT = "Helvetica"


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
    """Generate a stylised PDF export for the current user."""
    if request.method != "POST":
        return redirect("exports:export_form")

    user = request.user
    year_value = request.POST.get("year")
    try:
        selected_year = int(year_value) if year_value else None
    except (TypeError, ValueError):
        selected_year = None

    statements_qs = FinancialStatement.objects.filter(owner=user).order_by("year")
    if selected_year:
        statements_qs = statements_qs.filter(year=selected_year)
    statements = list(statements_qs)
    selected_sections = set(request.POST.getlist("sections") or [])
    include_charts = not selected_sections or "charts" in selected_sections
    include_tables = not selected_sections or "tables" in selected_sections
    include_survey = not selected_sections or "survey" in selected_sections
    include_suropen = not selected_sections or "suropen" in selected_sections

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=48,
        bottomMargin=48,
    )

    palette = {
        "primary": colors.HexColor("#041434"),
        "muted": colors.HexColor("#64748b"),
        "text": colors.HexColor("#1e293b"),
        "border": colors.HexColor("#d7e3ff"),
        "border_subtle": colors.HexColor("#e2e8f0"),
        "card": colors.HexColor("#f6f8ff"),
    }

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=BASE_FONT,
        fontSize=22,
        leading=26,
        textColor=palette["primary"],
        alignment=0,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["BodyText"],
        fontName=BASE_FONT,
        fontSize=12,
        leading=15,
        textColor=palette["muted"],
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName=BASE_FONT,
        fontSize=10.5,
        leading=14,
        textColor=palette["text"],
    )
    muted_style = ParagraphStyle(
        "ReportMuted",
        parent=styles["BodyText"],
        fontName=BASE_FONT,
        fontSize=9,
        leading=12,
        textColor=palette["muted"],
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName=BASE_FONT,
        fontSize=14,
        leading=18,
        textColor=palette["primary"],
        spaceAfter=8,
    )
    subsection_heading = ParagraphStyle(
        "SubSectionHeading",
        parent=styles["Heading3"],
        fontName=BASE_FONT,
        fontSize=12,
        leading=16,
        textColor=palette["primary"],
        spaceAfter=6,
    )
    table_head_style = ParagraphStyle(
        "TableHead",
        parent=body_style,
        fontName=BASE_FONT,
        fontSize=10,
        leading=13,
        textColor=palette["primary"],
    )
    table_head_small = ParagraphStyle(
        "TableHeadSmall",
        parent=body_style,
        fontName=BASE_FONT,
        fontSize=9.5,
        leading=12,
        textColor=palette["primary"],
    )

    def make_card(flowables, background=None, padding=14, width=None, keep_together=False):
        """Render a bordered 'card' container; optionally keep all content together."""
        card_width = width or doc.width
        if isinstance(flowables, (list, tuple)):
            cell_content = list(flowables)
        else:
            cell_content = [flowables]
        cell_value = KeepTogether(cell_content) if keep_together else cell_content
        return Table(
            [[cell_value]],
            colWidths=[card_width],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), background or palette["card"]),
                ("BOX", (0, 0), (-1, -1), 0.6, palette["border"]),
                ("INNERGRID", (0, 0), (-1, -1), 0, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ]),
        )

    story = []

    def load_chart_image(chart_id, title, card_width=None):
        chart_dir = os.path.join(settings.MEDIA_ROOT, "charts")
        filename = f"chart_{chart_id}.png"
        file_path = os.path.join(chart_dir, filename)
        if not os.path.exists(file_path):
            return None
        try:
            chart_img = Image(file_path)
            chart_img.hAlign = "CENTER"
            target_width = max((card_width or doc.width) - 24, 120)
            chart_img._restrictSize(target_width, target_width * 0.75)
            elements = [
                Paragraph(title, subsection_heading),
                Spacer(1, 8),
                chart_img,
            ]
            # ❗ necháme bez KeepTogether; řádek grafů už bude řídit zalomení
            return make_card(
                elements,
                background=colors.white,
                padding=12,
                width=card_width,
                keep_together=False,
            )
        except Exception:
            return None

    def format_ai_paragraph(text, fallback="AI shrnutí není k dispozici."):
        cleaned = (text or "").strip()
        if not cleaned:
            cleaned = fallback

        # vlož zero-width space po ~80 nezlomitelných znacích
        ZERO_WIDTH_SPACE = "\u200b"

        def _softbreak(s, n=80):
            pattern = r"(\S{" + str(n) + r"})"
            return re.sub(pattern, r"\1" + ZERO_WIDTH_SPACE, s)

        lines = []
        for raw in cleaned.splitlines():
            line = raw.strip()
            if not line:
                continue
            lines.append(Paragraph(_softbreak(line), body_style))
        return lines

    def resolve_survey_answer(question_text, score):
        for item in QUESTIONS:
            if item.get("question") == question_text:
                for score_range, meaning in item.get("labels", {}).items():
                    try:
                        low, high = map(int, score_range.split("-"))
                        if low <= score <= high:
                            return meaning
                    except Exception:
                        continue
        return f"Skore {score}/10"

    story.append(Paragraph("ScaleupBoard Export", title_style))
    story.append(Paragraph("Finanční snapshot", subtitle_style))
    story.append(Paragraph(timezone.localtime().strftime("%d.%m.%Y %H:%M"), muted_style))
    story.append(Spacer(1, 14))

    company = (
        CompanyProfile.objects.filter(user=user)
        .select_related("assigned_coach__user")
        .first()
    )
    info_lines = []
    if company:
        info_lines.append(Paragraph(f"Firma: {company.company_name or '-'}", body_style))
        info_lines.append(Paragraph(f"I\u010cO: {company.ico or '-'}", body_style))
        if company.contact_person:
            info_lines.append(Paragraph(f"Kontaktn\u00ed osoba: {company.contact_person}", body_style))
    else:
        info_lines.append(Paragraph(f"U\u017eivatel: {user.get_full_name() or user.username}", body_style))
    contact_email = company.email if (company and company.email) else user.email
    info_lines.append(Paragraph(f"E-mail: {contact_email or '-'}", body_style))
    info_lines.append(Paragraph(f"Vybran\u00fd rok: {selected_year or 'v\u0161echna dostupn\u00e1 obdob\u00ed'}", body_style))
    story.append(make_card(info_lines))
    story.append(Spacer(1, 12))

    assigned_coach = getattr(company, "assigned_coach", None) if company else None
    if not assigned_coach:
        assignment = (
            UserCoachAssignment.objects.filter(client=user)
            .select_related("coach__user")
            .order_by("-assigned_at")
            .first()
        )
        if assignment:
            assigned_coach = assignment.coach
    coach_lines = []
    if assigned_coach:
        coach_user = getattr(assigned_coach, "user", None)
        coach_name = (coach_user.get_full_name() or coach_user.username) if coach_user else None
        coach_lines.append(Paragraph(f"P\u0159i\u0159azen\u00fd kou\u010d: {coach_name or str(assigned_coach)}", body_style))
        if getattr(assigned_coach, "specialization", None):
            coach_lines.append(Paragraph(f"Specializace: {assigned_coach.specialization}", body_style))
        coach_email = getattr(assigned_coach, "email", None) or (coach_user.email if coach_user else None)
        coach_phone = getattr(assigned_coach, "phone", None)
        coach_city = getattr(assigned_coach, "city", None)
        if coach_email:
            coach_lines.append(Paragraph(f"E-mail: {coach_email}", body_style))
        if coach_phone:
            coach_lines.append(Paragraph(f"Telefon: {coach_phone}", body_style))
        if coach_city:
            coach_lines.append(Paragraph(f"Lokace: {coach_city}", body_style))
        if getattr(assigned_coach, "linkedin", None):
            coach_lines.append(Paragraph(f"LinkedIn: {assigned_coach.linkedin}", body_style))
        if getattr(assigned_coach, "website", None):
            coach_lines.append(Paragraph(f"Web: {assigned_coach.website}", body_style))
    else:
        coach_lines.append(Paragraph("Ke spole\u010dnosti zat\u00edm nen\u00ed p\u0159i\u0159azen \u017e\u00e1dn\u00fd kou\u010d.", body_style))

    story.append(Paragraph("V\u00e1\u0161 kou\u010d", section_heading))
    story.append(make_card(coach_lines))
    story.append(Spacer(1, 18))

    placeholder_rows = [
        ("Skóre firmy", "Doplní se po automatické analýze dotazníků."),
        ("Doporučení AI", "Zatím není dostupné – vyčkejte na další běh asistenta."),
        ("Nálada týmu", "Poslední měření zatím neproběhlo."),
        ("Úkoly do příště", "Domluvte s koučem během další konzultace."),
    ]
    story.append(Paragraph("Rychlý přehled", section_heading))
    story.append(Table(
        placeholder_rows,
        colWidths=[doc.width * 0.32, doc.width * 0.68],
        style=TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [palette["card"], colors.white]),
            ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
            ("TEXTCOLOR", (0, 0), (-1, -1), palette["text"]),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEABOVE", (0, 0), (-1, 0), 0.6, palette["border_subtle"]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.2, palette["border_subtle"]),
        ])
    ))
    story.append(Spacer(1, 18))

    def to_number(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace(" ", "").replace("Kč", "").replace("CZK", "").replace(",", ".")
            return float(cleaned)
        except (TypeError, ValueError):
            return None

    if statements and include_tables:
        story.append(Paragraph("Finanční tabulka", section_heading))
        table_header = ["Rok", "Tržby", "Náklady", "Hrubá marže", "EBIT", "Čistý zisk"]
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
                ("BACKGROUND", (0, 0), (-1, 0), palette["card"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), palette["primary"]),
                ("FONTNAME", (0, 0), (-1, 0), BASE_FONT),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.25, palette["border_subtle"]),
            ])
        ))
    elif not statements and include_tables:
        story.append(Paragraph("Pro zvolený rok nejsou dostupné finanční výkazy.", body_style))

    story.append(Spacer(1, 24))
    story.append(Paragraph("Poznámka: Všechna čísla jsou uvedena v českých korunách (Kč).", muted_style))

    chart_specs = [
        ("profit_story", "V\u00e1\u0161 p\u0159\u00edb\u011bh zisku"),
        ("profitability_trends", "Trend ziskovosti"),
        ("rev_cogs_growth", "R\u016fst tr\u017eeb vs. n\u00e1klad\u016f na zbo\u017e\u00ed"),
        ("rev_overheads_growth", "R\u016fst tr\u017eeb vs. provozn\u00edch n\u00e1klad\u016f"),
        ("all_metrics", "V\u00fdvoj kl\u00ed\u010dov\u00fdch metrik"),
        ("metrics_trend", "Finan\u010dn\u00ed trajektorie"),
    ]
    if include_charts:
        chart_columns = 2
        chart_gap = 16
        chart_col_width = (doc.width - chart_gap) / chart_columns
        chart_cards = []
        for chart_id, chart_title in chart_specs:
            card = load_chart_image(chart_id, chart_title, card_width=chart_col_width)
            if card:
                chart_cards.append(card)
        if chart_cards:
            story.append(PageBreak())
            story.append(Paragraph("Vizualizace", section_heading))
            chart_rows = []
            current_row = []
            for card in chart_cards:
                current_row.append(card)
                if len(current_row) == chart_columns:
                    chart_rows.append(current_row)
                    current_row = []
            if current_row:
                while len(current_row) < chart_columns:
                    current_row.append(Spacer(1, 1))
                chart_rows.append(current_row)

            # ❗ NEBALIT řádek do KeepTogether – umožní přesunout řádek na další stranu
            for row in chart_rows:
                row_table = Table(
                    [row],
                    colWidths=[chart_col_width] * chart_columns,
                    hAlign="CENTER",
                    style=TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]),
                )
                story.append(row_table)
                story.append(Spacer(1, 12))
            story.append(Spacer(1, 6))

    latest_submission = (
        SurveySubmission.objects.filter(user=user)
        .prefetch_related("responses")
        .order_by("-created_at")
        .first()
    )
    if include_survey and latest_submission:
        story.append(PageBreak())
        story.append(Paragraph("AI shrnutí dotazníku", section_heading))
        story.append(make_card(
            format_ai_paragraph(latest_submission.ai_response, "AI shrnutí není k dispozici."),
            keep_together=False,
        ))
        story.append(Spacer(1, 12))
        responses = list(latest_submission.responses.all())
        if responses:
            table_rows = [[
                Paragraph("Ot\u00e1zka", table_head_style),
                Paragraph("Odpov\u011b\u010f", table_head_style),
            ]]
            for resp in responses:
                answer_text = resolve_survey_answer(resp.question, resp.score)
                table_rows.append([
                    Paragraph(textwrap.shorten(resp.question, width=110, placeholder="..."), body_style),
                    Paragraph(answer_text, body_style),
                ])
            story.append(Table(
                table_rows,
                colWidths=[doc.width * 0.52, doc.width * 0.48],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), palette["card"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), palette["primary"]),
                    ("FONTNAME", (0, 0), (-1, 0), BASE_FONT),
                    ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.25, palette["border_subtle"]),
                ])
            ))
            story.append(Spacer(1, 12))

    latest_open_answer = (
        OpenAnswer.objects.filter(user=user)
        .order_by("-created_at")
        .first()
    )
    if include_suropen and latest_open_answer and latest_open_answer.ai_response:
        story.append(PageBreak())
        story.append(Paragraph("AI shrnutí otevřených odpovědí", section_heading))
        story.append(make_card(
            format_ai_paragraph(latest_open_answer.ai_response),
            keep_together=False,
        ))
        entries = list(
            OpenAnswer.objects.filter(user=user, batch_id=latest_open_answer.batch_id)
            .order_by("created_at")
        )
        if entries:
            qa_rows = [[
                Paragraph("Ot\u00e1zka", table_head_small),
                Paragraph("Odpov\u011b\u010f", table_head_small),
            ]]
            for entry in entries:
                qa_rows.append([
                    Paragraph(textwrap.shorten(entry.question or "-", width=100, placeholder="..."), body_style),
                    Paragraph(textwrap.shorten(entry.answer or "-", width=140, placeholder="..."), body_style),
                ])
            story.append(Spacer(1, 12))
            story.append(Table(
                qa_rows,
                colWidths=[doc.width * 0.45, doc.width * 0.55],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), palette["card"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), palette["primary"]),
                    ("FONTNAME", (0, 0), (-1, 0), BASE_FONT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.25, palette["border_subtle"]),
                ])
            ))

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
