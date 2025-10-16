#!/usr/bin/env python
"""
Script pro nastavení coach profilu pro brona.klus@gmail.com
"""

import os
import sys
import django

# Setup Django
sys.path.append('c:\\Users\\Administrator\\Documents\\work\\scaleup\\scb_ai_refactor')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import CompanyProfile, UserRole
from coaching.models import Coach


def setup_brona_coach():
    """Nastaví coach profil pro brona.klus@gmail.com"""
    print("🔧 Nastavuji coach profil pro brona.klus@gmail.com...")
    
    try:
        # Najdi uživatele brona.klus@gmail.com
        brona_user = User.objects.get(username='brona.klus@gmail.com')
        print(f"✅ Nalezen uživatel: {brona_user.username}")
        
        # Vytvoř nebo aktualizuj Coach profil
        coach_profile, created = Coach.objects.get_or_create(
            user=brona_user,
            defaults={
                'specialization': 'Finanční poradenství a business coaching',
                'bio': 'Zkušený business coach specializující se na finanční řízení SME',
                'phone': '+420 123 456 789',
                'email': 'brona.klus@gmail.com',
                'city': 'Praha',
                'available': True
            }
        )
        
        if created:
            print("✅ Vytvořen nový Coach profil")
        else:
            print("✅ Coach profil už existuje, aktualizuji...")
            coach_profile.specialization = 'Finanční poradenství a business coaching'
            coach_profile.bio = 'Zkušený business coach specializující se na finanční řízení SME'
            coach_profile.available = True
            coach_profile.save()
        
        # Vytvoř nebo aktualizuj UserRole
        role, created = UserRole.objects.get_or_create(
            user=brona_user,
            defaults={'role': 'coach'}
        )
        if created:
            print("✅ Vytvořena role coach")
        else:
            role.role = 'coach'
            role.save()
            print("✅ Role aktualizována na coach")
        
        print(f"✅ Coach profil: {coach_profile}")
        
        # Teď přiřaďme skutečné klienty
        print("\n🔗 Přiřazuji klienty k coach profilu...")
        
        # Najdi existující company profiles (včetně všech kromě prázdných)
        all_clients = CompanyProfile.objects.exclude(user=brona_user)  # Jen nepřiřazuj sám sebe
        
        print("📋 Dostupní klienti:")
        for client in all_clients:
            print(f"  - ID {client.id}: '{client.company_name}' (user: {client.user.username})")
        
        assigned_count = 0
        for client in all_clients:
            # Přiřaď všechny klienty k tomuto kouči
            old_coach = client.assigned_coach
            client.assigned_coach = coach_profile
            client.save()
            print(f"  ✅ Přiřazen klient: '{client.company_name}' (user: {client.user.username})")
            assigned_count += 1
        
        print(f"\n🎉 Dokončeno! Přiřazeno {assigned_count} klientů k coach profilu.")
        
        # Výsledný přehled
        print("\n📊 FINÁLNÍ STAV:")
        print(f"Coach: {coach_profile.user.username}")
        print(f"Specialization: {coach_profile.specialization}")
        print(f"Přiřazení klienti:")
        
        assigned_clients = CompanyProfile.objects.filter(assigned_coach=coach_profile)
        for client in assigned_clients:
            print(f"  - {client.company_name} ({client.user.username})")
        
        return coach_profile
        
    except User.DoesNotExist:
        print("❌ Uživatel brona.klus@gmail.com nebyl nalezen!")
        return None
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return None


if __name__ == '__main__':
    setup_brona_coach()