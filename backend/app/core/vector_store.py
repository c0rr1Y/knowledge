"""ChromaDB vector store wrapper."""

from typing import Optional
import hashlib
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings
import os

_vector_store: Optional[chromadb.PersistentClient] = None


def get_vector_store() -> chromadb.PersistentClient:
    """Get or create the ChromaDB persistent client singleton."""
    global _vector_store
    if _vector_store is None:
        persist_dir = os.path.normpath(os.path.abspath(settings.chroma_persist_dir))
        os.makedirs(persist_dir, exist_ok=True)
        _vector_store = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _vector_store


def get_collection_name(tenant_id: str, kb_id: str) -> str:
    """Build a valid ChromaDB collection name from tenant and KB IDs.

    ChromaDB limits collection names to 3-63 chars, alphanumeric, underscores, hyphens.
    We hash the IDs to stay within limits while avoiding collisions.
    """
    combined = f"{tenant_id}_{kb_id}"
    short_hash = hashlib.md5(combined.encode()).hexdigest()[:16]
    return f"kb_{short_hash}"
