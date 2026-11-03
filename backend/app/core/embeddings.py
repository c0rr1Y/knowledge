"""Embedding model wrapper using sentence-transformers (bge-large-zh-v1.5)."""

from sentence_transformers import SentenceTransformer
from app.config import settings

from typing import Optional

_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or create the embedding model singleton (GPU if available)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            settings.embedding_model,
            device="cuda",  # Use NVIDIA GPU (RTX 4070)
        )
    return _embedding_model
