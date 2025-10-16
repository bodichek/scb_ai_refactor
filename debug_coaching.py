#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Coach, CompanyProfile

print("=== DATABÁZE DEBUG ===")

print("\n1. VŠICHNI UŽIVATELÉ:")
users = User.objects.all()
for u in users:
    print(f"   ID: {u.id} | Username: {u.username} | Email: {u.email} | Jméno: {u.first_name} {u.last_name}")

print(f"\nCelkem uživatelů: {users.count()}")

print("\n2. VŠICHNI KOUČI:")
coaches = Coach.objects.all()
for c in coaches:
    print(f"   ID: {c.id} | User: {c.user.username} ({c.user.email}) | Specializace: {c.specialization}")

print(f"\nCelkem koučů: {coaches.count()}")

print("\n3. VŠECHNY FIREMNÍ PROFILY:")
profiles = CompanyProfile.objects.all()
for cp in profiles:
    assigned_text = cp.assigned_coach.user.username if cp.assigned_coach else "ŽÁDNÝ"
    print(f"   ID: {cp.id} | Firma: {cp.company_name} | User: {cp.user.username} ({cp.user.email}) | Kouč: {assigned_text}")

print(f"\nCelkem firemních profilů: {profiles.count()}")

print("\n4. KONTROLA PŘIŘAZENÍ:")
for coach in coaches:
    assigned_clients = CompanyProfile.objects.filter(assigned_coach=coach)
    print(f"   Kouč {coach.user.username} má {assigned_clients.count()} klientů:")
    for client in assigned_clients:
        print(f"     - {client.company_name} ({client.user.username})")

print("\n=== KONEC DEBUGU ===")