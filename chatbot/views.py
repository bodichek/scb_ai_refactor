import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from exports.services import get_latest_export
from ingest.models import Document, FinancialStatement
from survey.models import Response, SurveySubmission
from suropen.models import OpenAnswer

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
    "ingest": "Uzivatel prave nahrava financni vykazy. Pomoz mu s interpretaci dat.",
    "dashboard": "Uzivatel se diva na financni dashboard s grafy a tabulkami.",
    "survey": "Uzivatel vyplnuje dotaznik o sve firme.",
    "exports": "Uzivatel chce exportovat data do PDF.",
}

CLASSIFIER_PROMPT = (
    "Posud, zda dotaz vyzaduje konkretni firemni data uzivatele. Data mohou pochazet z financnich exportu, "
    "nahranych vykazu, seznamu dokumentu, vysledku pruzkumu nebo otevrenych odpovedi. "
    'Odpovez pouze slovem "context" nebo "general".'
)

ASSISTANT_SYSTEM_PROMPT = """Jsi financni analytik ceske aplikace ScaleupBoard.
Pracujes s cisly z exportu a databaze a pomahas s vysvetlovanim financnich ukazatelu i praktickou interpretaci.

Pokyny:
- Odpovidej cesky, vecne a srozumitelne.
- Pokud obdrzis JSON s klicem context_data, obsah muze zahrnovat latest_export, financial_statements, documents,
  survey_history nebo open_answers. Pracuj pouze s tim, co je skutecne k dispozici a nevymyslej dalsi cisla.
- Pokud data chybi nebo n�kter� ukazatel nelze spocitat, jasne to uved a popis, co je ke spocitani potreba.
- Navrhni konkretni dalsi kroky jen tehdy, kdyz davaji smysl pro dany dotaz.
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


FINANCIAL_METRIC_KEYS: List[str] = [
    "Revenue",
    "COGS",
    "GrossMargin",
    "Overheads",
    "Depreciation",
    "EBIT",
    "NetProfit",
    "CashFromCustomers",
    "CashToSuppliers",
]


def _collect_user_context(user) -> Dict[str, Any]:
    # Build a snapshot of user-specific data that the assistant can leverage.
    # Returns an empty dict if nothing useful is available.
    context: Dict[str, Any] = {}

    # Latest export payload
    try:
        export = get_latest_export(user, ensure_exists=True)
    except Exception as exc:
        logger.warning("Unable to obtain export snapshot: %s", exc)
        export = None

    if export:
        export_payload = {
            "statement_year": export.statement_year,
            "created_at": export.created_at.isoformat(),
            "source": export.source,
            "data": export.data,
        }
        if export.metadata:
            export_payload["metadata"] = export.metadata
        context["latest_export"] = export_payload

    # Financial statements overview
    try:
        statements = list(
            FinancialStatement.objects.filter(owner=user)
            .select_related("document")
            .order_by("-year")[:3]
        )
    except Exception as exc:
        logger.warning("Unable to load financial statements: %s", exc)
        statements = []

    if statements:
        snapshot: List[Dict[str, Any]] = []
        for stmt in statements:
            data = stmt.data or {}
            metrics = {key: data.get(key) for key in FINANCIAL_METRIC_KEYS if key in data}
            entry: Dict[str, Any] = {
                "year": stmt.year,
                "created_at": stmt.created_at.isoformat(),
                "metrics": metrics,
                "data": data,
            }
            document = getattr(stmt, "document", None)
            if document:
                entry["document"] = {
                    "id": document.id,
                    "type": document.doc_type,
                    "year": document.year,
                    "filename": document.filename,
                    "analyzed": document.analyzed,
                    "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
                }
            snapshot.append(entry)
        context["financial_statements"] = snapshot

    # Uploaded documents (including those without statements yet)
    try:
        documents = list(
            Document.objects.filter(owner=user)
            .order_by("-uploaded_at")
            .values("id", "doc_type", "year", "filename", "analyzed", "uploaded_at")[:10]
        )
    except Exception as exc:
        logger.warning("Unable to load documents: %s", exc)
        documents = []

    if documents:
        for doc in documents:
            uploaded_at = doc.get("uploaded_at")
            if uploaded_at:
                doc["uploaded_at"] = uploaded_at.isoformat()
        context["documents"] = documents

    # Survey submissions with responses
    try:
        survey_prefetch = Prefetch(
            "responses",
            queryset=Response.objects.order_by("created_at"),
        )
        submissions = list(
            SurveySubmission.objects.filter(user=user)
            .prefetch_related(survey_prefetch)
            .order_by("-created_at")[:3]
        )
    except Exception as exc:
        logger.warning("Unable to load survey submissions: %s", exc)
        submissions = []

    if submissions:
        records: List[Dict[str, Any]] = []
        for submission in submissions:
            responses = list(submission.responses.all())
            scores = [resp.score for resp in responses if resp.score is not None]
            avg_score = round(sum(scores) / len(scores), 2) if scores else None
            records.append(
                {
                    "created_at": submission.created_at.isoformat(),
                    "average_score": avg_score,
                    "ai_summary": submission.ai_response,
                    "responses": [
                        {"question": resp.question, "score": resp.score}
                        for resp in responses
                    ],
                }
            )
        context["survey_history"] = records

    # Latest batch of open-ended answers (coaching form)
    try:
        latest_answer = (
            OpenAnswer.objects.filter(user=user)
            .order_by("-created_at")
            .first()
        )
    except Exception as exc:
        logger.warning("Unable to load open answers: %s", exc)
        latest_answer = None

    if latest_answer:
        batch_answers = list(
            OpenAnswer.objects.filter(user=user, batch_id=latest_answer.batch_id)
            .order_by("created_at")
        )
        context["open_answers"] = {
            "batch_id": str(latest_answer.batch_id),
            "created_at": batch_answers[0].created_at.isoformat() if batch_answers else None,
            "ai_summary": latest_answer.ai_response,
            "entries": [
                {
                    "section": answer.section,
                    "question": answer.question,
                    "answer": answer.answer,
                }
                for answer in batch_answers
            ],
        }

    return context


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

    context_payload: Optional[Dict[str, Any]] = None
    if query_type == ChatMessage.QUERY_CONTEXT:
        context_payload = _collect_user_context(request.user)
        if not context_payload:
            fallback_response = (
                "Nemam k dispozici zadna ulozena firemni data. "
                "Nahraj prosim financni vykaz nebo vypln dotaznik a zkus to znovu."
            )
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

    system_prompt = _compose_system_prompt(section)
    messages = _build_messages(system_prompt, user_message, section, context_payload)

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
            {"error": f"Chyba pri komunikaci s AI: {exc}"},
            status=500,
        )

    ChatMessage.objects.create(
        user=request.user,
        role=ChatMessage.ROLE_USER,
        section=section,
        query_type=query_type,
        message=user_message,
        response=ai_response,
        context_data=context_payload,
    )

    return JsonResponse(
        {
            "response": ai_response,
            "success": True,
            "query_type": query_type,
            "context_attached": bool(context_payload),
        }
    )

@login_required
def chat_history(request):
    """Display chat history for the current user."""
    messages = ChatMessage.objects.filter(user=request.user)[:20]
    return render(request, 'chatbot/history.html', {
        'messages': messages
    })


