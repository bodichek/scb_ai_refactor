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
    HRFlowable,
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
        wordWrap="LTR",
        splitLongWords=True,
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

    def clean_text(value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def extract_recommendation_points(text, max_points=5):
        if not text:
            return []

        try:
            parsed = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None

        points = []
        seen = set()
        preferred_keys = [
            "action_plan",
            "actions",
            "recommendations",
            "next_steps",
            "steps",
            "key_actions",
            "actionItems",
        ]

        def add_point(value):
            if len(points) >= max_points:
                return
            cleaned_value = clean_text(value)
            if not cleaned_value:
                return
            normalized = re.sub(r"\s+", " ", cleaned_value)
            lowered = normalized.lower()
            if lowered in seen:
                return
            seen.add(lowered)
            points.append(normalized)

        def collect_from_json(value):
            if len(points) >= max_points:
                return
            if isinstance(value, str):
                add_point(value)
            elif isinstance(value, (int, float)):
                add_point(value)
            elif isinstance(value, list):
                for item in value:
                    collect_from_json(item)
                    if len(points) >= max_points:
                        break
            elif isinstance(value, dict):
                for key in preferred_keys:
                    if key in value:
                        collect_from_json(value[key])
                if len(points) >= max_points:
                    return
                for key, val in value.items():
                    if key not in preferred_keys:
                        collect_from_json(val)

        if parsed is not None:
            collect_from_json(parsed)
        else:
            for raw_line in str(text).splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                line = re.sub(r"^[-*\u2022]+\s*", "", line)
                line = re.sub(r"^\d+[\.\)]\s*", "", line)
                line = line.replace("**", "")
                if not line:
                    continue
                add_point(line)
                if len(points) >= max_points:
                    break

        if not points and text:
            add_point(text)
        return points[:max_points]

    def make_card(flowables, background=None, padding=14, width=None, keep_together=False):
        """Render a bordered 'card' container; optionally keep all content together.

        DŮLEŽITÉ: nepoužívej pro dlouhé texty. Table se dělí jen mezi řádky.
        """
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

    def load_chart_image(chart_id, title, max_width=None):
        chart_dir = os.path.join(settings.MEDIA_ROOT, "charts")
        filename = f"chart_{chart_id}.png"
        file_path = os.path.join(chart_dir, filename)
        if not os.path.exists(file_path):
            return None
        try:
            chart_img = Image(file_path)
            chart_img.hAlign = "CENTER"
            target_width = max((max_width or doc.width) - 24, 120)
            chart_img._restrictSize(target_width, target_width * 0.75)
            return [
                Paragraph(title, subsection_heading),
                Spacer(1, 8),
                chart_img,
                Spacer(1, 18),
            ]
        except Exception:
            return None

    def format_ai_paragraph(text, fallback="AI shrnutí není k dispozici."):
        cleaned = clean_text(text)
        if not cleaned:
            cleaned = fallback

        ZERO_WIDTH_SPACE = "\u200b"

        def _softbreak(s, n=80):
            pattern = r"(\S{" + str(n) + r"})"
            return re.sub(pattern, r"\1" + ZERO_WIDTH_SPACE, s)

        def _flatten_json(value):
            lines = []
            if isinstance(value, str):
                lines.extend([frag.strip() for frag in value.splitlines() if frag.strip()])
            elif isinstance(value, (int, float, bool)):
                lines.append(str(value))
            elif isinstance(value, list):
                for item in value:
                    lines.extend(_flatten_json(item))
            elif isinstance(value, dict):
                for key, val in value.items():
                    nested = _flatten_json(val)
                    if not nested:
                        continue
                    if len(nested) == 1:
                        lines.append(f"{key}: {nested[0]}")
                    else:
                        lines.append(f"{key}:")
                        lines.extend(nested)
            return lines

        parsed_lines = None
        try:
            parsed = json.loads(cleaned)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        else:
            parsed_lines = _flatten_json(parsed)

        def _normalize_line(line):
            cleaned_line = re.sub(r"^\s*#{1,6}\s*", "", line)
            cleaned_line = re.sub(r"^\s*[-*+]+\s*", "", cleaned_line)
            cleaned_line = re.sub(r"^\s*\d+[\.\)]\s*", "", cleaned_line)
            cleaned_line = cleaned_line.replace("**", "").replace("__", "")
            cleaned_line = re.sub(r"\s+", " ", cleaned_line).strip()
            return cleaned_line

        source_lines = parsed_lines if parsed_lines else [
            line.strip() for line in cleaned.splitlines() if line.strip()
        ]
        normalized_lines = [_normalize_line(line) for line in source_lines]
        normalized_lines = [line for line in normalized_lines if line]
        if not normalized_lines:
            normalized_lines = [fallback]

        return [Paragraph(_softbreak(line), body_style) for line in normalized_lines]

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

    latest_submission = (
        SurveySubmission.objects.filter(user=user)
        .prefetch_related("responses")
        .order_by("-created_at")
        .first()
    )
    latest_survey_responses = list(latest_submission.responses.all()) if latest_submission else []
    score_values = [resp.score for resp in latest_survey_responses if resp.score is not None]
    company_score = round(sum(score_values) / len(score_values), 1) if score_values else None

    mood_label = "Bez dat"
    mood_description = "Vypln dotaznik, aby slo sledovat naladu tymu."
    if company_score is not None:
        if company_score >= 8:
            mood_label = "Pozitivni energie"
            mood_description = "Odpovedi naznacuji vybornou motivaci."
        elif company_score >= 6:
            mood_label = "Stabilni nalada"
            mood_description = "Vyvoj je vyrovnany, hledejte dalsi rust."
        else:
            mood_label = "Potrebuje podporu"
            mood_description = "Tym hlasi napeti, zamerte se na blokatory."
    latest_open_answer = (
        OpenAnswer.objects.filter(user=user)
        .order_by("-created_at")
        .first()
    )
    open_answer_summary = clean_text(getattr(latest_open_answer, "ai_response", "")) if latest_open_answer else ""
    coach_summary = clean_text(getattr(latest_submission, "ai_response", "")) if latest_submission else ""
    coach_recommendation_text = open_answer_summary or coach_summary
    recommendation_points = (
        extract_recommendation_points(coach_recommendation_text)
        if coach_recommendation_text
        else []
    )

    def summarize_block(value, default, width=None):
        cleaned_value = clean_text(value)
        if not cleaned_value:
            return default
        flattened = cleaned_value.replace("\n", " ")
        if width:
            return textwrap.shorten(flattened, width=width, placeholder="...")
        return flattened

    score_summary_text = (
        f"{company_score:.1f}/10 - prumer posledniho dotazniku"
        if company_score is not None
        else "Skore zatim neni dostupne. Vypln posledni dotaznik."
    )
    mood_summary_text = (
        summarize_block(f"{mood_label}: {mood_description}", "Nalada tymu zatim nelze urcit bez dat.", width=200)
        if company_score is not None
        else "Nalada tymu zatim nelze urcit bez dat."
    )
    raw_tasks_summary = (
        "; ".join(recommendation_points[:3])
        if recommendation_points
        else "Jakmile AI pripravi konkretni ukoly, zobrazime je zde."
    )
    tasks_summary_text = summarize_block(
        raw_tasks_summary,
        "Jakmile AI pripravi konkretni ukoly, zobrazime je zde.",
        width=200,
    )

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
    story.append(make_card(info_lines))  # plná šířka (už ne 200)
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
    story.append(make_card(coach_lines))  # plná šířka (už ne 200)
    story.append(Spacer(1, 18))

    summary_rows = [
        ("Skóre firmy", score_summary_text),
        ("Nálada týmu", mood_summary_text),
        ("Úkoly do příště", tasks_summary_text),
    ]
    summary_table = [
        [
            Paragraph(f"<b>{label}</b>", body_style),
            Paragraph(text, body_style),
        ]
        for label, text in summary_rows
    ]
    story.append(Paragraph("Rychlý přehled", section_heading))
    story.append(Table(
        summary_table,
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
    story.append(Spacer(1, 10))
    story.append(Paragraph("Doporučení AI", subsection_heading))
    ai_paragraphs = format_ai_paragraph(
        coach_recommendation_text,
        "AI doporuceni zatim neni k dispozici."
    )
    for para in ai_paragraphs:
        story.append(para)
        story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=0.5, color=palette["border_subtle"]))
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
        chart_blocks = []
        for chart_id, chart_title in chart_specs:
            block = load_chart_image(chart_id, chart_title)
            if block:
                chart_blocks.append(block)
        if chart_blocks:
            story.append(PageBreak())
            story.append(Paragraph("Vizualizace", section_heading))
            for block in chart_blocks:
                story.extend(block)

    if include_survey and latest_submission:
        story.append(PageBreak())
        story.append(Paragraph("AI shrnutí dotazníku", section_heading))
        survey_paragraphs = format_ai_paragraph(
            latest_submission.ai_response,
            "AI shrnutí není k dispozici."
        )
        for para in survey_paragraphs:
            story.append(para)
            story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=0.5, color=palette["border_subtle"]))
        story.append(Spacer(1, 12))
        responses = latest_survey_responses
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

    if include_suropen and latest_open_answer and latest_open_answer.ai_response:
        story.append(PageBreak())
        story.append(Paragraph("AI shrnutí otevřených odpovědí", section_heading))
        open_paragraphs = format_ai_paragraph(latest_open_answer.ai_response)
        for para in open_paragraphs:
            story.append(para)
            story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=0.5, color=palette["border_subtle"]))
        story.append(Spacer(1, 12))
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
