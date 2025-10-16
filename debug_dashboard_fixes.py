#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from accounts.models import Coach, CompanyProfile
import json

print("=== DEBUGGING COACH DASHBOARD ===")

# 1. Najdeme všechny coaches a jejich klienty
coaches = Coach.objects.all()
print(f"Celkem koučů: {coaches.count()}")

for coach in coaches:
    print(f"\nKouč: {coach.user.email} (ID: {coach.id})")
    clients = CompanyProfile.objects.filter(assigned_coach=coach)
    print(f"  Klientů: {clients.count()}")
    
    for client in clients:
        print(f"    - {client.company_name} (ID: {client.id}, User: {client.user.email})")

# 2. Testujeme AJAX endpoint přímo
print(f"\n=== TESTOVÁNÍ AJAX ENDPOINT ===")

# Vytvoříme test client
client_test = Client()

# Najdeme prvního kouče s klienty
coach_with_clients = None
test_client_id = None

for coach in coaches:
    clients = CompanyProfile.objects.filter(assigned_coach=coach)
    if clients.exists():
        coach_with_clients = coach
        test_client_id = clients.first().id
        break

if coach_with_clients and test_client_id:
    print(f"Testujeme kouče: {coach_with_clients.user.email}")
    print(f"S klientem ID: {test_client_id}")
    
    # Přihlásíme kouče
    client_test.force_login(coach_with_clients.user)
    
    # Testujeme AJAX endpoint
    response = client_test.get(f'/coaching/client/{test_client_id}/', 
                              HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.items())}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"JSON data keys: {list(data.keys())}")
            print(f"Client name: {data.get('client', {}).get('company_name', 'N/A')}")
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw response: {response.content[:200]}...")
    else:
        print(f"Error response: {response.content}")
else:
    print("Žádný kouč s klienty nenalezen!")

print("\n=== KONEC DEBUGGINGU ===")