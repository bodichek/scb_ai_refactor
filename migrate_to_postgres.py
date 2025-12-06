#!/usr/bin/env python
"""
Migrační script pro přechod z SQLite na PostgreSQL
Použití: python migrate_to_postgres.py
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.core import management
from django.db import connection


def check_postgres_connection():
    """Zkontroluje připojení k PostgreSQL"""
    print("\n1. Kontrola připojení k PostgreSQL...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"   OK PostgreSQL připojeno: {version[:50]}...")
            return True
    except Exception as e:
        print(f"   ERROR Chyba připojení: {e}")
        return False


def migrate_schema():
    """Vytvoří schéma v PostgreSQL"""
    print("\n2. Migrace schématu...")
    try:
        management.call_command('migrate', verbosity=1)
        print("   OK Schéma vytvořeno")
        return True
    except Exception as e:
        print(f"   ERROR Chyba migrace: {e}")
        return False


def import_data():
    """Importuje data ze záloh"""
    print("\n3. Import dat...")

    apps = [
        'auth',
        'accounts',
        'survey',
        'suropen',
        'chatbot',
        'coaching',
        'intercom',
        'ingest',
        'exports'
    ]

    success_count = 0
    for app in apps:
        try:
            filename = f'backup_{app}.json'
            if os.path.exists(filename):
                print(f"   Importing {app}...", end=' ')
                management.call_command('loaddata', filename, verbosity=0)
                print("OK")
                success_count += 1
            else:
                print(f"   WARNING {filename} not found, skipping")
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\n   OK Importováno {success_count}/{len(apps)} aplikací")
    return success_count > 0


def verify_data():
    """Ověří importovaná data"""
    print("\n4. Ověření dat...")

    from django.contrib.auth.models import User
    from accounts.models import CompanyProfile
    from survey.models import Response
    from coaching.models import Coach
    from ingest.models import Document

    stats = {
        'Users': User.objects.count(),
        'Companies': CompanyProfile.objects.count(),
        'Survey Responses': Response.objects.count(),
        'Coaches': Coach.objects.count(),
        'Documents': Document.objects.count(),
    }

    for name, count in stats.items():
        print(f"   {name}: {count}")

    print("   OK Ověření dokončeno")
    return True


def main():
    print("=" * 70)
    print(" PostgreSQL Migration Script - Scaling Up Platform")
    print("=" * 70)

    # Check that we have database credentials
    if not os.getenv("DB_HOST") or not os.getenv("DB_PASSWORD"):
        print("\nERROR: Database credentials not found in .env!")
        print("Make sure DB_HOST, DB_USER, DB_PASSWORD are set.")
        sys.exit(1)

    # Execute migration steps
    steps = [
        ("Kontrola připojení", check_postgres_connection),
        ("Migrace schématu", migrate_schema),
        ("Import dat", import_data),
        ("Ověření dat", verify_data),
    ]

    for step_name, step_func in steps:
        if not step_func():
            print(f"\n{'='*70}")
            print(f" ERROR: Krok '{step_name}' selhal!")
            print("=" * 70)
            sys.exit(1)

    print("\n" + "=" * 70)
    print(" SUCCESS: Migrace dokončena úspěšně!")
    print("=" * 70)
    print("\nDalší kroky:")
    print("1. Zkontroluj web aplikaci (přihlášení, dashboard)")
    print("2. Otestuj všechny funkce (upload dokumentů, survey, chatbot)")
    print("3. Pokud vše funguje, smaž SQLite zálohu")


if __name__ == "__main__":
    main()
