"""
RAG API Views

Endpoints for semantic search and document retrieval.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

from rag.services import SemanticSearchService
from rag.models import DocumentChunk
from ingest.models import Document

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def search(request):
    """
    Semantic search endpoint.

    POST /rag/search/
    Body: {
        "query": "search query text",
        "limit": 10,  // optional
        "similarity_threshold": 0.7,  // optional
        "document_id": 123  // optional - search within specific document
    }

    Returns: {
        "success": true,
        "results": [
            {
                "chunk_id": 1,
                "document_id": 123,
                "content": "chunk text",
                "score": 0.95,
                "rank": 1,
                "document": {
                    "id": 123,
                    "filename": "doc.pdf",
                    "year": 2024,
                    "doc_type": "income_statement"
                }
            }
        ],
        "count": 5,
        "query": "search query text"
    }
    """
    try:
        # Parse request body
        body = json.loads(request.body)
        query_text = body.get('query', '').strip()

        if not query_text:
            return JsonResponse({
                'success': False,
                'error': 'Query text is required'
            }, status=400)

        limit = body.get('limit', 10)
        similarity_threshold = body.get('similarity_threshold', 0.7)
        document_id = body.get('document_id')

        # Initialize search service
        search_service = SemanticSearchService()

        # Perform search
        if document_id:
            # Search within specific document
            try:
                document = Document.objects.get(id=document_id, owner=request.user)
                hits = search_service.search_by_document(
                    query=query_text,
                    document_id=document_id,
                    limit=limit,
                )
            except Document.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Document not found or access denied'
                }, status=404)
        else:
            # Search within user's documents
            hits = search_service.search_by_user(
                query=query_text,
                user=request.user,
                limit=limit,
            )

        # Format results
        results = []
        for hit in hits:
            results.append({
                'chunk_id': hit.chunk.id,
                'document_id': hit.chunk.document.id,
                'content': hit.chunk.content,
                'score': hit.score,
                'rank': hit.rank,
                'document': {
                    'id': hit.chunk.document.id,
                    'filename': hit.chunk.document.filename,
                    'year': hit.chunk.document.year,
                    'doc_type': hit.chunk.document.doc_type,
                }
            })

        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results),
            'query': query_text,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)

    except Exception as e:
        logger.error(f'Search error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_chunk(request, chunk_id):
    """
    Get specific chunk by ID.

    GET /rag/chunk/<chunk_id>/

    Returns: {
        "success": true,
        "chunk": {
            "id": 1,
            "content": "chunk text",
            "chunk_index": 0,
            "token_count": 500,
            "char_count": 2000,
            "document": {...}
        }
    }
    """
    try:
        chunk = DocumentChunk.objects.select_related('document').get(
            id=chunk_id,
            document__owner=request.user
        )

        return JsonResponse({
            'success': True,
            'chunk': {
                'id': chunk.id,
                'content': chunk.content,
                'chunk_index': chunk.chunk_index,
                'token_count': chunk.token_count,
                'char_count': chunk.char_count,
                'document': {
                    'id': chunk.document.id,
                    'filename': chunk.document.filename,
                    'year': chunk.document.year,
                    'doc_type': chunk.document.doc_type,
                }
            }
        })

    except DocumentChunk.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Chunk not found or access denied'
        }, status=404)

    except Exception as e:
        logger.error(f'Get chunk error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def similar_chunks(request, chunk_id):
    """
    Find similar chunks to a given chunk.

    GET /rag/chunk/<chunk_id>/similar/?limit=5

    Returns: {
        "success": true,
        "results": [...],
        "count": 5
    }
    """
    try:
        # Get the source chunk
        chunk = DocumentChunk.objects.select_related('document').get(
            id=chunk_id,
            document__owner=request.user
        )

        limit = int(request.GET.get('limit', 5))

        # Find similar chunks
        search_service = SemanticSearchService()
        hits = search_service.get_similar_chunks(
            chunk=chunk,
            limit=limit,
            exclude_same_document=True,
        )

        # Format results
        results = []
        for hit in hits:
            results.append({
                'chunk_id': hit.chunk.id,
                'document_id': hit.chunk.document.id,
                'content': hit.chunk.content,
                'score': hit.score,
                'rank': hit.rank,
                'document': {
                    'id': hit.chunk.document.id,
                    'filename': hit.chunk.document.filename,
                    'year': hit.chunk.document.year,
                    'doc_type': hit.chunk.document.doc_type,
                }
            })

        return JsonResponse({
            'success': True,
            'results': results,
            'count': len(results),
        })

    except DocumentChunk.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Chunk not found or access denied'
        }, status=404)

    except Exception as e:
        logger.error(f'Similar chunks error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def document_chunks(request, document_id):
    """
    Get all chunks for a document.

    GET /rag/document/<document_id>/chunks/

    Returns: {
        "success": true,
        "chunks": [...],
        "count": 10
    }
    """
    try:
        # Verify document ownership
        document = Document.objects.get(id=document_id, owner=request.user)

        # Get all chunks
        chunks = DocumentChunk.objects.filter(document=document).order_by('chunk_index')

        # Format results
        chunk_list = []
        for chunk in chunks:
            chunk_list.append({
                'id': chunk.id,
                'chunk_index': chunk.chunk_index,
                'content': chunk.content,
                'token_count': chunk.token_count,
                'char_count': chunk.char_count,
                'has_embedding': chunk.embedding is not None,
            })

        return JsonResponse({
            'success': True,
            'chunks': chunk_list,
            'count': len(chunk_list),
            'document': {
                'id': document.id,
                'filename': document.filename,
                'year': document.year,
                'doc_type': document.doc_type,
            }
        })

    except Document.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Document not found or access denied'
        }, status=404)

    except Exception as e:
        logger.error(f'Document chunks error: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)
