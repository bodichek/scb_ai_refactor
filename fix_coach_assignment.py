#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from coaching.models import Coach
from accounts.models import CompanyProfile, UserRole

print("=== Oprava přiřazení coach@example.com → brona.kus@gmail.com ===")

# 1. Najdeme/vytvoříme coach@example.com jako kouče
coach_users = User.objects.filter(email='coach@example.com')
if coach_users.exists():
    coach_user = coach_users.first()  # Vezmeme prvního
    print(f'✅ Coach user nalezen: {coach_user.email} (našel jsem {coach_users.count()} duplicitů)')
    
    # Smažeme duplicity
    if coach_users.count() > 1:
        for duplicate in coach_users[1:]:
            duplicate.delete()
            print(f'🗑️ Smazán duplicitní user: {duplicate.username}')
else:
    coach_user = User.objects.create_user(
        username='coach_example',
        email='coach@example.com',
        password='password123',
        first_name='Jan',
        last_name='Kouč'
    )
    print(f'✅ Coach user vytvořen: {coach_user.email}')

# Vytvoříme/najdeme Coach profil
coach, created = Coach.objects.get_or_create(
    user=coach_user,
    defaults={
        'specialization': 'Finanční poradenství',
        'bio': 'Zkušený kouč pro finanční růst podniků'
    }
)
print(f'✅ Coach profil: {coach}')

# Nastavíme roli
role, created = UserRole.objects.get_or_create(
    user=coach_user,
    defaults={'role': 'coach'}
)
if not created and role.role != 'coach':
    role.role = 'coach'
    role.save()
print(f'✅ Role nastavena: {role.role}')

# 2. Najdeme/vytvoříme brona.kus@gmail.com jako klienta  
try:
    client_user = User.objects.get(email='brona.kus@gmail.com')
    print(f'✅ Client user nalezen: {client_user.email}')
except User.DoesNotExist:
    client_user = User.objects.create_user(
        username='brona_kus',
        email='brona.kus@gmail.com', 
        password='password123',
        first_name='Brona',
        last_name='Kus'
    )
    print(f'✅ Client user vytvořen: {client_user.email}')

# Vytvoříme/najdeme CompanyProfile a přiřadíme kouče
profile, created = CompanyProfile.objects.get_or_create(
    user=client_user,
    defaults={
        'company_name': 'Brona Trading s.r.o.',
        'ico': '12345678',
        'city': 'Praha',
        'industry': 'Obchodní služby',
        'contact_person': 'Brona Kus',
        'phone': '+420 123 456 789'
    }
)

# ⭐ KLÍČOVÉ: Přiřadíme správného kouče
profile.assigned_coach = coach
profile.save()
print(f'✅ Client profile: {profile.company_name}')
print(f'✅ Přiřazen kouč: {profile.assigned_coach}')

# Nastavíme roli klienta
client_role, created = UserRole.objects.get_or_create(
    user=client_user,
    defaults={'role': 'company'}
)
if not created and client_role.role != 'company':
    client_role.role = 'company'
    client_role.save()

print(f"\n🎯 VÝSLEDEK:")
print(f"👤 Coach: {coach_user.email} ({coach_user.username})")
print(f"🏢 Client: {client_user.email} ({profile.company_name})")
print(f"🔗 Přiřazení: {profile.assigned_coach}")

# Ověření
clients = CompanyProfile.objects.filter(assigned_coach=coach)
print(f"\n📋 Klienti přiřazení k {coach_user.email}:")
for c in clients:
    print(f"  - {c.company_name} ({c.user.email})")

print(f"\n✅ Hotovo! Nyní se můžeš přihlásit jako coach@example.com a uvidíš klienta.")