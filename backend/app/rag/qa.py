from __future__ import annotations

from typing import List, Tuple

from backend.app.embeddings.grok import chat_completion
from backend.app.rag.retriever import search
from backend.app.models.schemas import SourceCitation


def _build_prompt(query: str, contexts: List[Tuple[str, dict]], history: List[dict]) -> List[dict]:
    system = (
        "انت مساعد قانوني ذكي متخصص في القوانين التونسية. "
        "أجب باللغة العربية بشكل واضح ومهني، واذكر المراجع مع رقم الصفحة. "
        "إذا لم تجد معلومة كافية، اطلب توضيحا من المستخدم."
    )

    context_text = []
    for text, meta in contexts:
        source = meta.get("source", "")
        page = meta.get("page", "")
        context_text.append(f"[المصدر: {source} | الصفحة: {page}]\n{text}")

    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-6:])

    messages.append(
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    "السياق القانوني:\n" + "\n---\n".join(context_text),
                    "السؤال:\n" + query,
                    "التعليمات: اجعل الإجابة مختصرة ثم أضف قائمة بالمصادر في النهاية.",
                ]
            ),
        }
    )
    return messages


def answer_with_rag(query: str, history: List[dict]) -> Tuple[str, List[SourceCitation]]:
    contexts = search(query)
    messages = _build_prompt(query, contexts, history)
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
