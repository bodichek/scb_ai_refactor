"""
RAG-Enhanced Chatbot Views

New chat endpoint with RAG integration for context-aware responses.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ChatMessage
from .services import RAGChatService

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)

# Models
ASSISTANT_MODEL = "gpt-4o"

# System prompt for RAG-enhanced chatbot
RAG_SYSTEM_PROMPT = """Jsi finanční analytik české aplikace ScaleupBoard.
Pomáháš uživatelům s interpretací jejich finančních dat a dokumentů.

Pokyny:
- Odpovídej česky, věcně a srozumitelně
- Když dostaneš kontext z dokumentů, vždy ho využij pro odpověď
- Cituj konkrétní dokumenty a roky, ze kterých čerpáš informace
- Pokud kontext neobsahuje odpověď, upřimně to přiznej
- Navrhni konkrétní další kroky jen když dávají smysl
- Buď precizní s čísly a daty
"""


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def chat_api_rag(request):
    """
    RAG-enhanced chat API endpoint.

    POST /chatbot/api/rag/
    Body: {
        "message": "user query",
        "section": "dashboard",  // optional
        "use_rag": true  // optional, default true
    }

    Returns: {
        "success": true,
        "response": "assistant response with sources",
        "has_rag_context": bool,
        "sources": [...],
        "message_id": int
    }
    """
    if not HAS_OPENAI:
        return JsonResponse({
            "success": False,
            "error": "OpenAI není nakonfigurován"
        }, status=500)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JsonResponse({
            "success": False,
            "error": "OPENAI_API_KEY není nastavena"
        }, status=500)

    try:
        # Parse request
        body = json.loads(request.body)
        message = body.get("message", "").strip()
        section = body.get("section")
        use_rag = body.get("use_rag", True)

        if not message:
            return JsonResponse({
                "success": False,
                "error": "Prázdná zpráva"
            }, status=400)

        # Initialize services
        rag_service = RAGChatService()
        client = OpenAI(api_key=api_key)

        # Generate RAG-enhanced response
        if use_rag:
            rag_result = rag_service.generate_rag_response(
                query=message,
                user=request.user,
                section=section,
            )

            user_message = rag_result["prompt"]
            has_rag_context = rag_result["has_rag_context"]
            sources = rag_result["sources"]
        else:
            # Fallback to non-RAG mode
            section_prefix = f"[Sekce: {section}]\n" if section else ""
            user_message = f"{section_prefix}{message}"
            has_rag_context = False
            sources = []

        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # Call OpenAI
        completion = client.chat.completions.create(
            model=ASSISTANT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
        )

        assistant_response = completion.choices[0].message.content.strip()

        # Format response with sources
        if has_rag_context and sources:
            formatted = rag_service.format_response_with_sources(
                response=assistant_response,
                sources=sources,
            )
            final_response = formatted["response"]
        else:
            final_response = assistant_response

        # Save to database
        chat_message = ChatMessage.objects.create(
            user=request.user,
            role=ChatMessage.ROLE_USER,
            section=section or "",
            query_type=ChatMessage.QUERY_CONTEXT if has_rag_context else ChatMessage.QUERY_GENERAL,
            message=message,
            response=final_response,
            context_data={
                "has_rag": has_rag_context,
                "sources": sources,
                "model": ASSISTANT_MODEL,
            }
        )

        logger.info(
            f"RAG Chat: user={request.user.id}, "
            f"has_context={has_rag_context}, "
            f"sources={len(sources)}"
        )

        return JsonResponse({
            "success": True,
            "response": final_response,
            "has_rag_context": has_rag_context,
            "sources": sources,
            "message_id": chat_message.id,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Neplatný JSON"
        }, status=400)

    except Exception as e:
        logger.error(f"RAG Chat error: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Interní chyba serveru"
        }, status=500)


@login_required
@require_http_methods(["GET"])
def chat_history_rag(request):
    """
    Get chat history with RAG context.

    GET /chatbot/api/history-rag/?limit=20

    Returns: {
        "success": true,
        "messages": [
            {
                "id": 1,
                "message": "user query",
                "response": "assistant response",
                "has_rag": bool,
                "sources_count": int,
                "timestamp": "ISO datetime"
            }
        ]
    }
    """
    try:
        limit = int(request.GET.get("limit", 20))

        messages = ChatMessage.objects.filter(
            user=request.user
        ).order_by("-timestamp")[:limit]

        message_list = []
        for msg in messages:
            context_data = msg.context_data or {}
            has_rag = context_data.get("has_rag", False)
            sources = context_data.get("sources", [])

            message_list.append({
                "id": msg.id,
                "message": msg.message,
                "response": msg.response,
                "has_rag": has_rag,
                "sources_count": len(sources),
                "sources": sources,
                "timestamp": msg.timestamp.isoformat(),
                "section": msg.section,
            })

        return JsonResponse({
            "success": True,
            "messages": message_list,
            "count": len(message_list),
        })

    except Exception as e:
        logger.error(f"Chat history error: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Interní chyba serveru"
        }, status=500)
