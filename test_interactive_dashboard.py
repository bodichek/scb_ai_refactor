#!/usr/bin/env python
"""
Test interaktivního coach dashboardu
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.test import Client, TestCase
from django.contrib.auth.models import User
from accounts.models import UserRole, CompanyProfile
from coaching.models import Coach, UserCoachAssignment
import json


def test_interactive_dashboard():
    print("=== Test interaktivního coach dashboardu ===\n")
    
    # Simulace HTTP klienta
    client = Client()
    
    # 1. Test přihlášení kouče
    try:
        brona_user = User.objects.get(username='brona.klus@gmail.com')
        login_success = client.force_login(brona_user)
        print("✅ Coach úspěšně přihlášen")
    except User.DoesNotExist:
        print("❌ Coach brona.klus@gmail.com nenalezen")
        return
    
    # 2. Test hlavní stránky dashboardu
    response = client.get('/coaching/my-clients/')
    if response.status_code == 200:
        print("✅ Hlavní dashboard se načetl úspěšně")
        print(f"   Status code: {response.status_code}")
    else:
        print(f"❌ Chyba při načítání dashboardu: {response.status_code}")
        return
    
    # 3. Test že template obsahuje potřebné elementy
    content = response.content.decode('utf-8')
    required_elements = [
        'client-selector',
        'overview-tab',
        'documents-tab',
        'cashflow-tab',
        'charts-tab',
        'surveys-tab',
        'suropen-tab',
        'notes-tab'
    ]
    
    for element in required_elements:
        if element in content:
            print(f"✅ Template obsahuje: {element}")
        else:
            print(f"❌ Template neobsahuje: {element}")
    
    # 4. Test AJAX endpointů pro každého přiřazeného klienta
    coach = Coach.objects.get(user=brona_user)
    assignments = UserCoachAssignment.objects.filter(coach=coach)
    
    print(f"\n=== Test AJAX endpointů pro {assignments.count()} klientů ===")
    
    for assignment in assignments:
        client_id = assignment.client.id
        client_name = assignment.client.username
        
        print(f"\n🔍 Test klienta: {client_name} (ID: {client_id})")
        
        # Test client_data endpoint
        response = client.get(f'/coaching/client/{client_id}/data/')
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                if data.get('success'):
                    print("  ✅ client_data endpoint funguje")
                else:
                    print("  ❌ client_data endpoint vrátil chybu")
            except json.JSONDecodeError:
                print("  ❌ client_data endpoint nevrátil platný JSON")
        else:
            print(f"  ❌ client_data endpoint chyba: {response.status_code}")
        
        # Test documents-data endpoint
        response = client.get(f'/coaching/client/{client_id}/documents-data/')
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                if data.get('success'):
                    print("  ✅ documents-data endpoint funguje")
                else:
                    print("  ❌ documents-data endpoint vrátil chybu")
            except json.JSONDecodeError:
                print("  ❌ documents-data endpoint nevrátil platný JSON")
        else:
            print(f"  ❌ documents-data endpoint chyba: {response.status_code}")
        
        # Test cashflow-data endpoint
        response = client.get(f'/coaching/client/{client_id}/cashflow-data/')
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                if data.get('success'):
                    print("  ✅ cashflow-data endpoint funguje")
                else:
                    print("  ❌ cashflow-data endpoint vrátil chybu")
            except json.JSONDecodeError:
                print("  ❌ cashflow-data endpoint nevrátil platný JSON")
        else:
            print(f"  ❌ cashflow-data endpoint chyba: {response.status_code}")
        
        # Test charts-data endpoint
        response = client.get(f'/coaching/client/{client_id}/charts-data/')
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                if data.get('success'):
                    print("  ✅ charts-data endpoint funguje")
                else:
                    print("  ❌ charts-data endpoint vrátil chybu")
            except json.JSONDecodeError:
                print("  ❌ charts-data endpoint nevrátil platný JSON")
        else:
            print(f"  ❌ charts-data endpoint chyba: {response.status_code}")
        
        # Test surveys-data endpoint
        response = client.get(f'/coaching/client/{client_id}/surveys-data/')
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                if data.get('success'):
                    print("  ✅ surveys-data endpoint funguje")
                else:
                    print("  ❌ surveys-data endpoint vrátil chybu")
            except json.JSONDecodeError:
                print("  ❌ surveys-data endpoint nevrátil platný JSON")
        else:
            print(f"  ❌ surveys-data endpoint chyba: {response.status_code}")
        
        # Test suropen-data endpoint
        response = client.get(f'/coaching/client/{client_id}/suropen-data/')
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                if data.get('success'):
                    print("  ✅ suropen-data endpoint funguje")
                else:
                    print("  ❌ suropen-data endpoint vrátil chybu")
            except json.JSONDecodeError:
                print("  ❌ suropen-data endpoint nevrátil platný JSON")
        else:
            print(f"  ❌ suropen-data endpoint chyba: {response.status_code}")
        
        # Test notes endpoint (POST)
        response = client.post(f'/coaching/client/{client_id}/notes/', 
                              json.dumps({'notes': 'Test poznámka'}),
                              content_type='application/json')
        if response.status_code == 200:
            try:
                data = json.loads(response.content)
                if data.get('success'):
                    print("  ✅ notes endpoint funguje")
                else:
                    print("  ❌ notes endpoint vrátil chybu")
            except json.JSONDecodeError:
                print("  ❌ notes endpoint nevrátil platný JSON")
        else:
            print(f"  ❌ notes endpoint chyba: {response.status_code}")
    
    # 5. Test starého dashboardu (backup)
    response = client.get('/coaching/my-clients-old/')
    if response.status_code == 200:
        print("\n✅ Starý dashboard (backup) je dostupný")
    else:
        print(f"\n❌ Starý dashboard nedostupný: {response.status_code}")
    
    print("\n" + "="*50)
    print("🎉 Test dokončen!")
    print("📝 Doporučení:")
    print("   1. Otevřete http://127.0.0.1:8000/coaching/my-clients/")
    print("   2. Vyberte klienta ze seznamu vlevo")
    print("   3. Vyzkoušejte všechny taby")
    print("   4. Napište poznámku a zkuste ji uložit")
    print("="*50)


if __name__ == '__main__':
    test_interactive_dashboard()