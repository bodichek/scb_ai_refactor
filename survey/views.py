from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from .models import Response, SurveySubmission
from openai import OpenAI
from django.conf import settings
import json

# ✅ OpenAI klient
client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))



# 🔹 Otázky a odpovědi napevno
QUESTIONS = [
    {
        "category": "CEO",
        "question": "Mám dostatek času na strategická rozhodnutí a rozvoj firmy.",
        "labels": {
            "1-2": "Vůbec nemám čas na strategická rozhodnutí, jsem zahlcen operativou.",
            "3-4": "Mám velmi omezený čas na strategická rozhodnutí, většina mé práce je operativní.",
            "5-6": "Někdy mám čas na strategii, ale je to nepravidelné a omezené.",
            "7-8": "Mám pravidelně dostatek času věnovat se strategii firmy.",
            "9-10": "Věnuji se převážně strategickým rozhodnutím a rozvoji, operativa mě minimálně zatěžuje."
        }
    },
    {
        "category": "CEO",
        "question": "Práce v mojí firmě mě baví, naplňuje a inspiruje.",
        "labels": {
            "1-2": "Necítím žádnou motivaci nebo nadšení z práce ve firmě.",
            "3-4": "Práce mě baví, ale radost často ztrácím kvůli stresu nebo problémům.",
            "5-6": "Svou práci dělám rád, ale někdy se cítím přetížený.",
            "7-8": "Ze své práce mám většinou radost a těším se na ni.",
            "9-10": "Práce ve firmě mi dává smysl, baví mě a inspiruje k neustálému rozvoji sebe i firmy."
        }
    },
    {
        "category": "CEO",
        "question": "Firma mi poskytuje dostatečné zdroje.",
        "labels": {
            "1-2": "Nemám dostatek financí na své potřeby a škálování firmy.",
            "3-4": "Mám základní finanční příjmy, ale nedostačují na větší růst.",
            "5-6": "Mám dostatek zdrojů na provoz, ale omezený prostor pro investice.",
            "7-8": "Firma mi přináší tolik, kolik očekávám, a dokážu s tím růst.",
            "9-10": "Mám dostatečné financování a zdroje pro maximální rozvoj firmy."
        }
    },
    {
        "category": "LIDÉ",
        "question": "Leadership a osobní růst.",
        "labels": {
            "1-2": "Na rozvoj leadershipu a osobní růst svých lidí nemám čas ani zdroje.",
            "3-4": "Snažím se se svými lidmi stanovovat cíle a motivovat je, ale není to systematické.",
            "5-6": "Hledám svůj styl leadershipu a snažím se být srozumitelný pro ostatní.",
            "7-8": "Systematicky pracuji na svém osobním růstu a leadershipu.",
            "9-10": "Podporuji své lidi v jejich osobním růstu a rozvoji, leadership je na vysoké úrovni."
        }
    },
    {
        "category": "LIDÉ",
        "question": "Přitahování a získávání talentů.",
        "labels": {
            "1-2": "Naše firma má špatnou pověst, což ztěžuje nábor nových lidí.",
            "3-4": "Volné pozice obsazujeme pomalu nebo s problémy.",
            "5-6": "Volné pozice ve firmě se nám daří bez větších problémů obsazovat.",
            "7-8": "Ve firmě jsou správní lidé na správných místech, ale stále hledáme talenty.",
            "9-10": "Aktivně nás vyhledávají a oslovují talentovaní lidé."
        }
    },
    {
        "category": "LIDÉ",
        "question": "Management a firemní kultura.",
        "labels": {
            "1-2": "V naší firmě není jasná organizační struktura a pravidla.",
            "3-4": "Máme vytvořenou základní strukturu a rámcový popis odpovědností.",
            "5-6": "Máme jasnou strukturu, definované pozice a popisy práce.",
            "7-8": "Každá pozice má jasně stanovené odpovědnosti a funguje spolupráce.",
            "9-10": "Ve firmě je patrná kultura odpovědnosti na všech úrovních."
        }
    },
    {
        "category": "STRATEGIE",
        "question": "Identita firmy, její poslání a hodnoty.",
        "labels": {
            "1-2": "Ve firmě není povědomí o jejím poslání a hodnotách.",
            "3-4": "Poslání a hodnoty firmy jsou vnímané, ale ne příliš uplatňované.",
            "5-6": "Je popsáno poslání firmy a její klíčové hodnoty.",
            "7-8": "Poslání firmy a klíčové hodnoty jsou dobře známé a uplatňované v praxi.",
            "9-10": "Všichni členové týmu přirozeně žijí firemním posláním a hodnotami."
        }
    },
    {
        "category": "STRATEGIE",
        "question": "Vize a strategické odlišení.",
        "labels": {
            "1-2": "Firma nemá žádnou konkrétní vizi budoucího stavu.",
            "3-4": "Máme vizi budoucího stavu, ale nevíme, jakým způsobem ji dosáhnout.",
            "5-6": "Známe nejdůležitější strategické oblasti, ale potřebujeme je více rozpracovat.",
            "7-8": "Základy odlišující strategie máme, potřebujeme je více rozvíjet.",
            "9-10": "Máme zpracovanou jednoznačnou odlišující strategii, která nás posouvá vpřed."
        }
    },
    {
        "category": "OBCHOD",
        "question": "Znalost trhu a zákazníků.",
        "labels": {
            "1-2": "Nemáme žádné informace o trhu ani zákaznících.",
            "3-4": "Máme pouze základní představu o trhu a zákaznících.",
            "5-6": "Provádíme občasné analýzy trhu a zákazníků.",
            "7-8": "Pravidelně sledujeme trh a známe potřeby zákazníků.",
            "9-10": "Máme detailní znalosti trhu i zákazníků a využíváme je k růstu."
        }
    },
    {
        "category": "OBCHOD",
        "question": "Prodejní a marketingové procesy.",
        "labels": {
            "1-2": "Nemáme nastavené žádné procesy pro prodej a marketing.",
            "3-4": "Procesy pro prodej a marketing fungují jen velmi omezeně.",
            "5-6": "Máme základní procesy, ale nejsou systematické.",
            "7-8": "Procesy fungují a pravidelně je vyhodnocujeme.",
            "9-10": "Prodejní a marketingové procesy jsou na vysoké úrovni a přinášejí výsledky."
        }
    },
    {
        "category": "FINANCE",
        "question": "Finanční řízení a plánování.",
        "labels": {
            "1-2": "Nemáme přehled o financích a neplánujeme dopředu.",
            "3-4": "Finanční plánování děláme jen ad hoc.",
            "5-6": "Máme základní finanční řízení, ale není systematické.",
            "7-8": "Pravidelně plánujeme finance a sledujeme výsledky.",
            "9-10": "Máme profesionální finanční řízení a jasné finanční plány."
        }
    },
    {
        "category": "FINANCE",
        "question": "Zdroje financování.",
        "labels": {
            "1-2": "Nemáme přístup k žádným zdrojům financování.",
            "3-4": "Financování řešíme pouze ze základních zdrojů.",
            "5-6": "Občas využíváme externí zdroje, ale bez jasné strategie.",
            "7-8": "Máme dostupné různé zdroje financování a využíváme je dle potřeby.",
            "9-10": "Máme stabilní a diverzifikované zdroje financování."
        }
    },
    {
        "category": "PROCESY",
        "question": "Efektivita vnitřních procesů.",
        "labels": {
            "1-2": "Naše procesy jsou chaotické a neefektivní.",
            "3-4": "Procesy máme jen částečně popsané a nejsou důsledně dodržovány.",
            "5-6": "Procesy máme nastavené, ale vyžadují zlepšení.",
            "7-8": "Procesy jsou efektivní a většinou dobře fungují.",
            "9-10": "Naše procesy jsou vysoce efektivní a přinášejí konkurenční výhodu."
        }
    },
    {
        "category": "PROCESY",
        "question": "Digitalizace a technologie.",
        "labels": {
            "1-2": "Nemáme žádné digitální nástroje ani technologie.",
            "3-4": "Používáme jen základní digitální nástroje.",
            "5-6": "Postupně zavádíme digitální nástroje a technologie.",
            "7-8": "Máme většinu procesů digitalizovaných a využíváme moderní technologie.",
            "9-10": "Jsme technologicky vyspělá firma a inovace jsou součástí naší kultury."
        }
    },
    {
        "category": "VÝSLEDKY",
        "question": "Růst a ziskovost.",
        "labels": {
            "1-2": "Firma stagnuje a nedosahuje zisku.",
            "3-4": "Růst je minimální a zisk nízký.",
            "5-6": "Dosahujeme průměrného růstu a ziskovosti.",
            "7-8": "Firma stabilně roste a dosahuje dobré ziskovosti.",
            "9-10": "Firma dynamicky roste a má vysokou ziskovost."
        }
    },
    {
        "category": "VÝSLEDKY",
        "question": "Spokojenost zákazníků.",
        "labels": {
            "1-2": "Zákazníci jsou nespokojení a odcházejí.",
            "3-4": "Část zákazníků je spokojená, část odchází.",
            "5-6": "Většina zákazníků je spokojená, ale máme rezervy.",
            "7-8": "Zákazníci jsou převážně spokojení a zůstávají nám věrní.",
            "9-10": "Máme vysokou spokojenost zákazníků a ti nás aktivně doporučují."
        }
    }
]

def generate_ai_summary(submission):
    """
    Vytvoří AI shrnutí pro jeden SurveySubmission a uloží jej do pole ai_response.
    Používá otázky + jejich význam slovně (ne jen čísla).
    """
    responses = submission.responses.all()
    if not responses.exists():
        return None

    # převod odpovědí na text s popisem významu skóre
    text_blocks = []
    for r in responses:
        label_text = None
        for q in QUESTIONS:
            if q["question"] == r.question:
                for score_range, meaning in q["labels"].items():
                    low, high = map(int, score_range.split("-"))
                    if low <= r.score <= high:
                        label_text = meaning
                        break
        text_blocks.append(f"Otázka: {r.question}\nOdpověď: {label_text or r.score}/10")

    combined_text = "\n\n".join(text_blocks)

    prompt = f"""
Na základě odpovědí z firemního dotazníku shrň hlavní zjištění.

Nepiš rozbor ke každé otázce zvlášť, ale vytvoř celkový přehled:
1. Shrň, jaký celkový obraz o firmě odpovědi vytvářejí (např. silné oblasti, slabiny, nálada ve firmě).
2. Uveď 2-3 klíčové faktory, které firmě pomáhají.
3. Uveď 2-3 největší výzvy nebo problémy, které mohou bránit růstu.
4. Navrhni 2-3 konkrétní doporučení nebo kroky, které mohou situaci zlepšit.

Buď stručný, konkrétní a piš přehledně v profesionálním tónu (max. 4 odstavce).

Níže jsou otázky a odpovědi v textové formě podle významu skóre:

{combined_text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Jsi firemní analytik, který interpretuje odpovědi z interních dotazníků."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=800,
        )
        summary = response.choices[0].message.content.strip()
        submission.ai_response = summary
        submission.save(update_fields=["ai_response"])
        return summary
    except Exception as e:
        print("❌ Chyba při generování AI shrnutí:", e)
        return None

# ✅ Vyplnění dotazníku a AI shrnutí
@login_required
def questionnaire(request):
    if request.method == "POST":
        with transaction.atomic():
            submission = SurveySubmission.objects.create(user=request.user)
            for i, q in enumerate(QUESTIONS):
                score = int(request.POST.get(f"q{i}", 0))
                Response.objects.create(
                    user=request.user,
                    submission=submission,
                    question=q["question"],
                    score=score,
                )

        # 🔹 Po odeslání vygeneruje shrnutí
        generate_ai_summary(submission)
        return redirect("survey:detail", batch_id=submission.batch_id)

    # Přehled dřívějších dotazníků s průměrnými výsledky
    submissions = []
    for s in SurveySubmission.objects.filter(user=request.user).order_by("-created_at"):
        avg_score = s.responses.aggregate(avg=Avg("score"))["avg"]
        submissions.append({
            "batch_id": s.batch_id,
            "created_at": s.created_at,
            "avg_score": round(avg_score, 1) if avg_score is not None else None,
            "ai_response": s.ai_response,
        })

    return render(request, "survey/questionnaire.html", {"questions": QUESTIONS, "submissions": submissions})


# ✅ Souhrn všech odeslaných dotazníků
@login_required
def survey_summary(request):
    """
    Přehled všech odeslaných dotazníků s průměrným hodnocením a shrnutím AI.
    """
    submissions = SurveySubmission.objects.filter(user=request.user).order_by("-created_at")
    batches = []
    for s in submissions:
        avg_score = s.responses.aggregate(avg=Avg("score"))["avg"]
        items = [{"question": r.question, "answer": r.score} for r in s.responses.all()]
        batches.append({
            "batch_id": s.batch_id,
            "created_at": s.created_at,
            "ai_response": s.ai_response,
            "items": items,
            "avg_score": round(avg_score, 1) if avg_score is not None else None,
        })

    # ✅ Vrací HTML šablonu, ne JSON
    return render(request, "survey/summary.html", {"batches": batches})



# ✅ Detail jednoho dotazníku
@login_required
def survey_detail(request, batch_id):
    submission = get_object_or_404(SurveySubmission, user=request.user, batch_id=batch_id)
    responses = submission.responses.all()

    enriched_responses = []
    for r in responses:
        label_text = None
        for q in QUESTIONS:
            if q["question"] == r.question:
                for score_range, text in q["labels"].items():
                    low, high = map(int, score_range.split("-"))
                    if low <= r.score <= high:
                        label_text = text
                        break
        enriched_responses.append({
            "question": r.question,
            "score": r.score,
            "label": label_text,
        })

    avg_score = responses.aggregate(avg=Avg("score"))["avg"]

    # Pokud chybí AI shrnutí, vygeneruj ho
    if not submission.ai_response:
        generate_ai_summary(submission)
        submission.refresh_from_db()

    # Historie dotazníků (pro graf trendu)
    history = list(SurveySubmission.objects.filter(user=request.user).order_by("created_at").prefetch_related("responses"))
    chart_labels = [s.created_at.strftime("%d.%m.%Y") for s in history]
    chart_data = [
        round(sum(r.score for r in s.responses.all()) / s.responses.count(), 2)
        for s in history
    ]

    # Najdi index aktuálního hodnocení pro zvýraznění v grafu
    current_index = next((i for i, s in enumerate(history) if s.batch_id == submission.batch_id), -1)

    return render(request, "survey/detail.html", {
        "submission": submission,
        "responses": enriched_responses,
        "avg_score": avg_score,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "current_index": current_index,
    })


# ---- API endpoints for SPA frontend ----

def _serialize_submission(submission: SurveySubmission, include_items: bool = False):
    avg_score = submission.responses.aggregate(avg=Avg("score"))["avg"]
    data = {
        "batch_id": str(submission.batch_id),
        "created_at": submission.created_at.isoformat(),
        "ai_response": submission.ai_response,
        "avg_score": round(avg_score, 1) if avg_score is not None else None,
    }
    if include_items:
        items = []
        for r in submission.responses.all():
            label_text = None
            for q in QUESTIONS:
                if q["question"] == r.question:
                    for score_range, text in q["labels"].items():
                        low, high = map(int, score_range.split("-"))
                        if low <= r.score <= high:
                            label_text = text
                            break
                    break
            items.append({
                "question": r.question,
                "score": r.score,
                "label": label_text,
            })
        data["items"] = items
    return data


@login_required
@require_http_methods(["GET", "POST"])
def questionnaire_api(request):
    """
    GET: Vrací otázky a seznam odeslaných dotazníků.
    POST: Uloží nové odpovědi, vygeneruje AI shrnutí a vrátí batch_id.
    """
    if request.method == "GET":
        submissions = [
            _serialize_submission(s)
            for s in SurveySubmission.objects.filter(user=request.user).order_by("-created_at")
        ]
        return JsonResponse({
            "questions": QUESTIONS,
            "submissions": submissions,
        })

    # POST
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON body.")

    answers = payload.get("answers")
    if not isinstance(answers, list) or len(answers) != len(QUESTIONS):
        return HttpResponseBadRequest("Odpovědi nejsou ve správném formátu.")

    with transaction.atomic():
        submission = SurveySubmission.objects.create(user=request.user)
        for idx, question in enumerate(QUESTIONS):
            value = answers[idx]
            try:
                score = int(value)
            except (TypeError, ValueError):
                score = 0
            Response.objects.create(
                user=request.user,
                submission=submission,
                question=question["question"],
                score=score,
            )

    generate_ai_summary(submission)

    return JsonResponse({
        "success": True,
        "submission": _serialize_submission(submission),
    }, status=201)


@login_required
def latest_submission_api(request):
    """Vrací poslední odeslaný dotazník."""
    submission = SurveySubmission.objects.filter(user=request.user).order_by("-created_at").first()
    if not submission:
        return JsonResponse({"submission": None})
    return JsonResponse({"submission": _serialize_submission(submission, include_items=True)})


@login_required
def submissions_api(request):
    """Vrací seznam odeslaných dotazníků."""
    submissions = [
        _serialize_submission(s)
        for s in SurveySubmission.objects.filter(user=request.user).order_by("-created_at")
    ]
    return JsonResponse({"submissions": submissions})


@login_required
def submission_detail_api(request, batch_id):
    submission = get_object_or_404(SurveySubmission, user=request.user, batch_id=batch_id)
    data = _serialize_submission(submission, include_items=True)

    history = SurveySubmission.objects.filter(user=request.user).order_by("created_at").prefetch_related("responses")
    chart = []
    for s in history:
        count = s.responses.count() or 1
        avg = sum(r.score for r in s.responses.all()) / count
        chart.append({
            "label": s.created_at.strftime("%d.%m.%Y"),
            "value": round(avg, 2),
        })

    return JsonResponse({"submission": data, "history": chart})
