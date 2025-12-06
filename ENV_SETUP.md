# 🔧 Rychlý návod - Oddělení Dev a Prod prostředí

## ✅ Co je hotovo

- ✅ **Automatické načítání správného .env** podle prostředí
- ✅ **`.env.local`** připraven pro development (vyžaduje vyplnění)
- ✅ **`.env.production`** obsahuje produkční credentials
- ✅ **`.gitignore`** aktualizován - credentials nejsou v gitu

## 🚀 Co musíte udělat

### 1️⃣ Vytvořit Development Supabase projekt

1. Jděte na https://supabase.com → **New Project**
2. Název: `scaleupboard-dev`
3. Region: **Europe West (eu-west-1)** nebo **Europe Central (eu-central-1)**
4. Zvolte silné heslo
5. Počkejte 2-3 minuty na inicializaci

### 2️⃣ Zkopírovat credentials z DEV projektu

V Supabase dashboardu **DEV projektu**:

#### A) Database Connection Pooling
**Settings → Database → Connection Pooling** (Transaction mode, Port 6543)

```
Host: aws-0-eu-central-1.pooler.supabase.com
Database: postgres
Port: 6543
User: postgres.xxxxxxxxxx
Password: [vaše heslo]
```

#### B) API Keys
**Settings → API**

```
Project URL: https://xxxxxxxxxx.supabase.co
anon/public: eyJhbGc...
```

### 3️⃣ Vyplnit `.env.local`

Otevřete soubor **`.env.local`** a nahraďte `XXXXXX`:

```env
DB_USER=postgres.xxxxxxxxxx  # Zkopírujte z Connection Pooling
DB_PASSWORD=vase_heslo       # Vaše heslo z DEV projektu
DB_HOST=aws-0-eu-central-1.pooler.supabase.com  # Z Connection Pooling
SUPABASE_URL=https://xxxxxxxxxx.supabase.co  # Project URL
SUPABASE_ANON_KEY=eyJhbGc...  # anon/public key
DATABASE_URL=postgresql://postgres.xxxxxxxxxx:vase_heslo@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

### 4️⃣ Inicializovat DEV databázi

```bash
# Aplikujte migrace
python manage.py migrate

# Vytvořte admin uživatele
python manage.py createsuperuser
```

### 5️⃣ Spustit lokální server

```bash
python manage.py runserver
```

Měli byste vidět:
```
[LOCAL DEV] Loading environment from C:\...\scaleupboard\.env.local
```

## ✅ Ověření

### Zkontrolujte DB připojení:

```bash
python manage.py dbshell
```

V PostgreSQL konzoli:
```sql
-- Zobrazit název databáze
SELECT current_database();

-- Měl by ukázat DEV projekt (ne ovenbpznaoroqcxydvxa)
```

## 🚀 Production (PythonAnywhere)

Na serveru nastavte environment proměnnou:

```bash
# V .bashrc nebo wsgi.py
export DJANGO_ENV=production
```

Server pak automaticky načte `.env.production` s produkčními credentials.

## 📊 Výsledek

**PŘED:**
- ❌ Local i PythonAnywhere → stejná databáze
- ❌ Testovací data zamořují produkci

**PO:**
- ✅ Local → DEV Supabase projekt
- ✅ PythonAnywhere → PROD Supabase projekt
- ✅ Oddělená data, bezpečné testování

## 🔍 Troubleshooting

### Pořád se připojuji k produkční DB lokálně

1. Zkontrolujte, že `.env.local` existuje a je vyplněný
2. Restart serveru
3. Zkontrolujte výstup: `[LOCAL DEV] Loading environment from...`

### Stále vidím "using fallback"

To znamená, že `.env.local` neexistuje nebo není vyplněný.
Zkopírujte a vyplňte credentials z nového DEV projektu.

---

📚 **Podrobný návod**: viz `DEPLOYMENT.md`
