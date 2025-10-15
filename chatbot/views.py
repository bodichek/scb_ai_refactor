import json
import os
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
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


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def chat_api(request):
    """API endpoint pro chatbot komunikaci s OpenAI"""
    
    if not openai:
        return JsonResponse({
            "error": "OpenAI knihovna není nainstalována"
        }, status=500)
    
    try:
        print(f"DEBUG: Request body: {request.body}")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
        
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        context = data.get('context', '')
        
        print(f"DEBUG: Message: {user_message}, Context: {context}")
        
        if not user_message:
            return JsonResponse({
                "error": "Zpráva nemůže být prázdná"
            }, status=400)
        
        # Systémový prompt pro finanční asistenta
        system_prompt = """Jsi finanční asistent pro českou aplikaci na analýzu firmy. 
        Pomáháš uživatelům s vyplňováním finančních dat a vysvětluješ účetní pojmy.
        
        Specializuješ se na:
        - České účetnictví a daňový řád
        - Vysvětlování finančních ukazatelů (tržby, COGS, EBIT, čistý zisk)
        - Pomoc s nahráváním a interpretací finančních výkazů
        - Cash flow analýzu
        - Rozdíly mezi ziskem a peněžním tokem
        
        Odpovídej POUZE v češtině, stručně a srozumitelně. 
        Používej české účetní termíny. Pokud si nejsi jistý, doporuč konzultaci s účetním."""
        
        # Přidáme kontext na základě aktuální stránky
        context_prompts = {
            'ingest': 'Uživatel právě nahrává finanční výkazy. Pomoz mu s interpretací dat.',
            'dashboard': 'Uživatel se dívá na finanční dashboard s grafy a tabulkami.',
            'survey': 'Uživatel vyplňuje dotazník o své firmě.',
            'exports': 'Uživatel chce exportovat data do PDF.',
        }
        
        if context in context_prompts:
            system_prompt += f"\n\nKontext: {context_prompts[context]}"
        
        # Volání OpenAI API
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return JsonResponse({
                "error": "OpenAI API klíč není nastaven. Zkontroluj .env soubor."
            }, status=500)
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Uložíme do databáze
        ChatMessage.objects.create(
            user=request.user,
            message=user_message,
            response=ai_response,
            context=context
        )
        
        return JsonResponse({
            "response": ai_response,
            "success": True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "error": "Neplatný JSON formát"
        }, status=400)
    except Exception as e:
        print(f"DEBUG: Exception occurred: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return JsonResponse({
            "error": f"Chyba při komunikaci s AI: {str(e)}"
        }, status=500)


@login_required
def chat_history(request):
    """Zobrazí historii chatů uživatele"""
    messages = ChatMessage.objects.filter(user=request.user)[:20]
    return render(request, 'chatbot/history.html', {
        'messages': messages
    })
