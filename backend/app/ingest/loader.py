from __future__ import annotations

import os
from typing import List, Tuple
from pypdf import PdfReader

from backend.app.config import settings
from backend.app.ingest.chunker import chunk_text
from backend.app.vectorstore.chroma import get_collection


def _extract_pdf_text(path: str) -> List[Tuple[int, str]]:
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i + 1, text))
    return pages


def load_pdfs_from_sources() -> int:
    sources = settings.sources_dir
    if not os.path.isdir(sources):
        return 0

    collection = get_collection()
    pdf_names = [name for name in os.listdir(sources) if name.lower().endswith(".pdf")]
    _remove_sources_not_present(collection, set(pdf_names))

    doc_count = 0
    for name in pdf_names:
        path = os.path.join(sources, name)
        pages = _extract_pdf_text(path)

        chunks = []
        metadatas = []
        ids = []
        for page_num, text in pages:
            for idx, chunk in enumerate(chunk_text(text)):
                chunk_id = f"{name}:{page_num}:{idx}"
                chunks.append(f"[SOURCE: {name}]\n{chunk}")
                metadatas.append({"source": name, "page": page_num, "chunk_id": chunk_id})
                ids.append(chunk_id)

        if chunks:
            collection.delete(where={"source": name})
            collection.upsert(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
            )
            doc_count += 1

    return doc_count


def _remove_sources_not_present(collection, current_sources: set[str]) -> None:
    existing = collection.get(include=["metadatas"])
    metadatas = existing.get("metadatas") or []

    stale_sources = {
        meta.get("source")
        for meta in metadatas
        if meta and meta.get("source") and meta.get("source") not in current_sources
    }
    for source in stale_sources:
        collection.delete(where={"source": source})
