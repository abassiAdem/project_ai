from __future__ import annotations

from typing import List
from backend.app.config import settings


def chunk_text(text: str) -> List[str]:
    size = settings.chunk_size
    overlap = settings.chunk_overlap

    clean = " ".join(text.split())
    if not clean:
        return []

    chunks = []
    start = 0
    while start < len(clean):
        end = min(start + size, len(clean))
        chunks.append(clean[start:end])
        start = max(end - overlap, end)

    return chunks
