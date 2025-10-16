#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from coaching.models import Coach
from accounts.models import CompanyProfile

print("=== Kontrola coach a klient dat ===")

# Najdeme coach@example.com
try:
    coach_user = User.objects.get(email='coach@example.com')
    print(f'✅ Coach user found: {coach_user.username} ({coach_user.email})')
    
    try:
        coach = Coach.objects.get(user=coach_user)
        print(f'✅ Coach profile found: {coach}')
        
        # Najdeme přiřazené klienty
        clients = CompanyProfile.objects.filter(assigned_coach=coach)
        print(f'📋 Assigned clients: {clients.count()}')
        
        for client in clients:
            print(f'  - {client.company_name} ({client.user.email})')
            
    except Coach.DoesNotExist:
        print('❌ Coach profile not found - creating...')
        coach = Coach.objects.create(user=coach_user, specialization='Finanční poradenství')
        print(f'✅ Coach profile created: {coach}')
        
except User.DoesNotExist:
    print('❌ Coach user not found')

print()

# Najdeme brona.kus@gmail.com  
try:
    client_user = User.objects.get(email='brona.kus@gmail.com')
    print(f'✅ Client user found: {client_user.username} ({client_user.email})')
    
    try:
        profile = CompanyProfile.objects.get(user=client_user)
        print(f'✅ Client profile: {profile.company_name}')
        print(f'👤 Assigned coach: {profile.assigned_coach}')
        
        # Pokud není přiřazen kouč, přiřadíme ho
        if not profile.assigned_coach and 'coach' in locals():
            profile.assigned_coach = coach
            profile.save()
            print(f'✅ Coach assigned to client!')
            
    except CompanyProfile.DoesNotExist:
        print('❌ Client profile not found')
        
except User.DoesNotExist:
    print('❌ Client user not found')

print("\n=== Všichni uživatelé ===")
for user in User.objects.all():
    print(f"- {user.username} ({user.email})")