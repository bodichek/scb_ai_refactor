# ScaleUpBoard - AI-Powered Financial Analysis Platform

**Inteligentní platforma pro finanční analýzu českých společností s využitím AI vision parsingu a automatizovaného coachingu.**

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![Claude Sonnet 4](https://img.shields.io/badge/Claude-Sonnet%204-purple.svg)](https://www.anthropic.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

---

## 📋 Obsah

- [O projektu](#o-projektu)
- [Klíčové funkce](#klíčové-funkce)
- [Technologie](#technologie)
- [Rychlý start](#rychlý-start)
- [Architektura](#architektura)
- [Moduly aplikace](#moduly-aplikace)
- [AI Integration](#ai-integration)
- [API dokumentace](#api-dokumentace)
- [Deployment](#deployment)
- [Bezpečnost](#bezpečnost)
- [Contributing](#contributing)
- [Licence](#licence)

---

## 🎯 O projektu

ScaleUpBoard je komplexní webová platforma určená pro finanční analýzu českých firem. Aplikace automaticky zpracovává PDF výkazy zisku a ztráty (výsledovky) a rozvahy pomocí Claude Vision API, analyzuje finanční zdraví firmy a poskytuje personalizované doporučení prostřednictvím AI asistenta.

### Hlavní cíle

- **Automatizace parsování finančních výkazů** - Claude Vision API extrahuje data přímo z PDF
- **Finanční analýza v reálném čase** - Metriky, trendy, cashflow, profitabilita
- **AI Coaching** - Inteligentní chatbot pro finanční poradenství
- **Onboarding nových uživatelů** - Průvodce nastavením a prvním nahráním dat
- **Interaktivní dashboard** - Vizualizace KPI, grafů a predikce vývoje

---

## ⚡ Klíčové funkce

### 1. 📄 Vision-Based PDF Extraction

- **Automatické zpracování PDF výkazů** českých účetních standardů
- **Claude Sonnet 4 Vision API** pro grafickou detekci sloupců a řádků
- Extrakce dat **pouze z "Běžné období"** sloupce (ignoruje historická data)
- **Automatická detekce měřítka** (tisíce Kč / Kč) a normalizace
- **Confidence scoring** - indikátor kvality extrakce (0.0-1.0)
- **PNG backup** pro audit a reanalýzu

### 2. 🔄 Duplicate Detection & Confirmation

- Kontrola existence dat před nahráním nového dokumentu
- Separátní detekce pro **Výsledovku** (income_statement) a **Rozvahu** (balance_sheet)
- **Varování s porovnáním** - zobrazení confidence nových vs. stávajících dat
- **Uživatelské potvrzení** před přepsáním dat
- **Session-based workflow** - bezpečné ukládání během potvrzení

### 3. 📊 Finanční Dashboard

- **Dynamické KPI metriky**: Revenue, COGS, Gross Profit, EBITDA, Net Income
- **Trend analýza**: YoY growth, profitabilita, margin vývoj
- **Cashflow kalkulace**: Operating CF, Free CF, Working Capital Changes
- **Parsovaná data** - tabulka všech extrahovaných klíčů z databáze
- **Backward compatibility** - funguje se starými i novými daty

### 4. 🤖 AI Chatbot & Coaching

- **Kontextově zaměřený asistent** s přístupem k finančním datům uživatele
- **OpenAI GPT-4** / **Claude API** integrace
- **Předdefinované coaching scénáře**: cashflow management, profitabilita, růst
- **Interaktivní konverzace** s historií a perzistencí
- **Automatické přiřazování kouče** na základě potřeb uživatele

### 5. 🚀 Onboarding Flow

- **Multi-step průvodce** pro nové uživatele
- **První nahrání dat** - intuitivní upload s validací
- **AI-driven doporučení** okamžitě po prvním nahrání
- **Tutorial dashboardu** - průvodce po metrikách

### 6. 📈 Export & Reporting

- **PDF reporty** s metrikami a grafy
- **Excel export** - raw data pro další analýzu
- **Cashflow statement** - strukturovaný výkaz
- **Custom date ranges** - filtrování podle období

---

## 🛠️ Technologie

### Backend

- **Python 3.13** - Programming language
- **Django 5.2** - Web framework
- **Poetry** - Dependency management
- **PostgreSQL (Supabase)** - Database with pgvector extension
- **Celery + Redis** - Async task processing (RAG embeddings)

### AI & Machine Learning

- **Anthropic Claude Sonnet 4** (`claude-sonnet-4-20250514`) - Vision API pro PDF parsing
- **OpenAI GPT-4** - Chatbot & coaching
- **OpenAI text-embedding-3-small** - RAG embeddings (1536 dimensions)
- **pgvector** - Vector similarity search v PostgreSQL
- **PyMuPDF (fitz)** - PDF → PNG conversion @ 300 DPI
- **PDFPlumber** - Fallback text extraction

### Frontend

- **Django Templates** - Server-side rendering
- **Tailwind CSS** - Styling framework
- **HTMX** (optional) - Dynamic interactions
- **Chart.js** / **Plotly** - Data visualization

### Infrastructure

- **Git** - Version control
- **GitHub** - Repository hosting
- **Docker** (optional) - Containerization
- **Gunicorn / uWSGI** - WSGI server (production)

---

## 🚀 Rychlý start

### Požadavky

- Python **3.13+** (⚠️ pouze 3.13 až <4.0)
- Poetry **1.8+**
- Git

### Instalace

1. **Klonování repozitáře**
```bash
git clone https://github.com/bodichek/scb_ai_refactor.git
cd scaleupboard
```

2. **Instalace závislostí**
```bash
poetry install
```

3. **Konfigurace prostředí**

**⚠️ DŮLEŽITÉ:** Projekt používá oddělené prostředí pro development a production.

Pro lokální vývoj:
1. Vytvořte nový Supabase projekt pro development na [supabase.com](https://supabase.com)
2. Zkopírujte `.env.local.example` → `.env.local`
3. Vyplňte credentials z DEV projektu

Viz **[ENV_SETUP.md](ENV_SETUP.md)** pro podrobný návod (5 minut setup).

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase PostgreSQL (Development)
DB_USER=postgres.xxxxxxxxxx
DB_PASSWORD=your-dev-password
DB_HOST=aws-0-eu-central-1.pooler.supabase.com
DB_PORT=6543
SUPABASE_URL=https://xxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...

# Anthropic API (Claude Vision)
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI API (Chatbot & RAG)
OPENAI_API_KEY=sk-proj-...
```

4. **Spuštění migracíí**
```bash
poetry run python manage.py migrate
```

5. **Vytvoření superuživatele**
```bash
poetry run python manage.py createsuperuser
```

6. **Spuštění dev serveru**
```bash
poetry run python manage.py runserver
```

7. **Otevření aplikace**
```
http://localhost:8000
```

---

## 🏗️ Architektura

### Struktura projektu

```
scaleupboard/
├── accounts/           # Uživatelské účty, autentizace, profily
├── app/                # Hlavní Django config (settings, urls, wsgi)
├── chatbot/            # AI chatbot a coaching modul
├── coaching/           # Coaching scénáře a přiřazování kouče
├── dashboard/          # Finanční dashboard a KPI metriky
├── exports/            # Export do PDF/Excel
├── finance/            # Finanční výpočty (compute_metrics, cashflow)
├── ingest/             # PDF upload, parsing, vision extraction
├── rag/                # RAG Processing & Vector Embeddings
│   ├── services.py     # Chunking & Embedding services
│   ├── tasks.py        # Celery tasks pro async processing
│   ├── admin.py        # RAG monitoring dashboard
│   └── config.py       # Processing rules (immediate/batch/manual)
│   ├── extraction/     # Claude Vision API integrace
│   │   ├── claude_extractor.py
│   │   └── pdf_processor.py
│   ├── services/       # Business logika pro parsování
│   ├── templates/      # Upload forms, confirmation pages
│   ├── tests/          # Unit & integration testy
│   └── utils/          # Konstanty, field mappings
├── intercom/           # Intercom integrace (customer support)
├── onboarding/         # Průvodce pro nové uživatele
├── suropen/            # Survey modul (průzkumy)
├── survey/             # Ankety a feedback
├── templates/          # Globální Django templates
├── static/             # CSS, JS, obrázky
├── media/              # User-uploaded soubory (PDFs, PNGs)
├── docs/               # Dokumentace (private - excluded from git)
│   ├── CHANGELOG.md
│   ├── DEPLOYMENT_STATUS.md
│   ├── FIXES.md
│   └── TECHNICAL_NOTES.md
├── .env                # Environment variables (gitignored)
├── pyproject.toml      # Poetry dependencies
├── poetry.lock         # Locked dependency versions
└── manage.py           # Django management script
```

### Database Schema (Core Models)

#### FinancialStatement
```python
class FinancialStatement(models.Model):
    user = ForeignKey(User)                    # Vlastník dat
    year = IntegerField()                      # Rok výkazu
    income = JSONField(null=True)              # Výsledovka (Income Statement)
    balance = JSONField(null=True)             # Rozvaha (Balance Sheet)
    scale = CharField(default="thousands")     # Měřítko dat (vždy v tisících)
    local_image_path = CharField(max_length=500)  # Cesta k PNG backup
    confidence = FloatField()                  # Kvalita extrakce (0.0-1.0)
    document = OneToOneField(Document)         # Vztah k původnímu PDF

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'year'])  # Jeden záznam per rok
        ]
```

**Důležité:**
- **Jeden záznam per (user, year)** obsahuje **OBĚ** pole: `income` + `balance`
- Při nahrání Výsledovky → vyplní se `income` pole
- Při nahrání Rozvahy → vyplní se `balance` pole
- Přepsání jednoho typu neovlivní druhý

#### Document
```python
class Document(models.Model):
    uploaded_by = ForeignKey(User)
    file = FileField(upload_to='uploads/')
    document_type = CharField(choices=[
        ('income_statement', 'Výkaz zisku a ztráty'),
        ('balance_sheet', 'Rozvaha')
    ])
    uploaded_at = DateTimeField(auto_now_add=True)
```

#### ChatConversation
```python
class ChatConversation(models.Model):
    user = ForeignKey(User)
    messages = JSONField()  # Historie konverzace
    created_at = DateTimeField(auto_now_add=True)
```

---

## 📦 Moduly aplikace

### 1. `ingest/` - PDF Ingestion & Vision Extraction

**Účel:** Zpracování uploadovaných PDF výkazů pomocí Claude Vision API.

**Klíčové soubory:**
- `extraction/claude_extractor.py` - FinancialExtractor třída (Vision API volání)
- `extraction/pdf_processor.py` - PDFProcessor (PDF → PNG @ 300 DPI)
- `views.py` - Upload endpoints, duplicate detection logic
- `templates/upload_confirm.html` - Confirmation page před přepsáním dat

**Data Flow:**
```
PDF Upload → PNG Conversion → Claude Vision API → JSON Extraction
  → Post-Processing (scale + aggregates) → Database Save → Dashboard Display
```

**Podporované formáty:**
- Výkaz zisku a ztráty (Income Statement) - `income_statement`
- Rozvaha (Balance Sheet) - `balance_sheet`

**Extrahované klíče (Vision Parser):**
```python
# Výsledovka
revenue_products_services, revenue_goods, cogs_goods, cogs_materials,
cogs_services, personnel_costs, personnel_costs_wages,
personnel_costs_social, depreciation, other_operating_expenses,
other_operating_income, interest_expense, interest_income, tax, net_income

# Rozvaha
assets_total, fixed_assets, fixed_assets_intangible, fixed_assets_tangible,
fixed_assets_financial, current_assets, inventory, receivables, cash,
liabilities_total, equity, liabilities, liabilities_long, liabilities_short
```

---

### 2. `finance/` - Financial Calculations

**Účel:** Výpočty finančních metrik z raw dat.

**Klíčové funkce:**

#### `compute_metrics(fs: FinancialStatement) -> Dict`
Vypočítá všechny metriky z jednoho záznamu:
```python
{
    "revenue": 20367,           # Agregát nebo součet komponent
    "cogs": 15000,              # Cost of Goods Sold
    "gross_profit": 5367,       # Revenue - COGS
    "gross_margin": 0.263,      # Gross Profit / Revenue
    "ebitda": 4500,             # Earnings Before Interest, Tax, Depreciation, Amortization
    "ebitda_margin": 0.221,
    "net_income": 3200,
    "net_margin": 0.157,
    "income": {...},            # Raw výsledovka data
    "balance": {...}            # Raw rozvaha data
}
```

#### Backward Compatibility
Funguje s **novými i starými daty**:
- Nové: `revenue_products_services` + `revenue_goods` → `revenue`
- Staré: `Revenue` (aggregate) → `revenue`

---

### 3. `dashboard/` - Dashboard & Visualization

**Účel:** Zobrazení finančních metrik, trendů a grafů.

**Klíčové views:**
- `index()` - Hlavní dashboard s multi-year overview
- `build_dashboard_context()` - Agregace dat pro template
- `cashflow.py` - Kalkulace cashflow statements

**Zobrazované sekce:**
1. **KPI Cards** - Revenue, Gross Profit, EBITDA, Net Income (current year)
2. **Year-over-Year Growth** - Procentní změny metrik
3. **Profitability Analysis** - Margins (gross, EBITDA, net)
4. **Cashflow Statement** - Operating CF, Investing CF, Financing CF
5. **Parsovaná data** - Dynamická tabulka všech extrahovaných klíčů

**Dynamická tabulka:**
- Automaticky zobrazuje **všechny klíče** z `income` a `balance` polí
- Podporuje **nové i staré formáty** současně
- Žádné hardcodované názvy polí

---

### 4. `chatbot/` - AI Assistant

**Účel:** Inteligentní finanční asistent s přístupem k datům uživatele.

**Klíčové funkce:**
- **Kontextová konverzace** - AI vidí historii chatu
- **Finanční data access** - Chatbot má přístup k metrikám uživatele
- **OpenAI GPT-4** nebo **Claude API** integrace
- **Persistence** - Ukládání historie do databáze

**Usage:**
```python
from chatbot.services import ChatService

service = ChatService(user=request.user)
response = service.send_message("Jak vypadá můj cashflow?")
```

---

### 5. `coaching/` - AI Coaching System

**Účel:** Automatické přiřazování kouče na základě finančních potřeb.

**Coaching Scénáře:**
1. **Cashflow Management** - Negativní cashflow, vysoké DSO
2. **Profitability Improvement** - Nízké margins, vysoké náklady
3. **Growth Strategy** - Stagnující revenue, market expansion
4. **Cost Optimization** - Vysoké overhead costs

**Automatické přiřazení:**
```python
from coaching.services import assign_coach

coach = assign_coach(user)
# Analyzuje finanční metriky → doporučí nejlepšího kouče
```

---

### 6. `onboarding/` - User Onboarding

**Účel:** Průvodce pro nové uživatele.

**Steps:**
1. **Welcome** - Úvod do platformy
2. **Upload First Document** - První nahrání PDF
3. **View Dashboard** - Tutorial dashboardu
4. **Meet Your Coach** - Představení AI asistenta
5. **Completion** - Aktivace všech funkcí

---

### 7. `exports/` - Reporting & Exports

**Účel:** Export dat do různých formátů.

**Podporované formáty:**
- **PDF Report** - Finanční výkaz s grafy (ReportLab)
- **Excel (.xlsx)** - Raw data export (pandas / openpyxl)
- **JSON API** - Programmatický přístup k datům

**Usage:**
```python
from exports.services import generate_pdf_report

pdf_bytes = generate_pdf_report(user, year=2023)
```

---

### 8. `rag/` - RAG Processing System

**Účel:** Retrieval-Augmented Generation pro AI chatbot s dokumentovým kontextem.

**Komponenty:**
- **Document Chunking** - Rozdělení dokumentů na menší části (2000 tokenů, overlap 200)
- **Embedding Generation** - OpenAI text-embedding-3-small (1536 dimensions)
- **Vector Search** - pgvector similarity search
- **Hybrid Processing** - Immediate vs. Batch processing

**Processing Modes:**
1. **Immediate** (< 2 MB, kritické výkazy) → Async zpracování ihned po uploadu
2. **Batch** (>= 2 MB, ostatní) → Zpracování v noci (2 AM cron job)
3. **Manual** → Admin-triggered processing

**Monitoring Dashboard:** `/admin/rag-monitor/`
- Status overview (pending/processing/completed/failed)
- Embeddings completion rate s progress barem
- Failed documents s error messages
- Processing mode distribution

**Management Commands:**
```bash
# Zpracovat všechny pending dokumenty
python manage.py process_documents_rag

# Zpracovat konkrétní dokument
python manage.py process_documents_rag --document-id 123

# Pouze chunking (bez embeddings)
python manage.py process_documents_rag --skip-embeddings
```

**Viz:** [README_HYBRID_RAG.md](README_HYBRID_RAG.md) pro detailní dokumentaci

---

## 🤖 AI Integration

### Claude Vision API (PDF Parsing)

**Model:** `claude-sonnet-4-20250514`

**Workflow:**
1. PDF → PNG conversion @ 300 DPI (PyMuPDF)
2. PNG base64 encoded → Claude Vision API
3. Prompt instructs Claude to extract **only "Běžné období" column**
4. Response: JSON with raw components
5. Post-processing: aggregates computation + scale conversion

**Prompt Engineering:**
```
Extrahuj data z "Běžné období" sloupce. IGNORUJ "Minulé období".
Vrať POUZE JSON. Použij null pro chybějící hodnoty.
Nepiš agregáty - pouze raw komponenty (revenue_products_services, revenue_goods, atd.)
```

**Error Handling:**
- Confidence < 0.7 → Varování o špatné kvalitě
- API timeout → Fallback na text parser (PDFPlumber)
- Malformed JSON → Cleaning (`_clean_json_response()`)

### OpenAI GPT-4 (Chatbot)

**Model:** `gpt-4` / `gpt-3.5-turbo`

**System Prompt:**
```
Jsi finanční poradce pro české firmy. Máš přístup k finančním datům uživatele.
Analyzuj metriky a poskytni konkrétní doporučení.
```

**Context Injection:**
```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Moje data: {metrics}"},
    {"role": "user", "content": user_message}
]
```

---

## 🔧 API dokumentace

### REST Endpoints

#### Upload PDF
```
POST /ingest/upload/
Content-Type: multipart/form-data

Body:
{
  "year": 2023,
  "pdf_file": <binary>,
  "confirm_overwrite": "no"  // "yes" při potvrzení duplicity
}

Response:
{
  "success": true,
  "message": "Soubor byl úspěšně analyzován (confidence: 92%)",
  "year": 2023,
  "confidence": 0.92,
  "doc_type": "income_statement"
}
```

#### Dashboard Data
```
GET /dashboard/

Response: HTML (or JSON if Accept: application/json)
{
  "metrics": {
    "revenue": 20367,
    "gross_profit": 5367,
    "ebitda": 4500,
    ...
  },
  "years": [2021, 2022, 2023],
  "parsed_data": {...}
}
```

#### Chatbot Message
```
POST /chatbot/message/
Content-Type: application/json

Body:
{
  "message": "Jak vypadá můj cashflow?"
}

Response:
{
  "response": "Váš cashflow je...",
  "conversation_id": 123
}
```

---

## 🚀 Deployment

### Development

```bash
# Spuštění dev serveru
poetry run python manage.py runserver

# Spuštění testů
poetry run python manage.py test

# Vytvoření migrace
poetry run python manage.py makemigrations
poetry run python manage.py migrate
```

### Production (Ubuntu/Debian)

1. **Install system dependencies**
```bash
sudo apt update
sudo apt install python3.13 python3.13-venv python3-pip nginx postgresql
```

2. **Setup PostgreSQL**
```bash
sudo -u postgres createdb scaleupboard
sudo -u postgres createuser scaleupboard_user
```

3. **Configure environment**
```bash
cp .env.example .env
# Upravit .env s production hodnotami
```

4. **Install dependencies**
```bash
poetry install --no-dev
```

5. **Collect static files**
```bash
poetry run python manage.py collectstatic --no-input
```

6. **Setup Gunicorn**
```bash
poetry run gunicorn app.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

7. **Configure Nginx**
```nginx
server {
    listen 80;
    server_name scaleupboard.com;

    location /static/ {
        alias /var/www/scaleupboard/static/;
    }

    location /media/ {
        alias /var/www/scaleupboard/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

8. **Setup systemd service**
```ini
[Unit]
Description=ScaleUpBoard Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/scaleupboard
ExecStart=/var/www/scaleupboard/.venv/bin/gunicorn app.wsgi:application --bind 127.0.0.1:8000 --workers 4

[Install]
WantedBy=multi-user.target
```

---

## 🔒 Bezpečnost

### API Keys Management

⚠️ **NIKDY necommitovat API klíče do gitu!**

**Protected files (gitignored):**
- `.env` - Environment variables
- `.claude/settings.local.json` - Claude Code settings
- `db.sqlite3` - Database
- `media/` - User uploads

### Authentication

- Django default auth system
- Session-based authentication
- CSRF protection enabled
- Password hashing (PBKDF2)

### File Upload Security

- **Max file size:** 10 MB
- **Allowed formats:** `.pdf` only
- **Filename sanitization:** UUID-based naming
- **Virus scanning:** (TODO - integrate ClamAV)

### Database Security

- **SQL injection:** Protected by Django ORM
- **User isolation:** All queries filtered by `request.user`
- **Constraints:** UniqueConstraint per (user, year)

---

## 🧪 Testing

### Run all tests
```bash
poetry run python manage.py test
```

### Test specific module
```bash
poetry run python manage.py test ingest.tests
```

### Coverage report
```bash
poetry run coverage run --source='.' manage.py test
poetry run coverage report
poetry run coverage html
```

### Integration tests
```bash
# Dashboard integration
poetry run python test_dashboard_integration.py

# Vision extraction
poetry run python ingest/management/commands/test_vision_to_dashboard.py
```

---

## 📚 Dokumentace

### Setup & Deployment

- **[ENV_SETUP.md](ENV_SETUP.md)** - ⚡ Rychlý návod pro oddělení dev/prod prostředí (5 min)
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - 🚀 Detailní deployment guide pro PythonAnywhere
- **[README_HYBRID_RAG.md](README_HYBRID_RAG.md)** - 🧠 Kompletní dokumentace RAG systému
- **[MIGRATION_SUCCESS.md](MIGRATION_SUCCESS.md)** - 📊 PostgreSQL migrace poznámky

### Features & Systems

- **[COACH_ASSIGNMENT_SYSTEM.md](COACH_ASSIGNMENT_SYSTEM.md)** - Dokumentace coaching systému
- **[INTERACTIVE_DASHBOARD_GUIDE.md](INTERACTIVE_DASHBOARD_GUIDE.md)** - Guide pro dashboard features

### Private Docs (excluded from git)

- `docs/CHANGELOG.md` - Změny v aplikaci (kompletní historie)
- `docs/DEPLOYMENT_STATUS.md` - Aktuální stav deployment (konfigurace, testy)
- `docs/FIXES.md` - Opravy bugů (root cause analysis)
- `docs/TECHNICAL_NOTES.md` - Technické poznámky (architektura, debugging)

### Code Documentation

Všechny moduly obsahují docstrings:
```python
def compute_metrics(fs: FinancialStatement) -> Dict[str, Any]:
    """
    Vypočítá všechny finanční metriky z FinancialStatement.

    Args:
        fs: FinancialStatement instance s income a balance daty

    Returns:
        Dict obsahující revenue, cogs, gross_profit, margins, atd.
        Data jsou v tisících Kč (thousands).
    """
```

---

## 🤝 Contributing

### Branch Strategy

- `main` - Production-ready code
- `black_unicorn` - Current development branch (Vision Parser + Duplicate Detection)
- `feature/*` - Feature branches
- `fix/*` - Hotfix branches

### Commit Convention

```
<type>: <short description>

<detailed description>

Types: feat, fix, docs, style, refactor, test, chore
```

**Example:**
```
feat: add duplicate detection for PDF uploads

- Check for existing data before upload
- Show warning with confidence comparison
- Require user confirmation before overwrite
- Store temp file in session during confirmation

🤖 Generated with Claude Code
https://claude.com/claude-code

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Pull Request Process

1. Create feature branch from `main`
2. Implement changes with tests
3. Update documentation
4. Create PR with detailed description
5. Wait for review approval
6. Merge to `main`

---

## 📄 Licence

**Proprietary** - All rights reserved.

This software is private and proprietary. Unauthorized copying, distribution, or use is strictly prohibited.

---

## 👥 Tým

**Autor:** Bronislav Klus
**Email:** you@example.com
**GitHub:** [bodichek/scb_ai_refactor](https://github.com/bodichek/scb_ai_refactor)

**AI Assistant:** Claude (Anthropic)
**Development Tool:** [Claude Code](https://claude.com/claude-code)

---

## 🙏 Poděkování

- **Anthropic** - Claude Vision API pro PDF parsing
- **OpenAI** - GPT-4 pro chatbot
- **Django Community** - Framework a ekosystém
- **Python Community** - Tools a knihovny

---

## 📞 Kontakt & Podpora

- **Issues:** [GitHub Issues](https://github.com/bodichek/scb_ai_refactor/issues)
- **Email:** support@scaleupboard.com
- **Docs:** [Technical Notes](docs/TECHNICAL_NOTES.md)

---

**Made with ❤️ and 🤖 by ScaleUpBoard Team**

*Last updated: 2025-12-03*
