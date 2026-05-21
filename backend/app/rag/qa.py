from __future__ import annotations

import re
from typing import List, Tuple

from backend.app.llm.groq import chat_completion
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


def _looks_like_memory_question(query: str) -> bool:
    q = query.lower()
    patterns = [
        "mon premier message",
        "premier message",
        "premiere question",
        "c'est quoi mon premier message",
        "c est quoi mon premier message",
        "dernier message",
        "message precedent",
        "message précédent",
        "اول رسالة",
        "اول سؤال",
        "ما هي اول رسالة",
        "ما هو اول سؤال",
        "رسالة سابقة",
    ]
    return any(p in q for p in patterns)


def _answer_from_history(query: str, history: List[dict]) -> str:
    user_messages = [m["content"] for m in history if m.get("role") == "user"]
    if not user_messages:
        return "لا توجد رسائل سابقة في هذه الجلسة."

    q = query.lower()
    if "dernier" in q or "اخير" in q or "آخر" in q:
        return f"آخر رسالة منك في هذه الجلسة هي: {user_messages[-1]}"

    return f"أول رسالة منك في هذه الجلسة هي: {user_messages[0]}"


def _extract_article_tokens(query: str) -> List[str]:
    q = query.lower()
    tokens = []
    match = re.search(r"(article|الفصل|المادة)\s*(\d+)", q)
    if match:
        num = match.group(2)
        tokens.extend([f"article {num}", f"الفصل {num}", f"المادة {num}"])
    return tokens


def _contexts_contain_any_token(contexts: List[Tuple[str, dict]], tokens: List[str]) -> bool:
    if not tokens:
        return True
    joined = "\n".join([text for text, _ in contexts]).lower()
    normalized = " ".join(joined.split())
    for token in tokens:
        normalized_token = " ".join(token.lower().split())
        if normalized_token and normalized_token in normalized:
            return True
    return False


def _extract_article_snippet(contexts: List[Tuple[str, dict]], article_num: str) -> str:
    joined = "\n".join([text for text, _ in contexts])
    if not joined.strip():
        return ""

    pattern = re.compile(rf"Article\s*{article_num}(?!\d)[\s\S]{{0,1200}}", re.IGNORECASE)
    match = pattern.search(joined)
    if not match:
        return ""

    snippet = match.group(0)
    cutoff = re.search(r"\n\s*Article\s+\d+\b", snippet, re.IGNORECASE)
    if cutoff:
        snippet = snippet[: cutoff.start()]
    return snippet.strip()


def answer_with_rag(query: str, history: List[dict]) -> Tuple[str, List[SourceCitation]]:
    if _looks_like_memory_question(query):
        return _answer_from_history(query, history), []

    article_tokens = _extract_article_tokens(query)
    contexts = search(query, top_k=20 if article_tokens else None)
    if not contexts:
        return "لم يتم العثور على مقاطع ذات صلة في المصادر المتاحة.", []
    if article_tokens:
        if not _contexts_contain_any_token(contexts, article_tokens):
            return "لم يتم العثور على هذا الفصل أو المادة داخل المصادر المحملة.", []

        normalized_tokens = [" ".join(token.lower().split()) for token in article_tokens]
        filtered = []
        for text, meta in contexts:
            normalized_text = " ".join((text or "").lower().split())
            if any(token in normalized_text for token in normalized_tokens):
                filtered.append((text, meta))
        if filtered:
            contexts = filtered

        article_num = re.search(r"(article|الفصل|المادة)\s*(\d+)", query.lower())
        if article_num:
            num = article_num.group(2)
            article_pattern = re.compile(rf"article\s*{num}(?!\d)", re.IGNORECASE)
            contexts = [
                (text, meta)
                for text, meta in contexts
                if article_pattern.search(text or "")
            ] or contexts
            snippet = _extract_article_snippet(contexts, article_num.group(2))
            if snippet:
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
                return snippet, citations

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
