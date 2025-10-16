#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Coach, CompanyProfile

print("=== OPRAVA PŘIŘAZENÍ KLIENTA KOUČI ===")

# Najdeme kouče
coach_user = User.objects.get(username='coach@coach.com')
coach = Coach.objects.get(user=coach_user)
print(f"✅ Kouč nalezen: {coach.user.username}")

# Najdeme klienta
client_user = User.objects.get(username='brona.klus@gmail.com')
client_profile = CompanyProfile.objects.get(user=client_user)
print(f"✅ Klient nalezen: {client_profile.company_name} ({client_user.username})")

# Přiřadíme kouče klientovi
client_profile.assigned_coach = coach
client_profile.save()
print(f"✅ Klient přiřazen kouči!")

print(f"\n🎯 VÝSLEDEK:")
print(f"   Kouč: {coach.user.username}")
print(f"   Klient: {client_profile.company_name} ({client_user.username})")
print(f"   Přiřazen: {client_profile.assigned_coach.user.username}")

print("\n=== DOKONČENO ===")