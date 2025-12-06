# Deployment Guide - Oddělení Development a Production Prostředí

## 📋 Přehled

Projekt používá **dva samostatné Supabase projekty** pro oddělení vývojových a produkčních dat:

- **Local Development** → `.env.local` → Development Supabase projekt
- **Production (PythonAnywhere)** → `.env.production` → Production Supabase projekt

## 🏗️ Setup pro Lokální Vývoj

### 1. Vytvoření Development Supabase projektu

1. Přihlaste se na [supabase.com](https://supabase.com)
2. Klikněte na **"New Project"**
3. Vyplňte údaje:
   - **Name**: `scaleupboard-dev` (nebo jiný název)
   - **Database Password**: Zvolte silné heslo
   - **Region**: `Europe (eu-central-1)` nebo `Europe West (eu-west-1)`
4. Klikněte **"Create new project"**
5. Počkejte 2-3 minuty na inicializaci

### 2. Získání Development Credentials

V Supabase dashboardu DEV projektu:

#### A) Database Connection
**Project Settings** → **Database** → **Connection Pooling**

Zkopírujte:
- **Host**: `aws-0-eu-central-1.pooler.supabase.com`
- **Database**: `postgres`
- **Port**: `6543` (Transaction mode)
- **User**: `postgres.xxxxxxxxxx`
- **Password**: Vaše zvolené heslo

#### B) API Credentials
**Project Settings** → **API**

Zkopírujte:
- **Project URL**: `https://xxxxxxxxxx.supabase.co`
- **anon/public key**: `eyJhbGc...`

### 3. Vyplnění `.env.local`

Otevřete soubor `.env.local` a vyplňte hodnoty z DEV projektu:

```env
# Development Database (Transaction Pooler - Port 6543)
DB_NAME=postgres
DB_USER=postgres.xxxxxxxxxx  # Z Connection Pooling
DB_PASSWORD=vase_heslo       # Vaše zvolené heslo
DB_HOST=aws-0-eu-central-1.pooler.supabase.com  # Z Connection Pooling
DB_PORT=6543

# Development Supabase API
SUPABASE_URL=https://xxxxxxxxxx.supabase.co  # Project URL
SUPABASE_ANON_KEY=eyJhbGc...  # anon/public key

# SQLAlchemy Database URL
DATABASE_URL=postgresql://postgres.xxxxxxxxxx:vase_heslo@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

### 4. Inicializace Development databáze

```bash
# Aplikujte migrace na DEV databázi
python manage.py migrate

# Vytvořte admin uživatele pro DEV
python manage.py createsuperuser

# (Volitelně) Naplňte testovacími daty
python manage.py loaddata fixtures/test_data.json
```

### 5. Spuštění lokálního serveru

```bash
# Automaticky načte .env.local
python manage.py runserver
```

Měli byste vidět:
```
💻 Loading LOCAL development environment from C:\...\scaleupboard\.env.local
```

## 🚀 Deployment na PythonAnywhere (Production)

### 1. Upload `.env.production` na server

```bash
# Na PythonAnywhere v Bash console
cd ~/scaleupboard
nano .env.production
# Vložte obsah .env.production a uložte (Ctrl+X, Y, Enter)
```

### 2. Nastavení environment proměnné

V souboru `wsgi.py` na PythonAnywhere:

```python
import os
os.environ['DJANGO_ENV'] = 'production'  # Přidejte PŘED importem aplikace

# Nebo přidejte do .bashrc:
export DJANGO_ENV=production
```

### 3. Restart aplikace

V PythonAnywhere **Web** tab → **Reload** tlačítko

Server by měl načíst produkční konfiguraci:
```
🚀 Loading PRODUCTION environment from /home/bodichek/scaleupboard/.env.production
```

## 🔒 Bezpečnost

### Co je v .gitignore (NEBUDE commitováno)
✅ `.env.local` - development credentials
✅ `.env.production` - production credentials
✅ `.env` - defaultní env soubor

### Co MŮŽETE commitovat
✅ `settings.py` - konfigurační logika (bez credentials)
✅ `DEPLOYMENT.md` - tento návod
✅ `requirements.txt` - dependencies

## 🧪 Testování Prostředí

### Ověření, které prostředí je načteno:

```python
# V Django shell
python manage.py shell

from django.conf import settings
import os

# Zkontrolujte DB host
print(f"DB Host: {settings.DATABASES['default']['HOST']}")

# Zkontrolujte environment
print(f"Environment: {os.getenv('DJANGO_ENV', 'local')}")
```

**Development** by měl ukázat:
```
DB Host: aws-0-eu-central-1.pooler.supabase.com (nový DEV projekt)
Environment: local
```

**Production** by měl ukázat:
```
DB Host: aws-1-eu-west-1.pooler.supabase.com (stávající PROD projekt)
Environment: production
```

## 📊 Kontrola dat

### Zkontrolujte, že píšete do správné databáze:

```bash
# Lokálně (DEV)
python manage.py dbshell
\dt  # Seznam tabulek DEV databáze
SELECT COUNT(*) FROM ingest_document;  # Počet dokumentů v DEV
\q

# Na PythonAnywhere (PROD)
python manage.py dbshell
SELECT COUNT(*) FROM ingest_document;  # Počet dokumentů v PROD
```

Čísla by měla být **ROZDÍLNÁ** - to potvrzuje oddělené databáze.

## 🛠️ Troubleshooting

### ❌ Stále se připojuji k produkční databázi lokálně

1. Zkontrolujte, že `.env.local` existuje a je vyplněný
2. Zkontrolujte konzoli při spuštění serveru - měli byste vidět:
   ```
   💻 Loading LOCAL development environment from ...
   ```
3. Restartujte development server

### ❌ PythonAnywhere se připojuje k DEV databázi

1. Zkontrolujte, že je nastaveno `DJANGO_ENV=production`
2. Zkontrolujte error log v PythonAnywhere → Web → Log files
3. Ujistěte se, že `.env.production` existuje na serveru

### ❌ Migrace selžou

```bash
# Zkontrolujte připojení
python manage.py check --database default

# Ověřte credentials
python manage.py dbshell
```

## 📚 Další kroky

1. ✅ Vytvořte DEV Supabase projekt
2. ✅ Vyplňte `.env.local`
3. ✅ Spusťte migrace na DEV databázi
4. ✅ Otestujte lokální vývoj
5. ✅ Nahrajte `.env.production` na PythonAnywhere
6. ✅ Nastavte `DJANGO_ENV=production` na serveru
7. ✅ Restartujte PythonAnywhere aplikaci

## 🎯 Výhody tohoto řešení

✅ **Oddělená data**: DEV a PROD databáze jsou kompletně separované
✅ **Bezpečnost**: Žádné credentials v git repository
✅ **Automatické**: Správný .env se načte podle prostředí
✅ **Jednoduché**: Přepnutí přes `DJANGO_ENV` proměnnou
✅ **Škálovatelné**: Můžete přidat staging, testing, atd.
