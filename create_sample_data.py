#!/usr/bin/env python
"""
Vytvoření ukázkových survey a suropen dat pro testování rozšířeného dashboardu
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from survey.models import SurveySubmission, Response
from suropen.models import OpenAnswer
import uuid
from datetime import datetime, timedelta


def create_sample_data():
    print("=== Vytváření ukázkových dat pro rozšířený dashboard ===\n")
    
    # Najdeme testovací uživatele
    try:
        test_client = User.objects.get(username='test_client')
        client_example = User.objects.get(username='client@example.com')
        print("✅ Nalezeni testovací uživatelé")
    except User.DoesNotExist:
        print("❌ Testovací uživatelé nenalezeni")
        return
    
    users = [test_client, client_example]
    
    for user in users:
        print(f"\n🔍 Vytvářím data pro: {user.username}")
        
        # === SURVEY DATA ===
        print("  📋 Vytvářím survey data...")
        
        # Vytvoříme 2 survey submissions
        for i in range(2):
            submission = SurveySubmission.objects.create(
                user=user,
                ai_response=f"AI analýza {i+1}: Uživatel {user.username} vykazuje pozitivní postoj k finančnímu plánování a má jasné cíle."
            )
            
            # Přidáme odpovědi
            questions_scores = [
                ("Jak hodnotíte svou současnou finanční situaci?", 7),
                ("Jaké jsou vaše hlavní finanční cíle na příští rok?", 9),
                ("Co vás nejvíce trápí ve vašem podnikání?", 6),
                ("Jak často sledujete své finanční ukazatele?", 8),
                ("Používáte nějaký systém pro sledování cash flow?", 5)
            ]
            
            for question, score in questions_scores:
                Response.objects.create(
                    user=user,
                    submission=submission,
                    question=question,
                    score=score
                )
            
            print(f"    ✅ Survey submission {i+1} vytvořena ({len(questions_scores)} odpovědí)")
        
        # === SUROPEN DATA ===
        print("  🔓 Vytvářím suropen data...")
        
        # Vytvoříme 1-2 suropen batche
        for batch_num in range(2):
            batch_id = uuid.uuid4()
            created_date = datetime.now() - timedelta(days=batch_num * 15)
            
            ai_response = f"AI analýza batch {batch_num+1}: Uživatel projevuje ambice v oblasti růstu, ale potřebuje podporu v time managementu a strategickém myšlení."
            
            # VÍCE ČASU sekce
            time_questions = [
                ("Co byste dělali, kdybyste měli více času?", "Věnoval/a bych se strategickému plánování a rozvoji nových produktů."),
                ("Kde nejvíce ztrácíte čas?", "V administrativě a nekonečných meetinzích bez jasného výstupu."),
                ("Jak byste chtěli optimalizovat svůj čas?", "Delegováním rutinních úkolů a automatizací procesů.")
            ]
            
            for question, answer in time_questions:
                OpenAnswer.objects.create(
                    user=user,
                    batch_id=batch_id,
                    section="VÍCE ČASU",
                    question=question,
                    answer=answer,
                    ai_response=ai_response,
                    created_at=created_date
                )
            
            # VÍCE PENĚZ sekce
            money_questions = [
                ("Co byste dělali s více penězi?", "Investoval/a bych do marketingu a nových technologií pro růst firmy."),
                ("Kde vidíte největší příležitosti pro zvýšení příjmů?", "V rozšíření produktové řady a vstupu na nové trhy."),
                ("Co vás brzdí v dosahování vyšších příjmů?", "Nedostatek kapitálu na investice a konkurence na trhu.")
            ]
            
            for question, answer in money_questions:
                OpenAnswer.objects.create(
                    user=user,
                    batch_id=batch_id,
                    section="VÍCE PENĚZ",
                    question=question,
                    answer=answer,
                    ai_response=ai_response,
                    created_at=created_date
                )
            
            # MÉNĚ STRACHU sekce
            fear_questions = [
                ("Čeho se nejvíce bojíte v podnikání?", "Ekonomické krize a ztráty klíčových zákazníků."),
                ("Jak byste se cítili bez těchto obav?", "Mnohem sebevědoměji a byl/a bych ochotnější riskovat pro růst."),
                ("Co by vám pomohlo překonat tyto strachy?", "Lepší finanční rezervy a diverzifikované portfolio zákazníků.")
            ]
            
            for question, answer in fear_questions:
                OpenAnswer.objects.create(
                    user=user,
                    batch_id=batch_id,
                    section="MÉNĚ STRACHU",
                    question=question,
                    answer=answer,
                    ai_response=ai_response,
                    created_at=created_date
                )
            
            print(f"    ✅ Suropen batch {batch_num+1} vytvořen (9 odpovědí ve 3 sekcích)")
    
    # === STATISTIKY ===
    print("\n=== Finální statistiky ===")
    total_surveys = SurveySubmission.objects.count()
    total_responses = Response.objects.count()
    total_suropen = OpenAnswer.objects.values('batch_id').distinct().count()
    total_suropen_answers = OpenAnswer.objects.count()
    
    print(f"✅ Celkem survey submissions: {total_surveys}")
    print(f"✅ Celkem survey odpovědí: {total_responses}")
    print(f"✅ Celkem suropen batchů: {total_suropen}")
    print(f"✅ Celkem suropen odpovědí: {total_suropen_answers}")
    
    print("\n🎉 Ukázková data vytvořena!")
    print("📝 Doporučení:")
    print("   1. Otevřete http://127.0.0.1:8000/coaching/my-clients/")
    print("   2. Vyberte klienta (test_client nebo client@example.com)")
    print("   3. Vyzkoušejte taby 'Dotazníky' a 'Suropen'")
    print("   4. V tab 'Grafy' uvidíte ukázkové grafy")


if __name__ == '__main__':
    create_sample_data()