from __future__ import annotations

from typing import List, Tuple

from backend.app.rag.retriever import search
from backend.app.embeddings.gemini import chat_completion
from backend.app.models.schemas import SourceCitation


def legal_search_tool(query: str) -> Tuple[str, List[SourceCitation]]:
    contexts = search(query)
    context_text = []
    for text, meta in contexts:
        source = meta.get("source", "")
        page = meta.get("page", "")
        context_text.append(f"[المصدر: {source} | الصفحة: {page}]\n{text}")

    messages = [
        {
            "role": "system",
            "content": "انت مساعد قانوني. استخرج الاجابة من النصوص المرفقة فقط.",
        },
        {
            "role": "user",
            "content": "\n---\n".join(context_text) + "\n\nالسؤال:\n" + query,
        },
    ]

    answer = chat_completion(messages)

    citations = []
    for text, meta in contexts:
        citations.append(
            SourceCitation(
                source=meta.get("source", ""),
                page=int(meta.get("page", 0)),
                chunk_id=meta.get("chunk_id", ""),
                text=text,
            )
        )

    return answer, citations
