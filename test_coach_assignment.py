#!/usr/bin/env python
"""
Test script pro ověření nového systému přiřazování coach-client přes UserCoachAssignment
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserRole, CompanyProfile
from coaching.models import Coach, UserCoachAssignment
from accounts.permissions import can_coach_access_client, get_coach_clients


def test_coach_client_assignment():
    print("=== Test systému přiřazování coach-client ===\n")
    
    # 1. Najdi coach uživatele
    try:
        brona_user = User.objects.get(username='brona.klus@gmail.com')
        brona_coach = Coach.objects.get(user=brona_user)
        print(f"✅ Našel jsem kouče: {brona_user.username}")
    except (User.DoesNotExist, Coach.DoesNotExist) as e:
        print(f"❌ Coach brona.klus@gmail.com nenalezen: {e}")
        return

    # 2. Najdi nějaké company uživatele
    company_users = User.objects.filter(userrole__role='company')[:3]
    print(f"✅ Nalezeno {company_users.count()} company uživatelů")
    
    if company_users.count() == 0:
        print("❌ Žádní company uživatelé nenalezeni")
        return

    # 3. Vytvoř přiřazení coach-client
    for company_user in company_users:
        assignment, created = UserCoachAssignment.objects.get_or_create(
            coach=brona_coach,
            client=company_user,
            defaults={'notes': f'Automaticky přiřazen pro test - {company_user.username}'}
        )
        if created:
            print(f"✅ Vytvořeno přiřazení: {brona_coach} → {company_user.username}")
        else:
            print(f"ℹ️  Přiřazení už existuje: {brona_coach} → {company_user.username}")

    # 4. Test permissí
    print("\n=== Test oprávnění ===")
    assigned_clients = get_coach_clients(brona_user)
    print(f"✅ Coach má přiřazeno {assigned_clients.count()} klientů")
    
    for client in assigned_clients:
        has_access = can_coach_access_client(brona_user, client)
        print(f"{'✅' if has_access else '❌'} Přístup ke klientovi {client.username}: {has_access}")

    # 5. Test admin zobrazení
    print("\n=== Statistiky pro admin ===")
    total_assignments = UserCoachAssignment.objects.count()
    coaches_with_clients = Coach.objects.filter(usercoachassignment__isnull=False).distinct().count()
    print(f"✅ Celkem přiřazení: {total_assignments}")
    print(f"✅ Coaches s klienty: {coaches_with_clients}")

    # 6. Zobraz přiřazení
    print("\n=== Všechna přiřazení ===")
    assignments = UserCoachAssignment.objects.all().select_related('coach__user', 'client')
    for assignment in assignments:
        print(f"  {assignment.coach.user.username} → {assignment.client.username} (od {assignment.assigned_at})")

    print("\n✅ Test dokončen! Můžete testovat admin rozhraní a coach dashboard.")


if __name__ == '__main__':
    test_coach_client_assignment()