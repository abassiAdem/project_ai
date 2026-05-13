from __future__ import annotations

from typing import List, Tuple

from backend.app.config import settings
from backend.app.vectorstore.chroma import get_collection
from backend.app.embeddings.grok import embed_texts


def search(query: str, top_k: int | None = None) -> List[Tuple[str, dict]]:
    collection = get_collection()
    query_emb = embed_texts([query])[0]
    k = top_k or settings.top_k

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=k,
        include=["documents", "metadatas"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    return list(zip(docs, metas))
