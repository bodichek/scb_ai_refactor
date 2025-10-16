#!/usr/bin/env python
"""
Finální test nastavení pro brona.klus@gmail.com
"""

import os
import sys
import django

# Setup Django
sys.path.append('c:\\Users\\Administrator\\Documents\\work\\scaleup\\scb_ai_refactor')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserRole, CompanyProfile
from coaching.models import Coach
from accounts.permissions import is_coach

print('🔍 FINÁLNÍ KONTROLA NASTAVENÍ')
print('=' * 50)

try:
    brona_user = User.objects.get(username='brona.klus@gmail.com')
    print(f'✅ Uživatel: {brona_user.username}')
    
    # Kontrola UserRole
    try:
        role = UserRole.objects.get(user=brona_user)
        print(f'✅ UserRole: {role.role}')
    except UserRole.DoesNotExist:
        print('❌ UserRole neexistuje')
    
    # Kontrola Coach profilu
    try:
        coach = Coach.objects.get(user=brona_user)
        print(f'✅ Coach profil: {coach.specialization}')
    except Coach.DoesNotExist:
        print('❌ Coach profil neexistuje')
    
    # Kontrola is_coach funkce
    print(f'✅ is_coach() result: {is_coach(brona_user)}')
    
    # Přiřazení klienti
    assigned_clients = CompanyProfile.objects.filter(assigned_coach__user=brona_user)
    print(f'✅ Přiřazení klienti ({assigned_clients.count()}):')
    for client in assigned_clients:
        print(f'   - {client.company_name} ({client.user.username})')

except User.DoesNotExist:
    print('❌ Uživatel brona.klus@gmail.com nebyl nalezen')

print('\n🎯 INSTRUKCE PRO PŘIHLÁŠENÍ:')
print('1. Jděte na: http://127.0.0.1:8000/accounts/login/')
print('2. Přihlaste se jako: brona.klus@gmail.com')
print('3. V navigaci by se mělo zobrazit: 🎯 Moji klienti')
print('4. Kliknutím přejdete na coach dashboard')