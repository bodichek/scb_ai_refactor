# survey/utils.py
from openai import OpenAI
from django.conf import settings
from .models import OpenAnswer

client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))


def generate_ai_summary(batch_id, user):
    """
    Vytvoří souhrn odpovědí v rámci jednoho batch_id a uloží jej do všech odpovědí.
    """
    answers = OpenAnswer.objects.filter(user=user, batch_id=batch_id)
    if not answers.exists():
        return None

    # Vytvoření textu pro shrnutí
    text = "\n".join([f"Otázka: {a.question}\nOdpověď: {a.answer}" for a in answers])

    prompt = f"""
Shrň odpovědi uživatele z dotazníku do několika vět.
Zaměř se na hlavní témata, výzvy a pozitivní oblasti.
Piš česky, srozumitelně a přehledně.

{text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Jsi asistent, který shrnuje odpovědi z dotazníků."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        summary = response.choices[0].message.content.strip()

        # Uložení shrnutí ke všem odpovědím v batchi
        answers.update(ai_response=summary)
        return summary

    except Exception as e:
        print("❌ Chyba při generování AI shrnutí:", e)
        return None
