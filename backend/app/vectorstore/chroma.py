from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.app.config import settings


_client = None
_collection = None


def get_collection():
    global _client, _collection

    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(
        path=settings.chroma_dir,
        settings=ChromaSettings(allow_reset=True),
    )
    _collection = _client.get_or_create_collection(name="tunisian_law")
    return _collection
