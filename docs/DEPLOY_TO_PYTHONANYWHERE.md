# Deploy to PythonAnywhere - PostgreSQL Migration

## Datum: 2025-12-06
## Status: Ready to deploy

---

## ✅ MIGRACE ÚSPĚŠNÁ Z WINDOWS

**Update 2025-12-06 18:36 CET:** Migrace úspěšně dokončena z lokálního Windows prostředí!

**Řešení:** Použití Supabase Transaction Pooler endpoint:
- Host: `aws-1-eu-west-1.pooler.supabase.com`
- Port: `6543`
- Vyžaduje `DISABLE_SERVER_SIDE_CURSORS: True` v Django settings

---

## Příprava - Co máš připraveno

✅ Zálohy dat (backup_*.json)
✅ Migrační script (migrate_to_postgres.py)
✅ PostgreSQL konfigurace v settings.py
✅ Supabase credentials v .env
✅ pgvector aktivován v Supabase

---

## KROK 1: Upload souborů na PythonAnywhere

### 1.1 Přes Files tab

Nahraj tyto soubory do složky `/home/bodichek/scaleupboard/`:

**Zálohy:**
- `backup_auth.json`
- `backup_accounts.json`
- `backup_survey.json`
- `backup_suropen.json`
- `backup_chatbot.json`
- `backup_coaching.json`
- `backup_intercom.json`
- `backup_ingest.json`
- `backup_exports.json`

**Scripty:**
- `migrate_to_postgres.py`
- `backup_script.py`

**Konfigurace:**
- Aktualizovaný `app/settings.py`

### 1.2 Vytvoř .env soubor

V PythonAnywhere Bash console:

```bash
cd ~/scaleupboard
nano .env
```

Zkopíruj obsah:

```bash
# OpenAI API
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_API_SECRET=your-secret-here

# Anthropic API (Claude Vision)
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Supabase PostgreSQL Database (Transaction Pooler - WORKING!)
DB_NAME=postgres
DB_USER=postgres.your-project-id
DB_PASSWORD=your-database-password
DB_HOST=aws-1-eu-west-1.pooler.supabase.com
DB_PORT=6543

# Supabase API
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key

# SQLAlchemy Database URL (pro RAG systém)
DATABASE_URL=postgresql://postgres.your-project-id:your-password@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

**POZNÁMKA:** Nahraď placeholder hodnoty skutečnými credentials z lokálního `.env` souboru (který není verzován v Gitu).

Ulož: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## KROK 2: Instalace závislostí

V PythonAnywhere Bash console:

```bash
cd ~/scaleupboard

# Instalace PostgreSQL závislostí
pip install --user psycopg2-binary sqlalchemy pgvector

# Ověření instalace
pip list | grep -E 'psycopg2|sqlalchemy|pgvector'
```

Očekávaný výstup:
```
pgvector          0.4.2
psycopg2-binary   2.9.11
sqlalchemy        2.0.44
```

---

## KROK 3: Test připojení

```bash
cd ~/scaleupboard

# Test Django připojení
python manage.py check --database default
```

Očekávaný výstup:
```
System check identified no issues (0 silenced).
```

Pokud vidíš chyby:
- Zkontroluj `.env` soubor (správné credentials)
- Zkontroluj, že PythonAnywhere má přístup k internetu
- Zkus `ping aws-0-eu-central-1.svc.supabase.com`

---

## KROK 4: Spuštění migrace

```bash
cd ~/scaleupboard

# Spusť automatický migrační script
python migrate_to_postgres.py
```

**Script provede:**
1. ✓ Kontrolu připojení k PostgreSQL
2. ✓ Vytvoření schématu (migrate)
3. ✓ Import dat ze záloh
4. ✓ Ověření dat

**Očekávaný výstup:**
```
======================================================================
 PostgreSQL Migration Script - Scaling Up Platform
======================================================================

1. Kontrola připojení k PostgreSQL...
   OK PostgreSQL připojeno: PostgreSQL 15.x ...

2. Migrace schématu...
   Running migrations:
   ...
   OK Schéma vytvořeno

3. Import dat...
   Importing auth... OK
   Importing accounts... OK
   Importing survey... OK
   Importing suropen... OK
   Importing chatbot... OK
   Importing coaching... OK
   Importing intercom... OK
   Importing ingest... OK
   Importing exports... OK

   OK Importováno 9/9 aplikací

4. Ověření dat...
   Users: 6
   Companies: 4
   Survey Responses: 112
   Coaches: 2
   Documents: 87
   OK Ověření dokončeno

======================================================================
 SUCCESS: Migrace dokončena úspěšně!
======================================================================
```

---

## KROK 5: Reload Web App

1. Jdi na **Web** tab
2. Najdi sekci **Reload bodichek.pythonanywhere.com**
3. Klikni na zelené tlačítko **Reload**
4. Počkej ~10 sekund

---

## KROK 6: Testování funkčnosti

### 6.1 Test přihlášení

1. Jdi na: `https://bodichek.pythonanywhere.com/accounts/login/`
2. Přihlaš se s existujícím uživatelem
3. Měl bys být přesměrován na dashboard

### 6.2 Test dashboardu

1. Dashboard se načte
2. Vidíš data (companies, survey responses)
3. Grafy se zobrazují

### 6.3 Test coach dashboardu

1. Přihlaš se jako coach
2. Jdi na `/coaching/my-clients/`
3. Vidíš seznam klientů
4. Klikni na detail klienta

### 6.4 Test upload dokumentů

1. Zkus nahrát dokument
2. Ověř, že se uložil do PostgreSQL
3. Zkontroluj parsing

### 6.5 Test survey

1. Vyplň nový dotazník
2. Ověř, že odpovědi jsou uloženy
3. Zkontroluj AI response

### 6.6 Test chatbotu

1. Otevři chatbot
2. Pošli zprávu
3. Ověř odpověď

---

## KROK 7: Monitoring v Supabase

1. Jdi na: `https://ovenbpznaoroqcxydvxa.supabase.co`
2. **Table Editor** → Vidíš nové tabulky
3. **Database** → **Roles** → Zkontroluj připojení
4. **Logs** → Query logs

---

## Rollback plán (pokud něco selže)

### Varianta A: Dočasný návrat na SQLite

1. V `app/settings.py` změň:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

2. Reload web app
3. Data zůstanou v SQLite záloze

### Varianta B: Opakování migrace

```bash
# Smaž PostgreSQL data
# V Supabase SQL Editor:
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

# Opakuj migraci
python migrate_to_postgres.py
```

---

## Troubleshooting

### Chyba: "could not translate host name"

**Příčina:** Špatný hostname nebo DNS problém

**Řešení:**
```bash
# Test DNS
nslookup aws-0-eu-central-1.svc.supabase.com

# Zkus ping
ping aws-0-eu-central-1.svc.supabase.com

# Zkontroluj .env
cat .env | grep DB_HOST
```

### Chyba: "password authentication failed"

**Příčina:** Špatné credentials

**Řešení:**
1. Zkontroluj heslo v `.env`
2. Zkontroluj username: `postgres.ovenbpznaoroqcxydvxa`
3. Reset hesla v Supabase dashboard

### Chyba: "relation does not exist"

**Příčina:** Migrace neproběhla

**Řešení:**
```bash
python manage.py migrate --run-syncdb
```

### Chyba: "IntegrityError" při importu

**Příčina:** Foreign key constraints

**Řešení:**
```bash
# Import v pořadí
python manage.py loaddata backup_auth.json
python manage.py loaddata backup_accounts.json
# ... atd.
```

---

## Po úspěšné migraci

### Co dělat:

1. ✅ Smaž SQLite zálohy (za týden)
2. ✅ Monitoruj výkon v Supabase
3. ✅ Pravidelně zálohuj PostgreSQL
4. ✅ Sleduj logy pro chyby

### Co NEDĚLAT:

- ❌ Nemazat zálohy hned
- ❌ Neměnit credentials bez zálohy
- ❌ Nepřeskakovat testy

---

## Další kroky (FÁZE 2)

Po úspěšné migraci pokračuj s:

1. **RAG Systém** - Implementace vektorového vyhledávání
2. **Chatbot s RAG** - Vylepšení s kontextem z dat
3. **Sentiment Analýza** - Analýza nálady
4. **Dashboard Views** - Coach/Client modes
5. **Vizuální Redesign** - Moderní UI

---

## Kontakt & Podpora

**Projekt:** Scaling Up Client Intelligence Platform
**Datum:** 2025-12-06
**Status:** Ready for deployment

**V případě problémů:**
- Zkontroluj logy v PythonAnywhere
- Zkontroluj Supabase logs
- Vrať se k dokumentaci POSTGRESQL_MIGRATION_GUIDE.md
