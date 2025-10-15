#!/usr/bin/env python
"""
Test script pro ověření funkcionalit coach dashboard a client management systému
"""

import os
import sys
import django

# Setup Django
sys.path.append('c:\\Users\\Administrator\\Documents\\work\\scaleup\\scb_ai_refactor')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import CompanyProfile, Coach, UserRole, CoachClientNotes
from accounts.permissions import get_user_role, is_coach, can_coach_access_client


def test_coach_system():
    """Test základních funkcionalit coach systému"""
    print("🧪 Testování coach/client management systému")
    print("=" * 60)
    
    # Test 1: Vytvoření testovacích uživatelů
    print("\n1️⃣ Vytváření testovacích uživatelů...")
    
    # Vytvoř kouče
    coach_user, created = User.objects.get_or_create(
        username='coach@example.com',
        defaults={
            'email': 'coach@example.com',
            'first_name': 'Test',
            'last_name': 'Coach'
        }
    )
    if created:
        coach_user.set_password('testpass123')
        coach_user.save()
    
    coach_role, _ = UserRole.objects.get_or_create(
        user=coach_user,
        defaults={'role': 'coach'}
    )
    
    coach_profile, _ = Coach.objects.get_or_create(
        user=coach_user,
        defaults={
            'specialization': 'Finanční poradenství',
            'bio': 'Zkušený finanční poradce',
            'phone': '+420 123 456 789',
            'email': 'coach@example.com',
            'city': 'Praha',
            'available': True
        }
    )
    
    # Vytvoř klienta
    client_user, created = User.objects.get_or_create(
        username='client@example.com',
        defaults={
            'email': 'client@example.com',
            'first_name': 'Test',
            'last_name': 'Client'
        }
    )
    if created:
        client_user.set_password('testpass123')
        client_user.save()
    
    client_role, _ = UserRole.objects.get_or_create(
        user=client_user,
        defaults={'role': 'company'}
    )
    
    client_profile, _ = CompanyProfile.objects.get_or_create(
        user=client_user,
        defaults={
            'company_name': 'Test s.r.o.',
            'ico': '12345678',
            'address': 'Testovací 123',
            'city': 'Praha',
            'postal_code': '110 00',
            'contact_person': 'Jan Novák',
            'phone': '+420 987 654 321',
            'industry': 'IT služby',
            'assigned_coach': coach_profile
        }
    )
    
    # Klient už je přiřazen kouči přes assigned_coach field
    print(f"   Klient přiřazen kouči: {client_profile.assigned_coach}")
    
    print(f"✅ Kouč vytvořen: {coach_user.username} ({coach_profile.specialization})")
    print(f"✅ Klient vytvořen: {client_user.username} ({client_profile.company_name})")
    
    # Test 2: Testování permissions systému
    print("\n2️⃣ Testování permissions systému...")
    
    # Test role detection
    coach_role_detected = get_user_role(coach_user)
    client_role_detected = get_user_role(client_user)
    
    print(f"✅ Role kouče: {coach_role_detected}")
    print(f"✅ Role klienta: {client_role_detected}")
    
    # Test is_coach function
    coach_check = is_coach(coach_user)
    client_check = is_coach(client_user)
    
    print(f"✅ is_coach(coach_user): {coach_check}")
    print(f"✅ is_coach(client_user): {client_check}")
    
    # Test přístupu kouče ke klientovi
    access_allowed_user = can_coach_access_client(coach_user, client_user)
    access_allowed_profile = can_coach_access_client(coach_user, client_profile)
    print(f"✅ Kouč má přístup ke klientovi (User): {access_allowed_user}")
    print(f"✅ Kouč má přístup ke klientovi (Profile): {access_allowed_profile}")
    
    # Test 3: Poznámky kouče
    print("\n3️⃣ Testování poznámek kouče...")
    
    note, created = CoachClientNotes.objects.get_or_create(
        coach=coach_profile,
        client=client_profile,
        defaults={'notes': 'Testovací poznámka o klientovi. Má potenciál pro růst.'}
    )
    
    if created:
        print("✅ Poznámka kouče vytvořena")
    else:
        print("✅ Poznámka kouče již existuje")
    
    print(f"📝 Poznámka: {note.notes[:50]}...")
    
    # Test 4: Statistiky
    print("\n4️⃣ Statistiky systému...")
    
    total_coaches = Coach.objects.count()
    total_clients = CompanyProfile.objects.count()
    total_assignments = CompanyProfile.objects.filter(assigned_coach__isnull=False).count()
    
    print(f"📊 Celkem koučů: {total_coaches}")
    print(f"📊 Celkem klientů: {total_clients}")
    print(f"📊 Celkem přiřazení: {total_assignments}")
    
    # Test 5: URL patterns (základní kontrola)
    print("\n5️⃣ Kontrola URL patterns...")
    
    try:
        from django.urls import reverse
        urls_to_test = [
            'coaching:my_clients',
            'coaching:edit_coach',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"✅ URL {url_name}: {url}")
            except Exception as e:
                print(f"❌ URL {url_name}: {e}")
                
        # URLs s parametry
        try:
            client_dashboard_url = reverse('coaching:client_dashboard', kwargs={'client_id': client_profile.id})
            print(f"✅ URL coaching:client_dashboard: {client_dashboard_url}")
        except Exception as e:
            print(f"❌ URL coaching:client_dashboard: {e}")
            
        try:
            client_docs_url = reverse('coaching:client_documents', kwargs={'client_id': client_profile.id})
            print(f"✅ URL coaching:client_documents: {client_docs_url}")
        except Exception as e:
            print(f"❌ URL coaching:client_documents: {e}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    
    print("\n🎉 Test dokončen!")
    print("=" * 60)
    
    return {
        'coach_user': coach_user,
        'client_user': client_user,
        'coach_profile': coach_profile,
        'client_profile': client_profile
    }


if __name__ == '__main__':
    test_data = test_coach_system()
    
    print("\n💡 Pro testování v browseru:")
    print(f"   Kouč login: {test_data['coach_user'].username} / testpass123")
    print(f"   Klient login: {test_data['client_user'].username} / testpass123")
    print("   Server: http://127.0.0.1:8000/")
    print("   Coach dashboard: http://127.0.0.1:8000/coaching/my-clients/")