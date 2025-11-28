import os
import io
import json
import base64
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import JsonResponse, FileResponse, HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

from accounts.models import CompanyProfile, CoachClientNotes
from ingest.models import Document, FinancialStatement
from survey.models import SurveySubmission
from suropen.models import OpenAnswer
from coaching.models import UserCoachAssignment
from finance.utils import (
    compute_overheads,
    compute_profitability,
    first_number,
    growth,
    to_number,
)

from .cashflow import calculate_cashflow


def _clean_text(text):
    if text is None:
        return ""
    if isinstance(text, str):
        return text.strip()
    return str(text).strip()


def _compute_overheads(data: dict) -> float:
    """Prefer sums of components; fall back to stored overhead totals."""
    return compute_overheads(data)


def _to_number(value):
    return to_number(value)


def _get_metric(data: dict, keys, default=None):
    val = first_number(data, keys)
    if val is None:
        return default
    return val


def _get_cogs_value(data: dict) -> float:
    """
    Vrátí COGS:

    - U legacy dat (TitleCase "COGS") očistí COGS o služby, protože byly součástí COGS.
    - U nového schématu (snake_case `cogs`) služby už součástí nejsou → neodečítáme.

    Tím zabráníme situaci, kdy se služby odečtou dvakrát a COGS spadne na 0.
    """
    services = _get_metric(data, ("services", "Services"))

    # Legacy: uložené "COGS" (TitleCase) – historicky obsahovalo i služby
    legacy_cogs = _get_metric(data, ("COGS",), None)
    if legacy_cogs is not None:
        if services is not None and services > 0 and legacy_cogs > 0:
            return max(legacy_cogs - services, 0.0)
        return legacy_cogs

    # Nové schéma: snake_case `cogs` je už BEZ služeb
    return _get_metric(data, ("cogs",), 0.0)


def _extract_recommendation_points(text, max_points=5):
    if not text:
        return []

    try:
        parsed = json.loads(text) if isinstance(text, str) else None
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
        cleaned = str(value).strip()
        if not cleaned:
            return
        cleaned = re.sub(r"\s+", " ", cleaned)
        lowered = cleaned.lower()
        if lowered in seen:
            return
        seen.add(lowered)
        points.append(cleaned)

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
            if not line or line.startswith('#'):
                continue
            line = re.sub(r"^[-*•]+\s*", "", line)
            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            line = line.replace('**', '')
            if not line:
                continue
            add_point(line)
            if len(points) >= max_points:
                break

    if not points:
        add_point(text)
    return points[:max_points]


def _build_cashflow_table(cf):
    if not cf:
        return []

    def entry(label, key, highlight=False):
        return {
            "label": label,
            "value": cf.get(key),
            "highlight": highlight,
        }

    return [
        {
            "title": "Provozní činnost",
            "rows": [
                entry("Čistý zisk", "net_profit"),
                entry("Odpisy", "depreciation"),
                entry("Změna pracovního kapitálu", "working_capital_change"),
                entry("Zaplatili jsme na úrocích", "interest_paid"),
                entry("Daň z příjmů", "income_tax_paid"),
                entry("Provozní cash flow", "operating_cf", highlight=True),
            ],
        },
        {
            "title": "Investiční činnost",
            "rows": [
                entry("Prodej majetku", "asset_sales"),
                entry("Investice do majetku (CapEx)", "capex"),
                entry("Investiční cash flow", "investing_cf", highlight=True),
            ],
        },
        {
            "title": "Finanční činnost",
            "rows": [
                entry("Přijaté úvěry", "loans_received"),
                entry("Splacené úvěry", "loans_repaid"),
                entry("Vyplacené dividendy", "dividends_paid"),
                entry("Finanční cash flow", "financing_cf", highlight=True),
            ],
        },
    ]


def _get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def build_dashboard_context(target_user):
    statements = FinancialStatement.objects.filter(owner=target_user).order_by("year")

    rows = []
    for s in statements:
        d = s.data or {}

        # Base metrics with snake_case/TitleCase fallback (prefer snake_case)
        revenue = _get_metric(d, ("revenue", "Revenue"), 0.0)
        cogs = _get_cogs_value(d)
        gross_margin = _get_metric(d, ("gross_margin", "GrossMargin"))
        if gross_margin is None:
            gross_margin = revenue - cogs

        depreciation = _get_metric(d, ("depreciation", "Depreciation"), 0.0)
        overheads = _compute_overheads(d)

        ebit = _get_metric(d, ("ebit", "EBIT"))
        if ebit is None:
            ebit = gross_margin - overheads

        net_profit = _get_metric(d, ("net_profit", "NetProfit"))
        if net_profit is None:
            net_profit = revenue - cogs - overheads

        profitability = compute_profitability(revenue, gross_margin, ebit, net_profit)

        rows.append({
            "year": s.year,
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "overheads": overheads,
            "depreciation": depreciation,
            "ebit": ebit,
            "net_profit": net_profit,
            "profitability": profitability,
            "growth": {},  # filled later
        })

    rows = sorted(rows, key=lambda r: r["year"])
    years = [r["year"] for r in rows]

    # Year-over-year growth using shared helper
    for i, r in enumerate(rows):
        if i == 0:
            r["growth"] = {"revenue": None, "cogs": None, "overheads": None}
        else:
            prev = rows[i - 1]
            r["growth"] = {
                "revenue": growth(r["revenue"], prev["revenue"]),
                "cogs": growth(r["cogs"], prev["cogs"]),
                "overheads": growth(r["overheads"], prev["overheads"]),
            }

    # 📈 Insights from survey responses
    survey_history = []
    latest_submission = None
    submissions_qs = SurveySubmission.objects.filter(user=target_user).order_by("created_at")
    for submission in submissions_qs:
        avg_score = None
        if hasattr(submission, "responses"):
            avg_score = submission.responses.aggregate(avg=Avg("score"))["avg"]
        if avg_score is not None:
            survey_history.append({
                "ts": submission.created_at,
                "value": round(avg_score, 1),
            })
        latest_submission = submission

    company_score = survey_history[-1]["value"] if survey_history else None
    score_trend = None
    if len(survey_history) >= 2:
        score_trend = round(survey_history[-1]["value"] - survey_history[-2]["value"], 1)

    mood_label = "Bez dat"
    mood_tone = "neutral"
    mood_description = "Vyplň firemní dotazník a zobrazíme náladu ve firmě."
    if company_score is not None:
        if company_score >= 8:
            mood_label = "Pozitivní energie"
            mood_tone = "positive"
            mood_description = "Odpovědi naznačují silnou motivaci a vysokou spokojenost týmu. Pokračujte v nastaveném tempu."
        elif company_score >= 6:
            mood_label = "Stabilní nálada"
            mood_tone = "neutral"
            mood_description = "Vývoj je vyrovnaný. Zaměřte se na konkrétní oblasti, které mohou přinést další růst."
        else:
            mood_label = "Potřebuje podporu"
            mood_tone = "negative"
            mood_description = "Tým hlásí napětí nebo únavu. Zvažte prioritizaci největších blokátorů a podporu leadershipu."

    # 🧠 AI doporučení
    coach_summary = _clean_text(latest_submission.ai_response) if (latest_submission and latest_submission.ai_response) else None
    open_answer_summary = None
    for answer in OpenAnswer.objects.filter(user=target_user).order_by("-created_at"):
        if answer.ai_response:
            open_answer_summary = _clean_text(answer.ai_response)
            break
    coach_recommendation = open_answer_summary or coach_summary
    recommendation_points = _extract_recommendation_points(coach_recommendation) if coach_recommendation else []

    profile = (
        CompanyProfile.objects.filter(user=target_user)
        .select_related("assigned_coach__user")
        .first()
    )
    assigned_coach = getattr(profile, "assigned_coach", None)
    if not assigned_coach:
        assignment = (
            UserCoachAssignment.objects.filter(client=target_user)
            .select_related("coach__user")
            .order_by("-assigned_at")
            .first()
        )
        if assignment:
            assigned_coach = assignment.coach
    coach_note_entry = None
    if profile:
        coach_note_entry = (
            CoachClientNotes.objects.filter(client=profile)
            .order_by("-updated_at")
            .first()
        )
    coach_note_text = _clean_text(coach_note_entry.notes) if coach_note_entry and coach_note_entry.notes else None

    document_status_map = {}
    doc_type_map = {
        "rozvaha": "rozvaha",
        "balance": "rozvaha",
        "vysledovka": "vysledovka",
        "income": "vysledovka",
    }
    document_qs = (
        Document.objects.filter(owner=target_user, doc_type__in=list(doc_type_map.keys()))
        .values("year", "doc_type", "analyzed")
    )
    for item in document_qs:
        year = item.get("year")
        doc_type = (item.get("doc_type") or "").lower()
        mapped_type = doc_type_map.get(doc_type)
        if year is None or mapped_type is None:
            continue
        try:
            year_int = int(year)
        except (TypeError, ValueError):
            continue
        entry = document_status_map.setdefault(
            year_int,
            {"year": year_int, "has_rozvaha": False, "has_vysledovka": False, "rozvaha_analyzed": False, "vysledovka_analyzed": False},
        )
        if mapped_type == "rozvaha":
            entry["has_rozvaha"] = True
            entry["rozvaha_analyzed"] = entry["rozvaha_analyzed"] or bool(item.get("analyzed"))
        elif mapped_type == "vysledovka":
            entry["has_vysledovka"] = True
            entry["vysledovka_analyzed"] = entry["vysledovka_analyzed"] or bool(item.get("analyzed"))

    statement_years = {
        int(s.year)
        for s in statements
        if getattr(s, "year", None) is not None
    }
    upload_years = sorted(
        set(document_status_map.keys()).union(statement_years),
        reverse=True,
    )
    document_upload_status = []
    for year in upload_years:
        entry = document_status_map.get(year, {})
        document_upload_status.append({
            "year": year,
            "has_rozvaha": entry.get("has_rozvaha", False),
            "has_vysledovka": entry.get("has_vysledovka", False),
            "rozvaha_analyzed": entry.get("rozvaha_analyzed", False),
            "vysledovka_analyzed": entry.get("vysledovka_analyzed", False),
        })

    chart_series = {
        "labels": years,
        "revenue": [r["revenue"] for r in rows],
        "net_profit": [r["net_profit"] for r in rows],
        "ebit": [r["ebit"] for r in rows],
    }

    # 💰 Výpočet cash flow pro poslední rok
    cf = None
    selected_year = years[-1] if years else None
    cashflow_table = []
    if selected_year:
        try:
            cf = calculate_cashflow(target_user, selected_year)
        except Exception as exc:
            print(f"⚠️ Chyba výpočtu cashflow: {exc}")
        else:
            cashflow_table = _build_cashflow_table(cf)

    return {
        "rows": json.dumps(rows),
        "years": json.dumps(years),
        "table_rows": rows,
        "cashflow": cf,
        "cashflow_table": cashflow_table,
        "selected_year": selected_year,
        "company_score": company_score,
        "score_trend": score_trend,
        "score_history": json.dumps([
            {"label": (item["ts"].strftime("%d.%m.%Y") if item["ts"] else str(idx)), "value": item["value"]}  # noqa: E501
            for idx, item in enumerate(survey_history)
        ]),
        "mood_label": mood_label,
        "mood_tone": mood_tone,
        "mood_description": mood_description,
        "coach_recommendation": coach_recommendation,
        "recommendation_points": recommendation_points,
        "assigned_coach": assigned_coach,
        "coach_note": coach_note_text,
        "chart_series": json.dumps(chart_series),
        "has_openai_client": bool(getattr(settings, "OPENAI_API_KEY", "")),
        "profile": profile,
        "document_upload_status": document_upload_status,
    }


@login_required
def index(request):
    context = build_dashboard_context(request.user)
    return render(request, "dashboard/index.html", context)


@login_required
def cashflow_view(request, year):
    data = calculate_cashflow(request.user, year)
    if not data:
        return render(request, "dashboard/cashflow_empty.html", {"year": year})
    return render(request, "dashboard/cashflow.html", {"data": data, "year": year})


@login_required
def api_cashflow(request, year):
    """API endpoint pro načítání Profit vs Cash Flow tabulky pro specifický rok"""
    cf = calculate_cashflow(request.user, year)
    context = {
        "cashflow": cf,
        "cashflow_table": _build_cashflow_table(cf),
    }
    html = render_to_string("dashboard/partials/cashflow_table.html", context, request=request)
    return HttpResponse(html)


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

        # 🧱 Ujisti se, že složka charts existuje
        charts_dir = os.path.join(settings.MEDIA_ROOT, "charts")
        os.makedirs(charts_dir, exist_ok=True)

        file_name = f"chart_{chart_id}.png"
        file_path = os.path.join(charts_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(image_binary)

        print(f"✅ Graf uložen: {file_path}")  # volitelný log
        return JsonResponse({"status": "ok", "file": file_path})

    return JsonResponse({"status": "error", "message": "invalid method"}, status=405)


@login_required
def ask_coach(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "invalid_method"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        payload = {}

    message = (payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"success": False, "error": "empty_message"}, status=400)

    reply_text = None
    client = _get_openai_client()
    if client:
        try:
            model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
            completion = client.chat.completions.create(
                model=model_name,
                temperature=0.55,
                max_tokens=380,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Jsi kouč Scaleupboardu. Reaguj stručně, konkrétně a povzbudivě."
                            " Zaměř se na další krok, potvrď pochopení a nabídni pomocné kroky."
                        ),
                    },
                    {"role": "user", "content": message},
                ],
            )
            reply_text = completion.choices[0].message.content.strip()
        except Exception as exc:
            print(f"⚠️ OpenAI ask_coach error: {exc}")
            reply_text = None

    if not reply_text:
        reply_text = (
            "Zprávu předáme koučovi. Připrav si prosím konkrétní situace a údaje,"
            " které chceš probrat – pomůže to urychlit společné řešení."
        )

    profile = CompanyProfile.objects.filter(user=request.user).select_related("assigned_coach").first()
    if profile and profile.assigned_coach:
        CoachClientNotes.objects.get_or_create(coach=profile.assigned_coach, client=profile)

    return JsonResponse({"success": True, "reply": reply_text})


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


def api_metrics_series(request):
    """
    Vrátí časové řady klíčových metrik a YoY růsty pro přihlášeného uživatele.
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": "Přihlaste se."}
        }, status=401)

    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    rows = []
    for s in statements:
        d = s.data or {}
        revenue = _get_metric(d, ("revenue", "Revenue"), 0.0)
        cogs = _get_cogs_value(d)
        overheads = _compute_overheads(d)
        gross_margin = _get_metric(d, ("gross_margin", "GrossMargin"))
        if gross_margin is None:
            gross_margin = revenue - cogs

        ebit = _get_metric(d, ("ebit", "EBIT"))
        if ebit is None:
            ebit = gross_margin - overheads

        net_profit = _get_metric(d, ("net_profit", "NetProfit"))
        if net_profit is None:
            net_profit = revenue - cogs - overheads
        rows.append({
            "year": int(s.year),
            "revenue": revenue,
            "cogs": cogs,
            "overheads": overheads,
            "ebit": ebit,
            "net_profit": net_profit,
        })

    rows = sorted(rows, key=lambda r: r["year"])
    years = [r["year"] for r in rows]

    margins = []
    for r in rows:
        profitability = compute_profitability(
            r["revenue"],
            r["revenue"] - r["cogs"],
            r["ebit"],
            r["net_profit"],
        )
        margins.append({
            "year": r["year"],
            **profitability,
        })

    yoy = []
    for i, r in enumerate(rows):
        if i == 0:
            yoy.append({
                "year": r["year"],
                "revenue_yoy": None,
                "cogs_yoy": None,
                "overheads_yoy": None,
                "net_profit_yoy": None,
                "ebit_yoy": None,
            })
        else:
            p = rows[i-1]
            yoy.append({
                "year": r["year"],
                "revenue_yoy": growth(r["revenue"], p["revenue"]),
                "cogs_yoy": growth(r["cogs"], p["cogs"]),
                "overheads_yoy": growth(r["overheads"], p["overheads"]),
                "net_profit_yoy": growth(r["net_profit"], p["net_profit"]),
                "ebit_yoy": growth(r["ebit"], p["ebit"]),
            })

    return JsonResponse({
        "success": True,
        "years": years,
        "series": rows,
        "margins": margins,
        "yoy": yoy,
    })


@login_required
def api_profitability(request):
    """Vrací přehled ziskovosti (náhrada za templates/dashboard/profitability.html)."""
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    rows = []
    for stmt in statements:
        data = stmt.data or {}
        revenue = _get_metric(data, ("revenue", "Revenue"), 0.0)
        cogs = _get_cogs_value(data)
        overheads = _compute_overheads(data)
        gross_margin = _get_metric(data, ("gross_margin", "GrossMargin"))
        if gross_margin is None:
            gross_margin = revenue - cogs
        ebit = _get_metric(data, ("ebit", "EBIT"))
        if ebit is None:
            ebit = gross_margin - overheads
        net_profit = _get_metric(data, ("net_profit", "NetProfit"))
        if net_profit is None:
            net_profit = revenue - cogs - overheads

        profitability = compute_profitability(revenue, gross_margin, ebit, net_profit)

        rows.append({
            "year": stmt.year,
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "overheads": overheads,
            "ebit": ebit,
            "net_profit": net_profit,
            "gm_pct": profitability["gm_pct"],
            "op_pct": profitability["op_pct"],
            "np_pct": profitability["np_pct"],
        })

    return JsonResponse({"success": True, "rows": rows})


@login_required
def api_cashflow_summary(request):
    """
    Vrací souhrn pro stránku cashflow:
    - seznam dostupných roků
    - detailní výpočet pro vybraný rok (výchozí poslední dostupný nebo ?year=)
    """
    years = list(
        FinancialStatement.objects.filter(owner=request.user)
        .values_list("year", flat=True)
        .order_by("year")
    )
    if not years:
        return JsonResponse({"success": True, "years": [], "current_year": None, "cashflow": None})

    try:
        selected_year = int(request.GET.get("year", years[-1]))
    except (TypeError, ValueError):
        selected_year = years[-1]

    if selected_year not in years:
        selected_year = years[-1]

    cf = calculate_cashflow(request.user, selected_year) or {}

    return JsonResponse({
        "success": True,
        "years": years,
        "current_year": selected_year,
        "cashflow": cf,
    })
