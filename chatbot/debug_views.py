import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def debug_config(request):
    """Debug endpoint pro kontrolu konfigurace"""
    
    # Načti environment variables
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Test importu
    try:
        import openai
        from openai import OpenAI
        openai_available = True
        openai_version = openai.__version__
    except ImportError as e:
        openai_available = False
        openai_version = str(e)
    
    # Test .env loading
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        env_path = BASE_DIR / ".env"
        load_dotenv(env_path)
        
        # Reload API key after dotenv
        api_key_after_dotenv = os.getenv('OPENAI_API_KEY')
        
        dotenv_info = {
            "available": True,
            "env_file_exists": env_path.exists(),
            "env_file_path": str(env_path),
            "api_key_before": bool(api_key),
            "api_key_after": bool(api_key_after_dotenv),
            "api_key_format_ok": bool(api_key_after_dotenv and api_key_after_dotenv.startswith('sk-'))
        }
    except ImportError as e:
        dotenv_info = {"available": False, "error": str(e)}
    
    return JsonResponse({
        "status": "DEBUG",
        "environment": {
            "api_key_set": bool(api_key),
            "api_key_format": api_key[:20] + "..." if api_key else None,
        },
        "openai": {
            "available": openai_available,
            "version": openai_version
        },
        "dotenv": dotenv_info
    }, json_dumps_params={'indent': 2})