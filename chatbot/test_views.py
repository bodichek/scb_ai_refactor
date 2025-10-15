import os
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def test_openai(request):
    """Testovací endpoint pro OpenAI připojení"""
    
    # Načti API klíč
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        return JsonResponse({
            "error": "OPENAI_API_KEY není nastaven v .env souboru",
            "status": "failed"
        })
    
    if not api_key.startswith('sk-'):
        return JsonResponse({
            "error": "OPENAI_API_KEY má nesprávný formát (měl by začínat 'sk-')",
            "status": "failed"
        })
    
    # Test OpenAI importu
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Jednoduchý test API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Řekni pouze 'API funguje'"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        
        return JsonResponse({
            "status": "success",
            "message": "OpenAI API úspěšně připojeno",
            "test_response": result,
            "api_key_prefix": api_key[:20] + "..."
        })
        
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        })

def test_page(request):
    """Testovací stránka pro OpenAI"""
    return render(request, 'chatbot/test.html')