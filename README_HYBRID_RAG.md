# Hybrid RAG Processing - Quick Start

**Datum:** 2025-12-06
**Status:** ✅ Production Ready

---

## Co je nového?

Automatický **hybrid RAG processing systém** s inteligentním rozhodováním a admin notifikacemi:

### ✨ Klíčové features

- **🚀 Auto-processing**: Dokumenty se zpracují automaticky po uploadu
- **🎯 Smart routing**: Immediate vs. batch podle velikosti a typu
- **🔄 Retry logic**: 3 pokusy s 5min delay při selhání
- **📧 Admin alerts**: Email notifikace při chybách
- **📊 Admin dashboard**: Enhanced interface s status badges
- **⚙️ Konfigurovatelné**: Pravidla v `rag/config.py`

---

## 🚀 Quick Start

### 1. Instalace závislostí

```bash
pip install celery redis
```

### 2. Spuštění Redis (broker pro Celery)

```bash
# Windows (chocolatey)
choco install redis-64
redis-server

# Linux/Mac
sudo apt-get install redis-server
redis-server
```

### 3. Spuštění Celery worker

```bash
celery -A app worker --loglevel=info
```

### 4. Upload dokumentu → Auto-processing

```python
# Upload v ingest/views.py se automaticky zpracuje
document = Document.objects.create(
    owner=request.user,
    file=uploaded_file,
    doc_type="income_statement",  # → immediate processing
)
# Celery task automaticky triggered!
```

---

## 📋 Processing Modes

### Immediate (ihned, async)
- **Kdy**: Malé dokumenty (< 5 MB) + critical types (income_statement, balance_sheet)
- **Jak**: Celery task spuštěn hned po uploadu
- **Latence**: ~5-10s

### Batch (v noci)
- **Kdy**: Velké dokumenty (>= 5 MB) + typ "other"
- **Jak**: Cron job ve 2:00
- **Latence**: Next day

### Manual (ručně)
- **Kdy**: Admin chce kontrolu
- **Jak**: Django admin action

---

## 🎯 Processing Flow

```
Upload → pre_save signal → determine mode (immediate/batch/manual)
      → Document.save() → rag_status="pending"
      → post_save signal → trigger podle mode

Immediate mode:
  → Celery task → extract + chunk + embed
  → SUCCESS: rag_status="completed"
  → FAILED: rag_status="failed" + email admin + retry (max 3x)

Batch mode:
  → Wait for cron job (2 AM)
  → Same processing as immediate
```

---

## 🛠️ Konfigurace

### Processing Rules ([rag/config.py](rag/config.py:18-29))

```python
class RAGProcessingConfig:
    # Max velikost pro immediate (5 MB)
    IMMEDIATE_PROCESSING_MAX_SIZE = 5 * 1024 * 1024

    # Doc types → immediate
    IMMEDIATE_PROCESSING_DOC_TYPES = [
        "income_statement",
        "balance_sheet",
    ]

    # Doc types → batch
    BATCH_PROCESSING_DOC_TYPES = [
        "other",
    ]

    # Enable/disable
    AUTO_PROCESSING_ENABLED = True
```

**Pravidla (priority order):**

1. `AUTO_PROCESSING_ENABLED = False` → **manual**
2. File size > 5 MB → **batch**
3. Doc type in immediate list → **immediate**
4. Doc type in batch list → **batch**
5. Default → **immediate**

### Django Settings

Přidej do `settings.py`:

```python
# Email notifikace
ADMINS = [
    ("Admin Name", "admin@example.com"),
]

# RAG settings (optional, mají defaults)
RAG_EMBEDDING_BATCH_SIZE = 10
RAG_MAX_RETRIES = 3
RAG_RETRY_DELAY = 300  # 5 min
RAG_EMAIL_NOTIFICATIONS = True
```

---

## 👨‍💼 Admin Interface

### Django Admin ([/admin/ingest/document/](http://localhost:8000/admin/ingest/document/))

**List view features:**

- **Status badge**: 🟢 COMPLETED, 🔴 FAILED, 🔵 PROCESSING, ⚫ PENDING
- **Chunks count**: "5 chunks (5 with embeddings)"
- **Processing mode filter**: immediate/batch/manual
- **Actions**: "Trigger RAG processing", "Retry failed documents"

**Detail view features:**

- **RAG Processing section**:
  - Status, processed at, retry count
  - Error message (pokud failed)
  - Chunks info (count, embeddings, chars, tokens)

**Batch actions:**

1. Vyber dokumenty
2. Action: "Trigger RAG processing" nebo "Retry failed documents"
3. Klikni "Go"

---

## 📧 Admin Notifications

### Single Document Failure

```
Subject: RAG Processing Failed: Vysledovka_2023.pdf

Document ID: 331
Filename: Vysledovka_2023.pdf
Owner: john@example.com
Retry count: 2

Error: OpenAI API error: Rate limit exceeded

Document URL: /admin/ingest/document/331/change/
```

### Batch Processing Summary

```
Subject: RAG Batch Processing Summary: 3 failures

Total: 25
Successful: 22
Failed: 3

Failed documents:
- Document 331 (Vysledovka_2023.pdf): OpenAI API error
- Document 332 (Balance_2023.pdf): No text extracted
```

---

## 🔍 Monitoring

### Django Shell

```python
from ingest.models import Document
from django.db.models import Count

# Status overview
status_counts = Document.objects.values('rag_status').annotate(count=Count('id'))
for s in status_counts:
    print(f"{s['rag_status']}: {s['count']}")

# Failed documents
failed = Document.objects.filter(rag_status="failed")
for doc in failed:
    print(f"{doc.id}: {doc.filename}")
    print(f"  Error: {doc.rag_error_message}")
    print(f"  Retries: {doc.rag_retry_count}")

# Pending batch
pending_batch = Document.objects.filter(
    rag_status="pending",
    rag_processing_mode="batch"
)
print(f"\nPending batch processing: {pending_batch.count()}")
```

### Admin Dashboard

```
/admin/ingest/document/
```

Filters:
- RAG status (pending/processing/completed/failed)
- RAG processing mode (immediate/batch/manual)
- Document type
- Year, Owner

---

## ⚠️ Troubleshooting

### Dokumenty se nezpracovávají automaticky

**Check:**

```bash
# 1. Běží Celery?
celery -A app inspect active

# 2. Config správný?
python manage.py shell
>>> from rag.config import RAGProcessingConfig
>>> RAGProcessingConfig.AUTO_PROCESSING_ENABLED
True

# 3. Document má správný mode?
>>> doc = Document.objects.last()
>>> doc.rag_processing_mode
'immediate'
>>> doc.rag_status
'pending'
```

### Failed processing bez error message

```python
# Django shell - manuální trigger s logem
from rag.tasks import process_document_rag

doc_id = 331
result = process_document_rag.apply(args=[doc_id])
print(result.get())  # Uvidíš error
```

### Email notifikace nefungují

```python
# Test email
from django.core.mail import mail_admins
mail_admins("Test Subject", "Test message", fail_silently=False)
```

Check v `settings.py`:
- `EMAIL_BACKEND`
- `EMAIL_HOST`, `EMAIL_PORT`
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `ADMINS` seznam

---

## 📚 Dokumentace

| Dokument | Popis |
|----------|-------|
| **[RAG_HYBRID_PROCESSING.md](docs/RAG_HYBRID_PROCESSING.md)** | Kompletní dokumentace systému |
| **[RAG_CHATBOT_GUIDE.md](docs/RAG_CHATBOT_GUIDE.md)** | RAG chatbot user guide |
| **[PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)** | FÁZE 2 technická spec |

---

## 🎯 Použití

### Scenario 1: Upload malého dokumentu

```python
# User uploadne income statement (2 MB)
document = Document.objects.create(
    owner=user,
    file=uploaded_file,
    doc_type="income_statement",
)

# → pre_save signal: rag_processing_mode = "immediate"
# → post_save signal: Celery task triggered
# → ~5s later: rag_status = "completed"
```

### Scenario 2: Upload velkého dokumentu

```python
# User uploadne other document (10 MB)
document = Document.objects.create(
    owner=user,
    file=uploaded_file,
    doc_type="other",
)

# → pre_save signal: rag_processing_mode = "batch"
# → post_save signal: Žádný trigger (čeká na cron)
# → Ve 2:00: Cron job zpracuje
```

### Scenario 3: Manuální processing

```python
# Admin uploadne s manual mode
document = Document.objects.create(
    owner=user,
    file=uploaded_file,
    rag_processing_mode="manual",  # Explicitně
)

# → Žádný auto-trigger
# → Admin musí spustit z Django admin
```

### Scenario 4: Retry po failure

```python
# V admin nebo shell
doc = Document.objects.get(id=331)
doc.rag_retry_count = 0
doc.rag_status = "pending"
doc.save()

from rag.tasks import process_document_rag
process_document_rag.delay(doc.id)
```

---

## 🔐 Production Setup

### 1. Celery Setup

```python
# app/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
app = Celery('scaleupboard')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

```python
# app/__init__.py
from .celery import app as celery_app
__all__ = ('celery_app',)
```

```python
# settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

### 2. Systemd Service (Linux)

```ini
# /etc/systemd/system/celery.service
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/scaleupboard
ExecStart=/usr/local/bin/celery -A app worker --detach --loglevel=info

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable celery
sudo systemctl start celery
```

### 3. Cron Job

```bash
# Batch processing každou noc ve 2:00
0 2 * * * cd /var/www/scaleupboard && python manage.py shell -c "from rag.tasks import process_batch_documents; process_batch_documents.delay()" >> /tmp/rag_cron.log 2>&1
```

---

## 📊 Status Tracking

### Document Model Fields

| Field | Type | Popis |
|-------|------|-------|
| `rag_status` | CharField | pending/processing/completed/failed/skipped |
| `rag_processing_mode` | CharField | immediate/batch/manual |
| `rag_processed_at` | DateTimeField | Kdy dokončeno |
| `rag_error_message` | TextField | Error details |
| `rag_retry_count` | IntegerField | Počet retry pokusů |

### Status Flow

```
PENDING → PROCESSING → COMPLETED
                    ↘
                      FAILED → retry → PENDING
                             ↘
                               FAILED (max retries)
```

---

## 💰 Costs

### Per Document

- **Chunking**: Zdarma
- **Embeddings**: ~$0.001-0.003 (OpenAI text-embedding-3-small)
- **Total**: ~$0.003 per document

### Monthly (100 docs/month)

- **Immediate**: $0.30
- **Batch**: $0.30 (stejné, jen jiný timing)

---

## ✅ Checklist před produkci

- [ ] Redis běží a je dostupný
- [ ] Celery worker běží
- [ ] Email settings nakonfigurované
- [ ] `ADMINS` seznam nastaven
- [ ] Cron job pro batch processing
- [ ] `AUTO_PROCESSING_ENABLED = True`
- [ ] Test upload + check admin
- [ ] Test failed document + check email
- [ ] Monitoring dashboard setup

---

## 🎉 Výsledek

Máš teď:

✅ **Automatické RAG processing** po uploadu
✅ **Inteligentní routing** (immediate/batch/manual)
✅ **Error handling** s retry logic
✅ **Admin notifikace** při chybách
✅ **Enhanced admin** s status monitoring
✅ **Konfigurovatelné pravidla** pro processing
✅ **Production-ready** dokumentace

**Next step**: Deploy to production a test! 🚀

---

**Branch:** `supabase-dev`
**Latest commit:** `0c4e4f9`

Pro detaily viz [docs/RAG_HYBRID_PROCESSING.md](docs/RAG_HYBRID_PROCESSING.md)
