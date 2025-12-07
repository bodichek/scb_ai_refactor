"""
Diagnostický skript pro testování RAG chatbot funkcionality
"""

import os
import django
import sys
from pathlib import Path

# Django setup
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

from django.contrib.auth import get_user_model
from rag.models import DocumentChunk
from rag.services import SemanticSearchService, EmbeddingService
from chatbot.services import RAGChatService
from ingest.models import Document

User = get_user_model()


def print_section(title):
    """Print section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_1_database_connection():
    """Test 1: PostgreSQL a pgvector připojení"""
    print_section("TEST 1: Databázové připojení")

    from django.db import connection

    try:
        with connection.cursor() as cursor:
            # Test pgvector extension
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            result = cursor.fetchone()

            if result:
                print("✅ pgvector extension je nainstalována")
                print(f"   Version: {result[1] if len(result) > 1 else 'N/A'}")
            else:
                print("❌ pgvector extension NENÍ nainstalována!")
                return False

            # Test RAG tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'rag_%';
            """)
            tables = cursor.fetchall()

            print(f"\n📊 RAG tabulky ({len(tables)}):")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                count = cursor.fetchone()[0]
                print(f"   - {table[0]}: {count} řádků")

            return True

    except Exception as e:
        print(f"❌ Chyba připojení: {e}")
        return False


def test_2_document_chunks():
    """Test 2: DocumentChunk data v databázi"""
    print_section("TEST 2: DocumentChunk Data")

    try:
        total_chunks = DocumentChunk.objects.count()
        chunks_with_embeddings = DocumentChunk.objects.filter(
            embedding__isnull=False
        ).count()

        print(f"📄 Celkem chunků: {total_chunks}")
        print(f"🧠 Chunky s embeddings: {chunks_with_embeddings}")

        if total_chunks == 0:
            print("\n⚠️  ŽÁDNÉ CHUNKY V DATABÁZI!")
            print("   Spusť: python manage.py process_documents_rag")
            return False

        if chunks_with_embeddings == 0:
            print("\n⚠️  ŽÁDNÉ EMBEDDINGS!")
            print("   Zkontroluj, zda běžel embedding proces")
            return False

        # Sample chunk
        sample = DocumentChunk.objects.filter(embedding__isnull=False).first()
        if sample:
            print(f"\n📝 Ukázkový chunk (ID: {sample.id}):")
            print(f"   Dokument: {sample.document.filename}")
            print(f"   Rok: {sample.document.year}")
            print(f"   Index: {sample.chunk_index}")
            print(f"   Content: {sample.content[:100]}...")
            print(f"   Has embedding: {'✅' if sample.embedding else '❌'}")

            # Check embedding dimension
            if sample.embedding:
                from rag.services.embedding_service import EmbeddingService
                emb_service = EmbeddingService()
                print(f"   Embedding dimension: {len(sample.embedding)} (očekáváno: {emb_service.dimension})")

        return chunks_with_embeddings > 0

    except Exception as e:
        print(f"❌ Chyba: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_semantic_search():
    """Test 3: Semantic Search funkcionalita"""
    print_section("TEST 3: Semantic Search")

    try:
        # Get a test user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ Žádný aktivní uživatel nenalezen!")
            return False

        print(f"👤 Test user: {user.username} (ID: {user.id})")

        # Check user documents
        user_docs = Document.objects.filter(owner=user).count()
        user_chunks = DocumentChunk.objects.filter(document__owner=user).count()
        user_chunks_emb = DocumentChunk.objects.filter(
            document__owner=user,
            embedding__isnull=False
        ).count()

        print(f"📄 Dokumenty uživatele: {user_docs}")
        print(f"📦 Chunky uživatele: {user_chunks}")
        print(f"🧠 Chunky s embeddings: {user_chunks_emb}")

        if user_chunks_emb == 0:
            print("\n⚠️  Uživatel nemá žádné chunky s embeddings!")
            print("   RAG search nebude fungovat pro tohoto uživatele")
            return False

        # Test search
        print("\n🔍 Testování semantic search...")
        search_service = SemanticSearchService()

        test_queries = [
            "jaké jsou tržby?",
            "kolik je zisk?",
            "cash flow",
        ]

        for query in test_queries:
            print(f"\n   Query: '{query}'")
            results = search_service.search_by_user(
                query=query,
                user=user,
                limit=3,
            )

            print(f"   Výsledky: {len(results)}")
            for i, hit in enumerate(results, 1):
                print(f"      {i}. Doc: {hit.chunk.document.filename} "
                      f"({hit.chunk.document.year}) "
                      f"[score: {hit.score:.3f}]")
                print(f"         Content: {hit.chunk.content[:80]}...")

        return len(results) > 0

    except Exception as e:
        print(f"❌ Chyba: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_rag_chat_service():
    """Test 4: RAG Chat Service"""
    print_section("TEST 4: RAG Chat Service")

    try:
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ Žádný uživatel!")
            return False

        print(f"👤 Test user: {user.username}")

        # Initialize RAG service
        rag_service = RAGChatService()
        print("✅ RAGChatService inicializován")

        # Test context retrieval
        test_query = "jaké jsou finanční výsledky za poslední rok?"

        print(f"\n🔍 Test query: '{test_query}'")
        print("   Získávám kontext...")

        context = rag_service.retrieve_context(
            query=test_query,
            user=user,
        )

        print(f"\n📊 Výsledek:")
        print(f"   Has context: {context['has_context']}")
        print(f"   Chunks: {len(context['chunks'])}")
        print(f"   Sources: {len(context['sources'])}")

        if context['has_context']:
            print(f"\n📝 Context text:")
            print(f"   {context['context_text'][:200]}...")

            print(f"\n📄 Zdroje:")
            for source in context['sources']:
                print(f"      - {source['document_name']} ({source['year']}) "
                      f"[similarity: {source['similarity']:.3f}]")
        else:
            print("\n⚠️  Žádný kontext nenalezen!")

        # Test prompt building
        print(f"\n🤖 Generování RAG response...")
        rag_result = rag_service.generate_rag_response(
            query=test_query,
            user=user,
        )

        print(f"\n   Has RAG context: {rag_result['has_rag_context']}")
        print(f"   Sources: {len(rag_result['sources'])}")
        print(f"\n   Prompt pro LLM:")
        print(f"   {rag_result['prompt'][:300]}...")

        return rag_result['has_rag_context']

    except Exception as e:
        print(f"❌ Chyba: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_openai_connection():
    """Test 5: OpenAI API připojení"""
    print_section("TEST 5: OpenAI API")

    try:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY není nastavena!")
            return False

        print(f"🔑 API Key: {api_key[:20]}...{api_key[-5:]}")

        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client inicializován")

        # Test embeddings
        print("\n🧪 Testování embeddings API...")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="test query"
        )

        embedding = response.data[0].embedding
        print(f"✅ Embedding vygenerován: {len(embedding)} dimensions")

        # Test chat completion
        print("\n🧪 Testování chat API...")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Řekni pouze 'test OK'"}
            ],
            max_tokens=10,
        )

        response_text = completion.choices[0].message.content.strip()
        print(f"✅ Chat response: {response_text}")

        return True

    except Exception as e:
        print(f"❌ Chyba: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_full_rag_flow():
    """Test 6: Kompletní RAG flow (simulace chatbot requestu)"""
    print_section("TEST 6: Kompletní RAG Flow")

    try:
        from openai import OpenAI
        from chatbot.services import RAGChatService

        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ Žádný uživatel!")
            return False

        print(f"👤 User: {user.username}")

        # Initialize services
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY není nastavena!")
            return False

        client = OpenAI(api_key=api_key)
        rag_service = RAGChatService()

        # User query
        query = "Jaké byly tržby v roce 2023?"
        print(f"\n💬 Dotaz: '{query}'")

        # Step 1: RAG context retrieval
        print("\n1️⃣  Získávání RAG kontextu...")
        rag_result = rag_service.generate_rag_response(
            query=query,
            user=user,
        )

        has_context = rag_result['has_rag_context']
        print(f"   Has context: {has_context}")
        print(f"   Sources: {len(rag_result['sources'])}")

        if has_context:
            for source in rag_result['sources'][:3]:
                print(f"      - {source['document_name']} ({source['year']})")

        # Step 2: LLM call with context
        print("\n2️⃣  Volání OpenAI s kontextem...")
        messages = [
            {"role": "system", "content": "Jsi finanční analytik. Odpovídej česky."},
            {"role": "user", "content": rag_result['prompt']},
        ]

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )

        response = completion.choices[0].message.content.strip()

        # Step 3: Format response with sources
        print("\n3️⃣  Formátování odpovědi...")
        if has_context:
            formatted = rag_service.format_response_with_sources(
                response=response,
                sources=rag_result['sources'],
            )
            final_response = formatted['response']
        else:
            final_response = response

        print(f"\n✅ FINÁLNÍ ODPOVĚĎ:")
        print(f"{'='*60}")
        print(final_response)
        print(f"{'='*60}")

        return True

    except Exception as e:
        print(f"❌ Chyba: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  RAG CHATBOT DIAGNOSTIKA")
    print("="*60)

    results = {}

    tests = [
        ("Database Connection", test_1_database_connection),
        ("Document Chunks", test_2_document_chunks),
        ("Semantic Search", test_3_semantic_search),
        ("RAG Chat Service", test_4_rag_chat_service),
        ("OpenAI API", test_5_openai_connection),
        ("Full RAG Flow", test_6_full_rag_flow),
    ]

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except KeyboardInterrupt:
            print("\n\n⚠️  Test přerušen uživatelem")
            break
        except Exception as e:
            print(f"\n❌ Neočekávaná chyba v testu '{name}': {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Summary
    print_section("SOUHRN TESTŮ")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\n{'='*60}")
    print(f"Výsledek: {passed}/{total} testů prošlo")
    print(f"{'='*60}\n")

    if passed == total:
        print("🎉 VŠECHNY TESTY PROŠLY! RAG chatbot by měl fungovat správně.")
    else:
        print("⚠️  NĚKTERÉ TESTY SELHALY. Zkontroluj chyby výše.")
        print("\nTipy na řešení:")
        print("1. Spusť RAG processing: python manage.py process_documents_rag")
        print("2. Zkontroluj .env soubor (OPENAI_API_KEY)")
        print("3. Zkontroluj PostgreSQL připojení a pgvector extension")
        print("4. Zkontroluj, že uživatel má nahrané dokumenty")


if __name__ == "__main__":
    main()
