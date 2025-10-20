import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from exports.services import get_latest_export
from .models import ChatMessage

# Načtení .env souboru
try:
    from dotenv import load_dotenv
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None

logger = logging.getLogger(__name__)

CLASSIFIER_MODEL = "gpt-4o-mini"
ASSISTANT_MODEL = "gpt-4o"

CONTEXT_PROMPTS = {
    "ingest": "Uživatel právě nahrává finanční výkazy. Pomoz mu s interpretací dat.",
    "dashboard": "Uživatel se dívá na finanční dashboard s grafy a tabulkami.",
    "survey": "Uživatel vyplňuje dotazník o své firmě.",
    "exports": "Uživatel chce exportovat data do PDF.",
}

CLASSIFIER_PROMPT = (
    "Posuď, zda dotaz vyžaduje konkrétní finanční data z posledního exportu "
    "uživatele (například výsledovku, růst tržeb, marže, cash flow nebo trendy). "
    'Odpověz pouze slovem "context" nebo "general".'
)

ASSISTANT_SYSTEM_PROMPT = """Jsi finanční analytik české aplikace ScaleupBoard.
Pracuješ s čísly z exportů a pomáháš s vysvětlováním finančních ukazatelů i praktickou interpretací.

Pokyny:
- Odpovídej česky, věcně a srozumitelně.
- Pokud obdržíš JSON s klíčem context_data, použij tato čísla pro výpočty a vysvětlení.
- Pokud data chybí nebo některý ukazatel nelze spočítat, jasně to sděl a popiš, co je k výpočtu potřeba.
- Nepřidávej neověřená čísla, vycházej pouze z poskytnutých dat nebo z obecných principů.
- Navrhni konkrétní další kroky jen tehdy, když dávají smysl pro daný dotaz.
"""


def _compose_system_prompt(section: Optional[str]) -> str:
    prompt = ASSISTANT_SYSTEM_PROMPT
    section_key = (section or "").lower()
    if section_key in CONTEXT_PROMPTS:
        prompt += f"\n\nKontext sekce: {CONTEXT_PROMPTS[section_key]}"
    return prompt


def _classify_query(
    client: "OpenAI",
    message: str,
    section: Optional[str],
) -> str:
    try:
        classifier_messages = [
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {
                "role": "user",
                "content": f"Sekce: {section or 'neuvedeno'}\nDotaz: {message}",
            },
        ]
        completion = client.chat.completions.create(
            model=CLASSIFIER_MODEL,
            messages=classifier_messages,
            max_tokens=4,
            temperature=0,
        )
        label = completion.choices[0].message.content.strip().lower()
        if "context" in label:
            return ChatMessage.QUERY_CONTEXT
    except Exception as exc:
        logger.warning("Classifier fallback: %s", exc)
    return ChatMessage.QUERY_GENERAL


def _build_user_payload(
    message: str,
    section: Optional[str],
    context_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "query": message,
    }
    if section:
        payload["section"] = section
    if context_data is not None:
        payload["context_data"] = context_data
    return payload


def _build_messages(
    system_prompt: str,
    message: str,
    section: Optional[str],
    context_data: Optional[Dict[str, Any]],
) -> list[Dict[str, str]]:
    if context_data is not None:
        user_payload = _build_user_payload(message, section, context_data)
        user_content = json.dumps(user_payload, ensure_ascii=False)
    else:
        prefix = f"[Sekce: {section}]\n" if section else ""
        user_content = f"{prefix}{message}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def chat_api(request):
    """API endpoint pro chatbot komunikaci s OpenAI."""

    if not openai:
        return JsonResponse(
            {"error": "OpenAI knihovna není nainstalována."},
            status=500,
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JsonResponse(
            {"error": "OpenAI API klíč není nastaven. Zkontroluj .env soubor."},
            status=500,
        )

    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Neplatný JSON formát."},
            status=400,
        )

    user_message = (payload.get("message") or "").strip()
    section = (payload.get("section") or "").strip() or "dashboard"

    if not user_message:
        return JsonResponse(
            {"error": "Zpráva nemůže být prázdná."},
            status=400,
        )

    try:
        client = OpenAI(api_key=api_key)
    except Exception as exc:
        logger.exception("Failed to initialise OpenAI client: %s", exc)
        return JsonResponse(
            {"error": f"Nepodařilo se inicializovat OpenAI klienta: {exc}"},
            status=500,
        )

    query_type = _classify_query(client, user_message, section)

    export_record = None
    export_data = None

    if query_type == ChatMessage.QUERY_CONTEXT:
        export_record = get_latest_export(request.user, ensure_exists=True)
        if not export_record:
            fallback_response = "Nemám aktuální exportní data, prosím nejdříve nahraj finanční výkaz."
            ChatMessage.objects.create(
                user=request.user,
                role=ChatMessage.ROLE_USER,
                section=section,
                query_type=ChatMessage.QUERY_CONTEXT,
                message=user_message,
                response=fallback_response,
                context_data=None,
            )
            return JsonResponse(
                {
                    "response": fallback_response,
                    "success": False,
                    "query_type": ChatMessage.QUERY_CONTEXT,
                    "context_attached": False,
                }
            )
    else:
        export_record = get_latest_export(request.user, ensure_exists=False)

    if export_record:
        export_data = export_record.data

    system_prompt = _compose_system_prompt(section)
    context_for_model = export_data if query_type == ChatMessage.QUERY_CONTEXT else None
    messages = _build_messages(system_prompt, user_message, section, context_for_model)

    try:
        completion = client.chat.completions.create(
            model=ASSISTANT_MODEL,
            messages=messages,
            max_tokens=400,
            temperature=0.3,
        )
        ai_response = completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("Assistant completion failed: %s", exc)
        return JsonResponse(
            {"error": f"Chyba při komunikaci s AI: {exc}"},
            status=500,
        )

    ChatMessage.objects.create(
        user=request.user,
        role=ChatMessage.ROLE_USER,
        section=section,
        query_type=query_type,
        message=user_message,
        response=ai_response,
        context_data=export_data,
    )

    return JsonResponse(
        {
            "response": ai_response,
            "success": True,
            "query_type": query_type,
            "context_attached": context_for_model is not None,
        }
    )


@login_required
def chat_history(request):
    """Zobrazí historii chatů uživatele"""
    messages = ChatMessage.objects.filter(user=request.user)[:20]
    return render(request, 'chatbot/history.html', {
        'messages': messages
    })
