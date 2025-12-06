"""
RAG URL Configuration
"""

from django.urls import path
from . import views

app_name = 'rag'

urlpatterns = [
    # Semantic search
    path('search/', views.search, name='search'),

    # Chunk operations
    path('chunk/<int:chunk_id>/', views.get_chunk, name='get_chunk'),
    path('chunk/<int:chunk_id>/similar/', views.similar_chunks, name='similar_chunks'),

    # Document chunks
    path('document/<int:document_id>/chunks/', views.document_chunks, name='document_chunks'),
]
