# PostgreSQL Migration Guide - Scaling Up Platform

## Datum: 2025-12-06
## Branch: main

---

## Přehled

Tento dokument popisuje migraci z SQLite na PostgreSQL (Supabase) pro produkční prostředí.

### Současný stav
- **Lokální vývoj (Windows)**: SQLite (`db.sqlite3`)
- **Produkce (PythonAnywhere)**: Připraveno pro PostgreSQL (Supabase)
- **Zálohy**: Vytvořeny před migrací

---

## Architektura

### Lokální vývoj (Windows)
```
USE_POSTGRES=False (v .env)
↓
Django používá SQLite
└── db.sqlite3
```

### Produkce (PythonAnywhere/Server)
```
USE_POSTGRES=True (v .env)
↓
Django používá PostgreSQL
└── Supabase: ovenbpznaoroqcxydvxa.supabase.co
```

---

## Konfigurace

### 1. Environment Variables (.env)

```bash
# Database Selection
USE_POSTGRES=False  # False pro lokální vývoj, True pro produkci

# Supabase PostgreSQL Database
DB_NAME=postgres
DB_USER=postgres.ovenbpznaoroqcxydvxa
DB_PASSWORD=vicepenezmenecasu
DB_HOST=db.ovenbpznaoroqcxydvxa.supabase.co
DB_PORT=5432

# Supabase API
SUPABASE_URL=https://ovenbpznaoroqcxydvxa.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...

# SQLAlchemy Database URL (pro RAG systém)
DATABASE_URL=postgresql://postgres.ovenbpznaoroqcxydvxa:vicepenezmenecasu@db.ovenbpznaoroqcxydvxa.supabase.co:5432/postgres
```

### 2. settings.py

```python
USE_POSTGRES = os.getenv("USE_POSTGRES", "False") == "True"

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "postgres"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {
                "sslmode": "require",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
```

---

## Migrace na PythonAnywhere

### Krok 1: Příprava

Na lokálním stroji:

```bash
# Ujisti se, že máš zálohy
ls -lh backup_*.json db.sqlite3.backup_*

# Uploaduj zálohy na PythonAnywhere
# (přes Files tab nebo scp)
```

### Krok 2: PythonAnywhere Environment Setup

V PythonAnywhere Bash console:

```bash
cd ~/scaleupboard

# Instalace závislostí
pip install --user psycopg2-binary sqlalchemy pgvector

# Vytvoř .env soubor
nano .env
```

Obsah `.env` na PythonAnywhere:

```bash
# DŮLEŽITÉ: Nastav na True pro produkci!
USE_POSTGRES=True

# Supabase credentials
DB_NAME=postgres
DB_USER=postgres.ovenbpznaoroqcxydvxa
DB_PASSWORD=vicepenezmenecasu
DB_HOST=db.ovenbpznaoroqcxydvxa.supabase.co
DB_PORT=5432

SUPABASE_URL=https://ovenbpznaoroqcxydvxa.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im92ZW5icHpuYW9yb3FjeHlkdnhhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwMzcxOTksImV4cCI6MjA4MDYxMzE5OX0.IUM1J3MHcywhSyTSexBZROB2gDtU2sikL24L7qPgQ3I

DATABASE_URL=postgresql://postgres.ovenbpznaoroqcxydvxa:vicepenezmenecasu@db.ovenbpznaoroqcxydvxa.supabase.co:5432/postgres

# API Keys
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Krok 3: Test připojení

```bash
python manage.py check --database default
```

Očekávaný výstup:
```
System check identified no issues (0 silenced).
```

### Krok 4: Migrace schématu

```bash
# Vytvoř tabulky v PostgreSQL
python manage.py migrate
```

### Krok 5: Import dat

```bash
# Import dat ze záloh (po aplikacích)
python manage.py loaddata backup_auth.json
python manage.py loaddata backup_accounts.json
python manage.py loaddata backup_survey.json
python manage.py loaddata backup_suropen.json
python manage.py loaddata backup_chatbot.json
python manage.py loaddata backup_coaching.json
python manage.py loaddata backup_intercom.json
python manage.py loaddata backup_ingest.json
python manage.py loaddata backup_exports.json
```

**Poznámka:** Pokud nastane chyba s foreign keys, použij:
```bash
python manage.py loaddata backup_full.json --ignorenonexistent
```

### Krok 6: Ověření dat

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from accounts.models import CompanyProfile
from survey.models import Response

# Zkontroluj počty
print(f"Users: {User.objects.count()}")
print(f"Companies: {CompanyProfile.objects.count()}")
print(f"Survey responses: {Response.objects.count()}")
```

### Krok 7: Restart Web App

Na PythonAnywhere:
1. Jdi na **Web** tab
2. Klikni na **Reload bodichek.pythonanywhere.com**
3. Otestuj přihlášení a základní funkce

---

## Automatický Migrační Script

Vytvoř soubor `migrate_to_postgres.py`:

```python
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
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✓ PostgreSQL připojeno: {version}")
            return True
    except Exception as e:
        print(f"✗ Chyba připojení: {e}")
        return False

def migrate_schema():
    """Vytvoří schéma v PostgreSQL"""
    print("\nMigrace schématu...")
    try:
        management.call_command('migrate', verbosity=2)
        print("✓ Schéma vytvořeno")
        return True
    except Exception as e:
        print(f"✗ Chyba migrace: {e}")
        return False

def import_data():
    """Importuje data ze záloh"""
    print("\nImport dat...")

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

    for app in apps:
        try:
            filename = f'backup_{app}.json'
            if os.path.exists(filename):
                print(f"  Importing {app}...")
                management.call_command('loaddata', filename, verbosity=0)
                print(f"  ✓ {app}")
            else:
                print(f"  ⚠ {filename} not found, skipping")
        except Exception as e:
            print(f"  ✗ Error importing {app}: {e}")

    print("✓ Data importována")

def verify_data():
    """Ověří importovaná data"""
    print("\nOvěření dat...")

    from django.contrib.auth.models import User
    from accounts.models import CompanyProfile
    from survey.models import Response
    from coaching.models import Coach

    stats = {
        'Users': User.objects.count(),
        'Companies': CompanyProfile.objects.count(),
        'Survey Responses': Response.objects.count(),
        'Coaches': Coach.objects.count(),
    }

    for name, count in stats.items():
        print(f"  {name}: {count}")

    print("✓ Ověření dokončeno")

def main():
    print("=" * 60)
    print("PostgreSQL Migration Script")
    print("=" * 60)

    # Check environment
    use_postgres = os.getenv("USE_POSTGRES", "False")
    if use_postgres != "True":
        print("⚠ USE_POSTGRES není nastaveno na True!")
        print("Nastav USE_POSTGRES=True v .env a spusť znovu.")
        sys.exit(1)

    # Execute migration
    if not check_postgres_connection():
        sys.exit(1)

    if not migrate_schema():
        sys.exit(1)

    import_data()
    verify_data()

    print("\n" + "=" * 60)
    print("✓ Migrace dokončena úspěšně!")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

Použití:
```bash
python migrate_to_postgres.py
```

---

## Rollback plán

Pokud migrace selže:

### 1. Vrácení na SQLite

```bash
# V .env nastav:
USE_POSTGRES=False

# Restart web app
```

### 2. Obnovení zálohy

```bash
cp db.sqlite3.backup_20251206 db.sqlite3
```

---

## Troubleshooting

### Problém: "could not translate host name"

**Příčina:** DNS problém, firewall, nebo špatný hostname

**Řešení:**
1. Zkontroluj hostname v Supabase dashboard
2. Zkus ping: `ping db.ovenbpznaoroqcxydvxa.supabase.co`
3. Použij direct connection místo pooler
4. Kontaktuj Supabase support

### Problém: "permission denied"

**Příčina:** Špatné credentials

**Řešení:**
1. Zkontroluj username: `postgres.ovenbpznaoroqcxydvxa`
2. Zkontroluj heslo v .env
3. Reset hesla v Supabase dashboard

### Problém: "relation does not exist"

**Příčina:** Tabulky nebyly vytvořeny

**Řešení:**
```bash
python manage.py migrate --run-syncdb
```

### Problém: "IntegrityError" při importu

**Příčina:** Foreign key constraints

**Řešení:**
```bash
# Import s ignorem
python manage.py loaddata backup_full.json --ignorenonexistent

# Nebo manuálně po aplikacích ve správném pořadí
```

---

## Monitoring

### Kontrola zdraví databáze

```python
from django.db import connection

with connection.cursor() as cursor:
    # Počet připojení
    cursor.execute("SELECT count(*) FROM pg_stat_activity;")
    print(f"Active connections: {cursor.fetchone()[0]}")

    # Velikost databáze
    cursor.execute("SELECT pg_size_pretty(pg_database_size('postgres'));")
    print(f"Database size: {cursor.fetchone()[0]}")

    # Tabulky
    cursor.execute("""
        SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 10;
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}.{row[1]}: {row[2]}")
```

---

## Další kroky (FÁZE 2)

Po úspěšné migraci na PostgreSQL:

1. **RAG Systém** - Implementace vektorového vyhledávání s pgvector
2. **Chatbot s RAG** - Vylepšení chatbotu s kontextem z dat
3. **Sentiment Analýza** - Analýza nálady uživatelů
4. **Dashboard Views** - Coach/Client přepínání
5. **Vizuální redesign** - Moderní UI

---

## Kontakt

Dokumentace vytvořena: 2025-12-06
Projekt: Scaling Up Client Intelligence Platform
Verze: 2.0 (PostgreSQL Ready)
