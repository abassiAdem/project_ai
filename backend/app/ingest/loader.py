from __future__ import annotations

import os
from typing import List, Tuple
from pypdf import PdfReader

from backend.app.config import settings
from backend.app.ingest.chunker import chunk_text
from backend.app.vectorstore.chroma import get_collection
from backend.app.embeddings.grok import embed_texts


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

    doc_count = 0
    for name in os.listdir(sources):
        if not name.lower().endswith(".pdf"):
            continue
        path = os.path.join(sources, name)
        pages = _extract_pdf_text(path)

        chunks = []
        metadatas = []
        ids = []
        for page_num, text in pages:
            for idx, chunk in enumerate(chunk_text(text)):
                chunk_id = f"{name}:{page_num}:{idx}"
                chunks.append(chunk)
                metadatas.append({"source": name, "page": page_num, "chunk_id": chunk_id})
                ids.append(chunk_id)

        if chunks:
            embeddings = embed_texts(chunks)
            collection.upsert(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            doc_count += 1

    return doc_count
