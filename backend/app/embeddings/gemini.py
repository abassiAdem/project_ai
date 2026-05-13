from __future__ import annotations

from typing import List, Sequence

import requests

from backend.app.config import settings

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _base_url() -> str:
    return DEFAULT_GEMINI_BASE_URL


def _request(url: str, payload: dict) -> dict:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    response = requests.post(
        url,
        json=payload,
        timeout=60,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def _prepare_query(text: str) -> str:
    return f"task: search result | query: {text}"


def _prepare_document(text: str, title: str | None = None) -> str:
    safe_title = title or "none"
    return f"title: {safe_title} | text: {text}"


def _extract_embedding(payload: dict) -> List[float]:
    if isinstance(payload.get("embedding"), dict):
        values = payload["embedding"].get("values")
        if values:
            return list(values)

    embeddings = payload.get("embeddings") or []
    if embeddings:
        values = embeddings[0].get("values")
        if values:
            return list(values)

    raise RuntimeError("Gemini embedding response did not contain values")


def embed_query(text: str) -> List[float]:
    payload = {
        "content": {"parts": [{"text": _prepare_query(text)}]},
    }
    response = _request(
        f"{_base_url()}/models/{settings.gemini_embed_model}:embedContent?key={settings.gemini_api_key}",
        payload,
    )
    return _extract_embedding(response)


def embed_documents(texts: Sequence[str], titles: Sequence[str | None] | None = None) -> List[List[float]]:
    title_list = list(titles) if titles is not None else [None] * len(texts)
    embeddings: List[List[float]] = []

    for text, title in zip(texts, title_list):
        payload = {
            "content": {"parts": [{"text": _prepare_document(text, title)}]},
        }
        response = _request(
            f"{_base_url()}/models/{settings.gemini_embed_model}:embedContent?key={settings.gemini_api_key}",
            payload,
        )
        embeddings.append(_extract_embedding(response))

    return embeddings


def chat_completion(messages: List[dict], temperature: float = 0.2) -> str:
    prompt = _messages_to_prompt(messages)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }

    try:
        response = _request(
            f"{_base_url()}/models/{settings.gemini_chat_model}:generateContent?key={settings.gemini_api_key}",
            payload,
        )
        return _extract_text(response) or _fallback_chat(messages, reason="Empty Gemini response")
    except Exception as exc:
        return _fallback_chat(messages, reason=str(exc))


def _messages_to_prompt(messages: List[dict]) -> str:
    lines: List[str] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    return "\n\n".join(lines)


def _extract_text(response: dict) -> str:
    candidates = response.get("candidates") or []
    if not candidates:
        return ""

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return "".join(texts).strip()


def _fallback_chat(messages: List[dict], reason: str | None = None) -> str:
    user_messages = [m["content"] for m in messages if m.get("role") == "user"]
    last_user = user_messages[-1] if user_messages else ""
    suffix = f" السبب التقني: {reason}." if reason else ""
    if "سياق قانوني" in last_user or "السؤال" in last_user:
        return (
            "تعذر الاتصال بـ Gemini حاليا، لذلك هذه إجابة محلية أولية اعتمادا على النصوص المسترجعة. "
            "يرجى التحقق من GEMINI_API_KEY واسم النموذج للحصول على إجابة أدق مع الاستشهادات."
            + suffix
        )
    return (
        "خطة أولية: 1) تحليل السؤال أو الوثيقة. 2) البحث في المصادر القانونية. "
        "3) تلخيص النتائج. 4) عرض المخاطر والتوصيات." + suffix
    )
