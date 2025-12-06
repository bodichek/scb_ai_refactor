# RAG Hybrid Processing System

**Datum:** 2025-12-06
**Status:** Production Ready

---

## Přehled

Hybrid RAG processing systém automaticky zpracovává dokumenty pro RAG (chunking + embeddings) s inteligentním rozhodováním mezi:

- **Immediate processing**: Dokument se zpracuje ihned po uploadu (asynchronně)
- **Batch processing**: Dokument se zpracuje v nočním batch jobu
- **Manual processing**: Admin musí spustit processing ručně

---

## Klíčové vlastnosti

### ✅ Automatické rozhodování
- Systém automaticky určí, jak dokument zpracovat na základě:
  - **Velikosti souboru** (< 5 MB → immediate, >= 5 MB → batch)
  - **Typu dokumentu** (income_statement/balance_sheet → immediate)
  - **Konfiguračních pravidel**

### ✅ Error handling & retry logic
- **Automatické retry**: 3 pokusy s 5min delay mezi nimi
- **Admin notifikace**: Email při selhání processingu
- **Status tracking**: Každý dokument má `rag_status` (pending/processing/completed/failed)

### ✅ Admin monitoring
- **Django admin interface** s barevnými statusy
- **Batch actions**: "Trigger RAG processing", "Retry failed documents"
- **Chunks info**: Počet chunks a embeddings
- **Error logs**: Detailní chybové zprávy

---

## Architektura

```
┌─────────────────┐
│  User uploads   │
│    document     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   pre_save      │  ← Určení processing mode (immediate/batch/manual)
│    signal       │     na základě pravidel v config.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Document.save() │  ← Uložení do DB s rag_status="pending"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  post_save      │  ← Trigger podle rag_processing_mode
│    signal       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────┐   ┌─────┐
│ immediate│ batch│
│         │     │
└────┬────┘ └───┬─┘
     │          │
     ▼          ▼
┌──────────┐ ┌────────┐
│  Celery  │ │ Nightly│
│   task   │ │  cron  │
└────┬─────┘ └───┬────┘
     │           │
     └─────┬─────┘
           ▼
    ┌──────────────┐
    │ RAG Process: │
    │ 1. Extract   │
    │ 2. Chunk     │
    │ 3. Embed     │
    └──────┬───────┘
           │
      ┌────┴────┐
      │         │
   SUCCESS    FAILED
      │         │
      ▼         ▼
┌─────────┐ ┌──────────┐
│ completed│ │  failed  │
│         │ │ + retry  │
│         │ │ + email  │
└─────────┘ └──────────┘
```

---

## Konfigurace

### Processing Rules ([rag/config.py](rag/config.py))

```python
class RAGProcessingConfig:
    # Max velikost pro immediate processing (5 MB)
    IMMEDIATE_PROCESSING_MAX_SIZE = 5 * 1024 * 1024

    # Doc types pro immediate processing
    IMMEDIATE_PROCESSING_DOC_TYPES = [
        "income_statement",
        "balance_sheet",
    ]

    # Doc types pro batch processing
    BATCH_PROCESSING_DOC_TYPES = [
        "other",
    ]

    # Zapnout/vypnout auto-processing
    AUTO_PROCESSING_ENABLED = True
```

**Pravidla (v pořadí priority):**

1. Pokud `AUTO_PROCESSING_ENABLED = False` → **manual**
2. Pokud file size > threshold → **batch**
3. Pokud doc_type in immediate list → **immediate**
4. Pokud doc_type in batch list → **batch**
5. Default → **immediate**

### Django Settings

Přidej do `settings.py`:

```python
# RAG Processing Settings
RAG_EMBEDDING_BATCH_SIZE = 10  # Chunks per embedding batch
RAG_MAX_RETRIES = 3  # Max retry attempts
RAG_RETRY_DELAY = 300  # Retry delay in seconds (5 min)
RAG_CHUNK_SIZE = 2000  # Characters per chunk
RAG_CHUNK_OVERLAP = 200  # Overlap between chunks
RAG_EMAIL_NOTIFICATIONS = True  # Email admins on failure

# Email settings (pro notifikace)
ADMINS = [
    ("Admin Name", "admin@example.com"),
]
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "your-email@gmail.com"
EMAIL_HOST_PASSWORD = "your-app-password"
```

---

## Celery Setup

### 1. Install Celery

```bash
pip install celery redis
```

### 2. Create celery.py

`app/celery.py`:

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('scaleupboard')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### 3. Update app/__init__.py

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 4. Add to settings.py

```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Prague'
```

### 5. Run Celery Worker

```bash
# Development
celery -A app worker --loglevel=info

# Production (with beat for scheduled tasks)
celery -A app worker --beat --loglevel=info
```

---

## Cron Job pro Batch Processing

### Nightly Batch Processing

Přidej do crontab:

```bash
# Každou noc ve 2:00 zpracovat pending dokumenty
0 2 * * * cd /path/to/project && python manage.py process_batch_rag >> /tmp/rag_batch.log 2>&1
```

Nebo vytvoř Django management command:

```bash
python manage.py process_batch_rag
```

---

## Použití

### 1. Upload dokumentu (automatický trigger)

```python
# V ingest/views.py
document = Document.objects.create(
    owner=request.user,
    file=uploaded_file,
    doc_type="income_statement",  # Automatic immediate processing
)
# → rag_processing_mode="immediate" (auto-set v pre_save signal)
# → Celery task triggered automatically (v post_save signal)
```

### 2. Manuální trigger z Adminu

1. Otevři Django admin: `/admin/ingest/document/`
2. Vyber dokumenty
3. Action: "Trigger RAG processing"
4. Klikni "Go"

### 3. Retry failed documents

```python
# V admin nebo shell
failed_docs = Document.objects.filter(rag_status="failed")

for doc in failed_docs:
    doc.rag_retry_count = 0
    doc.rag_status = "pending"
    doc.save()

    from rag.tasks import process_document_rag
    process_document_rag.delay(doc.id)
```

### 4. Monitoring z Django shell

```python
from ingest.models import Document

# Status overview
from django.db.models import Count
status_counts = Document.objects.values('rag_status').annotate(count=Count('id'))
for s in status_counts:
    print(f"{s['rag_status']}: {s['count']}")

# Failed documents
failed = Document.objects.filter(rag_status="failed")
for doc in failed:
    print(f"{doc.id}: {doc.filename} - {doc.rag_error_message}")

# Pending batch processing
pending_batch = Document.objects.filter(
    rag_status="pending",
    rag_processing_mode="batch"
)
print(f"Pending batch: {pending_batch.count()}")
```

---

## Admin Interface

### List View Features

- **Status badge**: Barevný status (pending/processing/completed/failed)
- **Chunks count**: Počet chunks + chunks s embeddings
- **Processing mode**: immediate/batch/manual
- **Actions column**: Tlačítka pro retry/process/view chunks

### Detail View Features

- **RAG Processing section** (collapsible):
  - Processing mode (editable)
  - Status (read-only)
  - Processed at timestamp
  - Retry count
  - Error message
  - Chunks info (count, embeddings, characters, tokens)

### Batch Actions

1. **Trigger RAG processing**: Spustí processing pro vybrané dokumenty
2. **Retry failed documents**: Retry pouze failed dokumenty z výběru

---

## Error Handling

### Automatic Retry

```python
# V tasks.py
@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def process_document_rag(self, document_id, ...):
    try:
        # Processing logic
        ...
    except Exception as e:
        # Update status
        document.rag_status = "failed"
        document.rag_error_message = str(e)
        document.rag_retry_count += 1
        document.save()

        # Notify admin
        _notify_admin_on_failure(document, e)

        # Retry if not max retries
        if document.rag_retry_count < 3:
            raise self.retry(exc=e)
```

### Admin Email Notifications

**Single document failure:**

```
Subject: RAG Processing Failed: Vysledovka_2023.pdf

Document ID: 331
Filename: Vysledovka_2023.pdf
Owner: john@example.com
Retry count: 2

Error:
OpenAI API error: Rate limit exceeded

Document URL: /admin/ingest/document/331/change/
```

**Batch processing summary:**

```
Subject: RAG Batch Processing Summary: 3 failures

Total documents: 25
Successful: 22
Failed: 3

Failed documents:
- Document 331 (Vysledovka_2023.pdf): OpenAI API error
- Document 332 (Balance_2023.pdf): No text extracted
- Document 335 (Other.pdf): Embedding generation failed
```

---

## Status Flow

```
┌─────────┐
│ PENDING │ ← Initial status po uploadu
└────┬────┘
     │
     ▼
┌────────────┐
│ PROCESSING │ ← Task started
└─────┬──────┘
      │
  ┌───┴───┐
  │       │
SUCCESS  FAILED
  │       │
  ▼       ▼
┌───────┐ ┌─────────┐
│COMPLETED│ │ FAILED  │
└─────────┘ └────┬────┘
              │
           retry?
              │
            ┌─┴─┐
         YES   NO
            │   │
            ▼   ▼
      ┌─────┐ ┌───────┐
      │PENDING│ │FAILED │
      └───────┘ └───────┘
```

---

## Troubleshooting

### Problém: Document se nezpracuje automaticky

**Check:**

1. Je `AUTO_PROCESSING_ENABLED = True` v config.py?
2. Jaký je `rag_processing_mode` dokumentu?
3. Běží Celery worker?

```bash
# Check processing mode
python manage.py shell
>>> doc = Document.objects.get(id=331)
>>> doc.rag_processing_mode
'immediate'
>>> doc.rag_status
'pending'

# Check Celery
celery -A app inspect active
```

### Problém: Failed processing, ale bez error message

**Fix:**

```python
# V Django shell
doc = Document.objects.get(id=331)
doc.rag_status = "pending"
doc.rag_retry_count = 0
doc.save()

# Trigger manually
from rag.tasks import process_document_rag
result = process_document_rag.apply(args=[doc.id])
print(result.get())
```

### Problém: Email notifikace nefungují

**Check:**

1. `RAG_EMAIL_NOTIFICATIONS = True` v settings?
2. `ADMINS` seznam nastaven?
3. `EMAIL_BACKEND` konfigurace správná?

```python
# Test email
from django.core.mail import mail_admins
mail_admins("Test", "Test message")
```

---

## API Reference

### Celery Tasks

```python
from rag.tasks import process_document_rag, process_batch_documents

# Process single document
task = process_document_rag.delay(document_id=331)
print(task.id)  # Task ID

# Process batch
result = process_batch_documents.delay(mode="batch")
```

### Signals

```python
# Pre-save: Auto-set processing mode
@receiver(pre_save, sender=Document)
def set_rag_processing_mode(sender, instance, **kwargs):
    RAGProcessingConfig.update_document_processing_mode(instance)

# Post-save: Trigger processing
@receiver(post_save, sender=Document)
def auto_process_document_rag(sender, instance, created, **kwargs):
    if created and instance.rag_processing_mode == "immediate":
        process_document_rag.delay(instance.id)
```

### Config API

```python
from rag.config import RAGProcessingConfig, RAGSettings

# Get processing mode for document
mode = RAGProcessingConfig.get_processing_mode(document)

# Check if should process immediately
should_process = RAGProcessingConfig.should_process_immediately(document)

# Get settings
batch_size = RAGSettings.get_embedding_batch_size()
max_retries = RAGSettings.get_max_retries()
```

---

## Performance & Costs

### Immediate Processing

- **Latency**: ~5-10s (extract + chunk + embed)
- **User experience**: Non-blocking (async via Celery)
- **Cost**: $0.001-0.003 per document

### Batch Processing

- **Latency**: Next day (2 AM)
- **Throughput**: ~100 docs/hour
- **Cost**: Same as immediate, but batched

### Recommendations

- **Small docs (< 5 MB)**: Immediate
- **Large docs (>= 5 MB)**: Batch
- **Critical doc types** (income_statement, balance_sheet): Immediate
- **Other docs**: Batch

---

## Migration from Manual Processing

Pokud už máš dokumenty v DB, které nebyly zpracovány:

```python
# 1. Set default processing mode for existing docs
from ingest.models import Document

docs_without_mode = Document.objects.filter(rag_processing_mode="")
for doc in docs_without_mode:
    from rag.config import RAGProcessingConfig
    RAGProcessingConfig.update_document_processing_mode(doc)
    doc.save()

# 2. Trigger batch processing for all pending
from rag.tasks import process_batch_documents
result = process_batch_documents.delay(mode="batch")
```

---

## Next Steps

### Production Deployment

1. **Setup Celery** (Redis broker)
2. **Configure email** (SMTP settings)
3. **Setup cron** (nightly batch)
4. **Test error flow** (manual failure simulation)
5. **Monitor first week** (check admin daily)

### Future Enhancements

- [ ] **Web UI** pro RAG status monitoring (dashboard)
- [ ] **Webhook notifications** (Slack/Discord místo email)
- [ ] **Priority queue** (VIP users → immediate processing)
- [ ] **Smart scheduling** (process large docs during low-traffic hours)
- [ ] **Cost tracking** (track OpenAI API costs per document)

---

## Soubory

| Soubor | Popis |
|--------|-------|
| [rag/tasks.py](rag/tasks.py) | Celery tasks pro async processing |
| [rag/signals.py](rag/signals.py) | Django signals pro auto-trigger |
| [rag/config.py](rag/config.py) | Processing rules & settings |
| [ingest/models.py](ingest/models.py) | Document model s RAG fields |
| [ingest/admin.py](ingest/admin.py) | Enhanced admin interface |
| [rag/management/commands/process_documents_rag.py](rag/management/commands/process_documents_rag.py) | Manual command |

---

**Projekt:** Scaling Up Client Intelligence Platform
**Hybrid RAG Implementation:** 2025-12-06
**Status:** Production Ready

Pro otázky nebo problémy, check Django admin logs nebo kontaktuj dev team.
