from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Max
from .models import OpenAnswer

# OpenAI client
from openai import OpenAI
client = OpenAI()  # používá env OPENAI_API_KEY


# 🔹 Otázky napevno (sekce → otázky)
QUESTIONS = [
    {
        "section": "VÍCE ČASU",
        "items": [
            "Jak často a v jaké podobě se věnuji strategickému přemýšlení o směrování firmy?",
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
            "Kdyby všechny obavy a pochybnosti zmizely, co bych podniknul ve svém podnikání?",
            "Co mi nejvíce brání v mém podnikání?",
        ],
    },
]


# 🔹 Pomocné funkce
def _build_ai_prompt(user_inputs):
    """Vytvoří prompt pro OpenAI z otevřených odpovědí."""
    system = (
        "Jsi byznysový kouč. Stručně, konkrétně a akčně shrň odpovědi zakladatele firmy, "
        "identifikuj 3–5 hlavních zjištění a navrhni 5 krátkých, proveditelných doporučení. "
        "Používej češtinu, buď věcný, bez floskulí."
    )

    lines = []
    for i, r in enumerate(user_inputs, 1):
        lines.append(f"{i}) [{r['section']}] {r['question']}\n→ Odpověď: {r['answer']}")

    user_text = (
        "Níže jsou moje otevřené odpovědi v kategoriích ČAS/PENÍZE/STRACH.\n\n"
        + "\n\n".join(lines)
        + "\n\nProsím: 1) krátké shrnutí, 2) klíčové překážky, 3) 5 konkrétních kroků na 14 dní."
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]


def _ask_openai(messages, model=None):
    """Zavolá OpenAI API a vrátí textovou odpověď."""
    model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=900,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return (
            "⚠️ Nepodařilo se získat odpověď od AI. "
            "Zkontroluj nastavení OPENAI_API_KEY/OPENAI_MODEL.\n"
            f"Detail: {type(e).__name__}: {e}"
        )


# 🔹 Hlavní view
@login_required
def form(request):
    if request.method == "POST":
        collected = []
        for s_idx, block in enumerate(QUESTIONS):
            for q_idx, question in enumerate(block["items"]):
                key = f"q-{s_idx}-{q_idx}"
                ans = (request.POST.get(key) or "").strip()
                collected.append({
                    "section": block["section"],
                    "question": question,
                    "answer": ans,
                })

        # ✅ validace: musí být aspoň jedna odpověď
        if not any(item["answer"] for item in collected):
            submissions = (
                OpenAnswer.objects.filter(user=request.user)
                .values("batch_id")
                .annotate(
                    count=Count("id"),
                    created_at=Max("created_at"),  # vezme nejnovější čas z batch
                )
                .order_by("-created_at")
            )
            return render(request, "suropen/form.html", {
                "questions": QUESTIONS,
                "error": "Vyplň prosím alespoň jednu odpověď.",
                "submissions": submissions,
            })

        # ✅ ochrana proti opakovanému odeslání do 10 s
        last = OpenAnswer.objects.filter(user=request.user).order_by("-created_at").first()
        if last and (timezone.now() - last.created_at) < timedelta(seconds=10):
            print("⚠️ Ignoruji duplicitní odeslání")
            return redirect(reverse("suropen:form") + "?duplicate=1")

        # ✅ AI + uložení
        messages = _build_ai_prompt(collected)
        ai_text = _ask_openai(messages)

        from uuid import uuid4
        batch_id = uuid4()
        with transaction.atomic():
            for item in collected:
                OpenAnswer.objects.create(
                    user=request.user,
                    batch_id=batch_id,
                    section=item["section"],
                    question=item["question"],
                    answer=item["answer"],
                    ai_response=ai_text,
                )

        # ✅ redirect (PRG)
        return redirect(reverse("suropen:form") + "?submitted=1")

    # 🔹 GET – načteme historii (souhrn batchů)
    submissions = (
        OpenAnswer.objects.filter(user=request.user)
        .values("batch_id")
        .annotate(
            count=Count("id"),
            created_at=Max("created_at"),
        )
        .order_by("-created_at")
    )

    ai_text = None
    just_submitted = request.GET.get("submitted") == "1"
    duplicate = request.GET.get("duplicate") == "1"

    return render(request, "suropen/form.html", {
        "questions": QUESTIONS,
        "submissions": submissions,
        "just_submitted": just_submitted,
        "duplicate": duplicate,
        "ai_text": ai_text,
    })


@login_required
def history(request):
    """Přehled vlastních odeslání seskupený dle batch_id."""
    batches = (
        OpenAnswer.objects
        .filter(user=request.user)
        .values("batch_id")
        .annotate(created_at=Max("created_at"))
        .order_by("-created_at")
    )

    data = []
    for b in batches:
        items = list(
            OpenAnswer.objects.filter(user=request.user, batch_id=b["batch_id"])
            .order_by("created_at")
            .values("section", "question", "answer", "ai_response")
        )
        data.append({
            "batch_id": b["batch_id"],
            "created_at": b["created_at"],
            "items": items,
            "ai_response": items[0]["ai_response"] if items else None,
        })

    return render(request, "suropen/history.html", {"batches": data})
