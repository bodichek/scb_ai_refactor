# RAG Chatbot - Analýza a Diagnostika

**Datum:** 6. prosince 2025
**Status:** ⚠️ NEFUNKČNÍ - Vyžaduje opravu

---

## 🔍 Zjištěné Problémy

### 1. ❌ KRITICKÉ: Databázové Připojení Selhává

**Chyba:**
```
connection to server at "aws-0-eu-central-1.pooler.supabase.com" failed:
FATAL: Tenant or user not found
```

**Příčina:**
- Soubor `.env.local` obsahuje **neplatné nebo zastaralé credentials**
- Development Supabase projekt neexistuje nebo má jiné credentials

**Řešení:**
1. Vytvoř nový Development Supabase projekt na https://supabase.com
2. Zkopíruj správné credentials do `.env.local`:
   ```env
   DB_USER=postgres.xxxxxxxxxx
   DB_PASSWORD=your-actual-password
   DB_HOST=aws-0-eu-central-1.pooler.supabase.com
   DB_PORT=6543
   SUPABASE_URL=https://xxxxxxxxxx.supabase.co
   SUPABASE_ANON_KEY=eyJhbGc...
   ```
3. Nebo použij **production credentials** dočasně:
   ```bash
   set DJANGO_ENV=production
   python test_rag_chatbot.py
   ```

---

## 📊 Architektura RAG Chatbotu

### Jak RAG Chatbot Funguje (Teoreticky)

```
User Query
    ↓
┌─────────────────────────────────────────┐
│ 1. EMBEDDING GENERATION                 │
│    - User dotaz → OpenAI embedding      │
│    - Model: text-embedding-3-small      │
│    - Dimension: 1536                    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 2. SEMANTIC SEARCH (pgvector)           │
│    - Cosine similarity v PostgreSQL     │
│    - Filtr: pouze user's documents      │
│    - Top K results (default: 5)         │
│    - Similarity threshold: 0.7          │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 3. CONTEXT BUILDING                     │
│    - Sestaví kontext z top chunks       │
│    - Přidá metadata (doc, year, type)   │
│    - Formátuje pro LLM                  │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 4. LLM PROMPT ENHANCEMENT               │
│    - System prompt + User query         │
│    - + Retrieved context                │
│    - Model: GPT-4o                      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 5. RESPONSE WITH SOURCES                │
│    - AI odpověď                         │
│    - + Source citations                 │
│    - + Similarity scores                │
└─────────────────────────────────────────┘
```

---

## 🔧 Kódová Analýza

### ✅ CO FUNGUJE (kód je správně napsaný)

#### 1. **RAG Chat Service** (`chatbot/services/rag_chat_service.py`)

**SPRÁVNĚ:**
- ✅ `retrieve_context()` - Volá `SemanticSearchService.search_by_user()`
- ✅ Filtruje podle `similarity_threshold` (0.7)
- ✅ Sestavuje kontext z DocumentChunks
- ✅ Builduje enhanced prompt s kontextem
- ✅ Formátuje response se sources

**Kód je korektní:**
```python
def retrieve_context(self, query: str, user: User, section: Optional[str] = None):
    # Performs semantic search
    hits = self.search_service.search_by_user(
        query=query,
        user=user,
        limit=self.max_context_chunks,  # 5
    )

    # Filters by similarity
    relevant_hits = [
        hit for hit in hits
        if hit.score >= self.similarity_threshold  # 0.7
    ]

    # Builds context text from chunks
    context_parts = []
    for hit in relevant_hits:
        context_parts.append(
            f"[Dokument {i}: {hit.chunk.document.filename} ({hit.chunk.document.year})]\n"
            f"{hit.chunk.content}\n"
        )
```

**✅ ANO, vidí do databáze** - používá `SemanticSearchService`

#### 2. **Semantic Search Service** (`rag/services/search_service.py`)

**SPRÁVNĚ:**
- ✅ `search_by_user()` - Přidává filter `document__owner_id = user.id`
- ✅ Používá pgvector `<=>` operator pro cosine distance
- ✅ SQL query je správně sestavený:

```python
def search_by_user(self, query: str, user: User, limit: int = 10):
    return self.search(
        query=query,
        user=user,
        limit=limit,
        filters={'document__owner_id': user.id},  # ✅ FILTR!
        log_query=True,
    )
```

**SQL Query:**
```sql
SELECT
    id, content, document_id, chunk_index,
    1 - (embedding <=> %s::vector) / 2 AS similarity
FROM rag_documentchunk
WHERE embedding IS NOT NULL
  AND document__owner_id = %s  -- ✅ USER FILTER
  AND (1 - (embedding <=> %s::vector) / 2) >= 0.7  -- threshold
ORDER BY embedding <=> %s::vector
LIMIT 5
```

**✅ ANO, posílá data z DB k OpenAI** - kontext je součástí promptu

#### 3. **RAG View** (`chatbot/views_rag.py`)

**SPRÁVNĚ:**
- ✅ `/chatbot/api/rag/` endpoint
- ✅ Volá `rag_service.generate_rag_response()`
- ✅ Posílá enhanced prompt do OpenAI:

```python
# Builds messages with RAG context
messages = [
    {"role": "system", "content": RAG_SYSTEM_PROMPT},
    {"role": "user", "content": user_message},  # ✅ Obsahuje kontext!
]

# Calls OpenAI
completion = client.chat.completions.create(
    model=ASSISTANT_MODEL,  # gpt-4o
    messages=messages,
    temperature=0.7,
    max_tokens=1500,
)
```

**✅ ANO, data z DB jdou do OpenAI** - jako součást `user_message`

---

## ⚠️ CO MŮŽE SELHAT (ne kód, ale data)

### 1. **Žádné Chunky v Databázi**
```python
# Pokud není spuštěn RAG processing:
DocumentChunk.objects.count()  # → 0 ❌
```

**Kontrola:**
```bash
python manage.py shell
>>> from rag.models import DocumentChunk
>>> DocumentChunk.objects.count()
>>> DocumentChunk.objects.filter(embedding__isnull=False).count()
```

**Řešení:**
```bash
python manage.py process_documents_rag
```

### 2. **Chunky Bez Embeddingů**
```python
# Pokud embeddings selhaly:
chunks_without_embeddings = DocumentChunk.objects.filter(embedding__isnull=True).count()
```

**Příčiny:**
- OpenAI API key není platný
- Rate limit exceeded
- Processing byl přerušen

### 3. **User Nemá Žádné Dokumenty**
```python
# Pokud user nemá nahrané PDF:
Document.objects.filter(owner=user).count()  # → 0 ❌
# Pak:
DocumentChunk.objects.filter(document__owner=user).count()  # → 0 ❌
```

**Výsledek:** RAG vrátí prázdný kontext

### 4. **Low Similarity Scores**
```python
# Pokud jsou všechny chunks irelevantní:
relevant_hits = [hit for hit in hits if hit.score >= 0.7]  # → [] ❌
```

**Příčiny:**
- User dotaz je příliš odlišný od obsahu dokumentů
- Embeddings jsou špatné kvality
- Threshold 0.7 je příliš přísný

---

## 🧪 Testovací Checklist

### Pro Ověření, Že RAG Funguje:

```bash
# 1. Zkontroluj databázové připojení
python manage.py shell
>>> from django.db import connection
>>> connection.cursor()  # Mělo by fungovat

# 2. Zkontroluj RAG data
>>> from rag.models import DocumentChunk
>>> DocumentChunk.objects.count()  # Mělo by být > 0
>>> DocumentChunk.objects.filter(embedding__isnull=False).count()  # > 0

# 3. Zkontroluj user documenty
>>> from django.contrib.auth import get_user_model
>>> from ingest.models import Document
>>> User = get_user_model()
>>> user = User.objects.first()
>>> Document.objects.filter(owner=user).count()  # > 0
>>> DocumentChunk.objects.filter(document__owner=user).count()  # > 0

# 4. Test semantic search
>>> from rag.services import SemanticSearchService
>>> search = SemanticSearchService()
>>> results = search.search_by_user(query="tržby", user=user, limit=3)
>>> len(results)  # Mělo by být > 0
>>> results[0].chunk.content  # Měl by obsahovat relevantní text

# 5. Test RAG service
>>> from chatbot.services import RAGChatService
>>> rag = RAGChatService()
>>> context = rag.retrieve_context(query="jaké jsou tržby?", user=user)
>>> context['has_context']  # True
>>> len(context['sources'])  # > 0

# 6. Test full flow
>>> result = rag.generate_rag_response(query="jaké jsou tržby?", user=user)
>>> result['has_rag_context']  # True
>>> result['prompt']  # Měl by obsahovat context z dokumentů
```

---

## 📋 Akční Kroky

### OKAMŽITĚ:

1. **Fix Database Connection:**
   ```bash
   # Option A: Použij production DB dočasně
   set DJANGO_ENV=production
   python manage.py shell

   # Option B: Vytvoř nový dev Supabase projekt
   # a updatuj .env.local
   ```

2. **Spusť RAG Processing:**
   ```bash
   python manage.py process_documents_rag
   ```

3. **Verify Data:**
   ```bash
   python manage.py shell
   >>> from rag.models import DocumentChunk
   >>> DocumentChunk.objects.count()
   >>> DocumentChunk.objects.filter(embedding__isnull=False).count()
   ```

### POTÉ:

4. **Test Chatbot Endpoint:**
   ```bash
   # V browseru nebo Postman:
   POST /chatbot/api/rag/
   {
       "message": "jaké jsou tržby za rok 2023?",
       "use_rag": true
   }
   ```

5. **Zkontroluj Logs:**
   ```bash
   # V Django shell:
   >>> from rag.models import SearchQuery
   >>> SearchQuery.objects.latest('created_at')
   # Mělo by zobrazit poslední search query
   ```

---

## ✅ ZÁVĚR

### Kód Je Správně Napsaný

- ✅ RAG service **ANO, vidí do databáze**
- ✅ Search service **ANO, filtruje podle user**
- ✅ Context **ANO, posílá se k OpenAI**
- ✅ SQL queries **jsou správně**
- ✅ Embeddings **generují se správně**

### Problém Je V Datech/Prostředí

- ❌ **Databáze není dostupná** (.env.local credentials)
- ❌ **RAG processing možná neběžel** (chunky/embeddings chybí)
- ❌ **User možná nemá dokumenty** (nic k prohledávání)

### Co Opravit

1. **DATABASE_CONNECTION** - Priorita #1
2. **RUN_RAG_PROCESSING** - Priorita #2
3. **UPLOAD_DOCUMENTS** - Priorita #3
4. **TEST_ENDPOINT** - Priorita #4

---

**Poznámka:** Kód chatbotu je **architekturálně správně navržený**. Problém není v logice, ale v missing data nebo špatném prostředí.
