import json
from uuid import UUID, uuid4
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from openai import OpenAI

from .models import OpenAnswer

client = OpenAI(api_key=settings.OPENAI_API_KEY)

QUESTIONS = [
    {
        "section": "VÍCE ČASU",
        "items": [
            "Jak často a v jaké podobě se věnuji strategickému přemýšlení o směřování firmy?",
            "Co mi nejvíce bere čas a energii?",
            "V jaké roli se cítím nejvíce produktivní a užitečný/á?",
        ],
    },
    {
        "section": "VÍCE PENĚZ",
        "items": [
            "Mám dostatek finančních zdrojů na své potřeby a rozvoj firmy?",
            "Co jsou hlavní faktory ovlivňující růst mého byznysu?",
        ],
    },
    {
        "section": "MÉNĚ STRACHU",
        "items": [
            "Čeho se nejvíce obávám nebo mi brání v rozhodování?",
            "Kdyby všechny obavy a pochybnosti zmizely, co bych podniknul/a ve svém podnikání?",
            "Co mi nejvíce brání v mém podnikání?",
        ],
    },
]

COOLDOWN_SECONDS = 10


class NoAnswerProvided(Exception):
    pass


class DuplicateSubmissionError(Exception):
    pass


def _build_ai_prompt(user_inputs):
    system = (
        "Jsi byznysový kouč. Stručně, konkrétně a akčně shrň odpovědi zakladatele firmy, "
        "identifikuj tři až pět hlavních zjištění a navrhni pět krátkých, proveditelných doporučení. "
        "Používej češtinu, buď věcný, bez floskulí."
    )

    lines = []
    for idx, row in enumerate(user_inputs, start=1):
        lines.append(f"{idx}) [{row['section']}] {row['question']}\n→ Odpověď: {row['answer']}")

    user_text = (
        "Níže jsou moje otevřené odpovědi v kategoriích ČAS/PENÍZE/STRACH.\n\n"
        + "\n\n".join(lines)
        + "\n\nProsím: 1) krátké shrnutí, 2) klíčové poznatky, 3) 5 konkrétních kroků na 14 dní."
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]


def _ask_openai(messages, model=None):
    model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=900,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # pragma: no cover - OpenAI fallback
        return (
            "Nepodařilo se získat odpověď od AI. "
            "Zkontroluj nastavení OPENAI_API_KEY/OPENAI_MODEL.\n"
            f"Detail: {type(exc).__name__}: {exc}"
        )


def _create_submission(user, answers):
    cleaned = []
    for item in answers:
        section = item.get("section", "").strip()
        question = item.get("question", "").strip()
        answer = (item.get("answer") or "").strip()
        cleaned.append({"section": section, "question": question, "answer": answer})

    if not any(entry["answer"] for entry in cleaned):
        raise NoAnswerProvided("Vyplňte alespoň jednu odpověď.")

    last = OpenAnswer.objects.filter(user=user).order_by("-created_at").first()
    if last and (timezone.now() - last.created_at) < timedelta(seconds=COOLDOWN_SECONDS):
        raise DuplicateSubmissionError("Formulář byl odeslán příliš rychle po sobě.")

    ai_text = _ask_openai(_build_ai_prompt(cleaned))
    batch_id = uuid4()

    with transaction.atomic():
        for entry in cleaned:
            OpenAnswer.objects.create(
                user=user,
                batch_id=batch_id,
                section=entry["section"],
                question=entry["question"],
                answer=entry["answer"],
                ai_response=ai_text,
            )

    return batch_id, ai_text


def _get_summaries(user):
    batches = (
        OpenAnswer.objects.filter(user=user)
        .values("batch_id")
        .annotate(count=Count("id"), created_at=Max("created_at"))
        .order_by("-created_at")
    )
    summaries = []
    for batch in batches:
        answers = (
            OpenAnswer.objects.filter(user=user, batch_id=batch["batch_id"])
            .order_by("created_at")
        )
        first = answers.first()
        summaries.append({
            "batch_id": str(batch["batch_id"]),
            "created_at": batch["created_at"].isoformat() if batch["created_at"] else None,
            "answer_count": batch["count"],
            "ai_response": getattr(first, "ai_response", None),
        })
    return summaries


def _get_batch_detail(user, batch_id):
    try:
        batch_uuid = UUID(str(batch_id))
    except (TypeError, ValueError):
        return None

    answers = list(
        OpenAnswer.objects.filter(user=user, batch_id=batch_uuid).order_by("created_at")
    )
    if not answers:
        return None
    first = answers[0]
    return {
        "batch_id": str(batch_uuid),
        "created_at": first.created_at.isoformat() if first.created_at else None,
        "ai_response": first.ai_response,
        "answers": [
            {"section": a.section, "question": a.question, "answer": a.answer}
            for a in answers
        ],
    }


@login_required
def form(request):
    if request.method == "POST":
        answers = []
        for s_idx, block in enumerate(QUESTIONS):
            for q_idx, question in enumerate(block["items"]):
                key = f"q-{s_idx}-{q_idx}"
                answer = (request.POST.get(key) or "").strip()
                answers.append({
                    "section": block["section"],
                    "question": question,
                    "answer": answer,
                })
        try:
            _create_submission(request.user, answers)
        except NoAnswerProvided:
            submissions = (
                OpenAnswer.objects.filter(user=request.user)
                .values("batch_id")
                .annotate(count=Count("id"), created_at=Max("created_at"))
                .order_by("-created_at")
            )
            return render(request, "suropen/form.html", {
                "questions": QUESTIONS,
                "submissions": submissions,
                "error": "Vyplň prosím alespoň jednu odpověď.",
                "just_submitted": False,
                "duplicate": False,
            })
        except DuplicateSubmissionError:
            return redirect(reverse("suropen:form") + "?duplicate=1")

        return redirect(reverse("suropen:form") + "?submitted=1")

    submissions = (
        OpenAnswer.objects.filter(user=request.user)
        .values("batch_id")
        .annotate(count=Count("id"), created_at=Max("created_at"))
        .order_by("-created_at")
    )

    just_submitted = request.GET.get("submitted") == "1"
    duplicate = request.GET.get("duplicate") == "1"

    return render(request, "suropen/form.html", {
        "questions": QUESTIONS,
        "submissions": submissions,
        "just_submitted": just_submitted,
        "duplicate": duplicate,
        "ai_text": None,
    })


@login_required
def history(request):
    summaries = _get_summaries(request.user)
    data = []
    for summary in summaries:
        detail = _get_batch_detail(request.user, summary["batch_id"])
        if detail:
            data.append(detail)
    return render(request, "suropen/history.html", {"batches": data})


# ---- API endpoints ----

@login_required
@require_http_methods(["GET", "POST"])
def form_api(request):
    if request.method == "GET":
        return JsonResponse({
            "questions": QUESTIONS,
            "submissions": _get_summaries(request.user),
            "cooldown_seconds": COOLDOWN_SECONDS,
        })

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON body.")

    answers = payload.get("answers")
    if not isinstance(answers, list):
        return HttpResponseBadRequest("Pole answers musí být seznam.")

    try:
        batch_id, _ = _create_submission(request.user, answers)
    except NoAnswerProvided as exc:
        return HttpResponseBadRequest(str(exc))
    except DuplicateSubmissionError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=429)

    detail = _get_batch_detail(request.user, batch_id)
    summary = _get_summaries(request.user)[0] if detail else None

    return JsonResponse({
        "success": True,
        "submission": summary,
        "detail": detail,
    }, status=201)


@login_required
def history_api(request):
    batches = []
    for summary in _get_summaries(request.user):
        detail = _get_batch_detail(request.user, summary["batch_id"])
        if detail:
            batches.append(detail)
    return JsonResponse({"batches": batches})


@login_required
def batch_detail_api(request, batch_id):
    detail = _get_batch_detail(request.user, batch_id)
    if not detail:
        return JsonResponse({"error": "Nenalezeno."}, status=404)
    return JsonResponse({"batch": detail})
