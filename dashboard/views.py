import os
import io
import json
import base64

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

from .cashflow import calculate_cashflow


def _clean_text(text):
    if not text:
        return ""
    return " ".join(str(text).strip().split())


def _extract_recommendation_points(text, max_points=5):
    if not text:
        return []
    points = []
    for raw_line in text.splitlines():
        line = raw_line.strip("•-•— \t")
        if not line:
            continue
        points.append(line)
        if len(points) >= max_points:
            break
    if not points:
        points = [text.strip()]
    return points


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


@login_required
def index(request):
    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")

    rows = []
    for s in statements:
        d = s.data or {}

        # ZÃ¡kladnÃ­ vÃ½poÄty
        revenue = d.get("Revenue", 0)
        cogs = d.get("COGS", 0)
        gross_margin = revenue - cogs
        overheads = d.get("Overheads", 0)
        depreciation = d.get("Depreciation", 0)
        ebit = d.get("EBIT", gross_margin - overheads - depreciation)
        net_profit = d.get("NetProfit", 0)

        # Cashflow (jen zÃ¡kladnÃ­ bloky)
        cash_from_customers = d.get("CashFromCustomers", revenue)
        cash_to_suppliers = d.get("CashToSuppliers", cogs)
        gross_cash_profit = cash_from_customers - cash_to_suppliers
        cash_overheads = d.get("Overheads", overheads)
        operating_cf = gross_cash_profit - cash_overheads

        interest = d.get("InterestPaid", 0)
        tax = d.get("IncomeTaxPaid", 0)
        extraordinary = d.get("ExtraordinaryItems", 0)
        dividends = d.get("DividendsPaid", 0)
        capex = d.get("Capex", 0)
        other_assets = d.get("OtherAssets", 0)

        net_cf = operating_cf - interest - tax - extraordinary - dividends - capex + other_assets

        rows.append({
            "year": s.year,
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "overheads": overheads,
            "depreciation": depreciation,
            "ebit": ebit,
            "net_profit": net_profit,

            # Profitability % (pomÄ›rovÃ© ukazatele)
            "profitability": {
                "gm_pct": (gross_margin / revenue * 100) if revenue else 0,
                "op_pct": (ebit / revenue * 100) if revenue else 0,
                "np_pct": (net_profit / revenue * 100) if revenue else 0,
            },

            # Cashflow
            "cash_from_customers": cash_from_customers,
            "cash_to_suppliers": cash_to_suppliers,
            "gross_cash_profit": gross_cash_profit,
            "cash_overheads": cash_overheads,
            "operating_cf": operating_cf,
            "interest": interest,
            "tax": tax,
            "extraordinary": extraordinary,
            "dividends": dividends,
            "capex": capex,
            "other_assets": other_assets,
            "net_cf": net_cf,

            "growth": {}  # doplnÃ­me nÃ­Å¾e
        })

    # SeÅ™adit a pÅ™ipravit roky
    rows = sorted(rows, key=lambda r: r["year"])
    years = [r["year"] for r in rows]

    # MeziroÄnÃ­ rÅ¯sty
    for i, r in enumerate(rows):
        if i == 0:
            r["growth"] = {"revenue": 0, "cogs": 0, "overheads": 0}
        else:
            prev = rows[i - 1]
            r["growth"] = {
                "revenue": ((r["revenue"] - prev["revenue"]) / prev["revenue"] * 100) if prev["revenue"] else 0,
                "cogs": ((r["cogs"] - prev["cogs"]) / prev["cogs"] * 100) if prev["cogs"] else 0,
                "overheads": ((r["overheads"] - prev["overheads"]) / prev["overheads"] * 100) if prev["overheads"] else 0,
            }

    # 📈 Insights from survey responses
    survey_history = []
    latest_submission = None
    submissions_qs = SurveySubmission.objects.filter(user=request.user).order_by("created_at")
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
    for answer in OpenAnswer.objects.filter(user=request.user).order_by("-created_at"):
        if answer.ai_response:
            open_answer_summary = _clean_text(answer.ai_response)
            break
    coach_recommendation = open_answer_summary or coach_summary
    recommendation_points = _extract_recommendation_points(coach_recommendation) if coach_recommendation else []

    profile = CompanyProfile.objects.filter(user=request.user).select_related("assigned_coach").first()
    assigned_coach = getattr(profile, "assigned_coach", None)
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
        Document.objects.filter(owner=request.user, doc_type__in=list(doc_type_map.keys()))
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

    # ðŸ’° Výpočet cash flow pro poslední rok (póvodní logika)
    cf = None
    selected_year = years[-1] if years else None
    cashflow_table = []
    if selected_year:
        try:
            cf = calculate_cashflow(request.user, selected_year)
        except Exception as exc:
            print(f"⚠️ Chyba výpočtu cashflow: {exc}")
        else:
            cashflow_table = _build_cashflow_table(cf)

    return render(request, "dashboard/index.html", {
        "rows": json.dumps(rows),
        "years": json.dumps(years),
        "table_rows": rows,
        "cashflow": cf,
        "cashflow_table": cashflow_table,
        "selected_year": selected_year,
        "company_score": company_score,
        "score_trend": score_trend,
        "score_history": json.dumps([
            {"label": (item["ts"].strftime("%d.%m.%Y") if item["ts"] else str(idx)), "value": item["value"]}
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
    })


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
    """UloÅ¾Ã­ pÅ™ijatÃ½ base64 PNG z frontendu do MEDIA_ROOT/charts/."""
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

        # ðŸŸ¢ Ujisti se, Å¾e sloÅ¾ka charts existuje
        charts_dir = os.path.join(settings.MEDIA_ROOT, "charts")
        os.makedirs(charts_dir, exist_ok=True)

        file_name = f"chart_{chart_id}.png"
        file_path = os.path.join(charts_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(image_binary)

        print(f"âœ… Graf uloÅ¾en: {file_path}")  # volitelnÃ½ log
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
    VytvoÅ™Ã­ PDF, do kterÃ©ho vloÅ¾Ã­ vÅ¡echny PNG grafy z MEDIA_ROOT
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("ðŸ“Š Financial Dashboard", styles["Title"]))
    elements.append(Spacer(1, 12))

    # projdi vÅ¡echny chart_*.png v MEDIA_ROOT
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
    VrÃ¡tÃ­ ÄasovÃ© Å™ady klÃ­ÄovÃ½ch metrik a YoY rÅ¯sty pro pÅ™ihlÃ¡Å¡enÃ©ho uÅ¾ivatele.
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            "success": False,
            "error": {"code": "UNAUTHORIZED", "message": "PÅ™ihlaste se."}
        }, status=401)

    statements = FinancialStatement.objects.filter(owner=request.user).order_by("year")
    rows = []
    for s in statements:
        d = s.data or {}
        revenue = float(d.get("Revenue", 0))
        cogs = float(d.get("COGS", 0))
        overheads = float(d.get("Overheads", 0))
        depreciation = float(d.get("Depreciation", 0))
        ebit = float(d.get("EBIT", (revenue - cogs - overheads - depreciation)))
        net_profit = float(d.get("NetProfit", (revenue - cogs - overheads - depreciation)))
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
        rev = r["revenue"]
        gm = (r["revenue"] - r["cogs"]) if rev else 0
        op = (r["revenue"] - r["cogs"] - r["overheads"]) if rev else 0
        np = r["net_profit"]
        margins.append({
            "year": r["year"],
            "gm_pct": (gm / rev * 100) if rev else 0.0,
            "op_pct": (op / rev * 100) if rev else 0.0,
            "np_pct": (np / rev * 100) if rev else 0.0,
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
            def growth(cur, prev):
                try:
                    if prev and prev != 0:
                        return (cur - prev) / abs(prev) * 100.0
                except Exception:
                    pass
                return None
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
        revenue = float(data.get("Revenue", 0))
        cogs = float(data.get("COGS", 0))
        overheads = float(data.get("Overheads", 0))
        depreciation = float(data.get("Depreciation", 0))
        gross_margin = float(data.get("GrossMargin", revenue - cogs))
        ebit = float(data.get("EBIT", revenue - cogs - overheads - depreciation))
        net_profit = float(data.get("NetProfit", revenue - cogs - overheads - depreciation))

        gm_pct = (gross_margin / revenue * 100) if revenue else 0.0
        op_pct = (ebit / revenue * 100) if revenue else 0.0
        np_pct = (net_profit / revenue * 100) if revenue else 0.0

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
