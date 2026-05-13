from __future__ import annotations

import hashlib
import math
from typing import List
import requests

from backend.app.config import settings


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.grok_api_key}",
        "Content-Type": "application/json",
    }


def _local_embedding(text: str, dimensions: int = 256) -> List[float]:
    """Deterministic fallback embedding when Grok is unavailable."""
    vector = [0.0] * dimensions
    tokens = [t for t in text.lower().split() if t]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % dimensions
        vector[index] += 1.0

    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not settings.grok_api_key:
        return [_local_embedding(text) for text in texts]

    url = f"{settings.grok_base_url}/embeddings"
    payload = {"model": settings.grok_embed_model, "input": texts}
    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        if embeddings:
            return embeddings
    except Exception:
        pass

    return [_local_embedding(text) for text in texts]


def chat_completion(messages: List[dict], temperature: float = 0.2) -> str:
    if not settings.grok_api_key:
        return _fallback_chat(messages)

    url = f"{settings.grok_base_url}/chat/completions"
    payload = {
        "model": settings.grok_chat_model,
        "messages": messages,
        "temperature": temperature,
    }
    try:
        resp = requests.post(url, headers=_headers(), json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        return _fallback_chat(messages, reason=str(exc))


def _fallback_chat(messages: List[dict], reason: str | None = None) -> str:
    user_messages = [m["content"] for m in messages if m.get("role") == "user"]
    last_user = user_messages[-1] if user_messages else ""
    suffix = f" السبب التقني: {reason}." if reason else ""
    if "سياق قانوني" in last_user or "السؤال" in last_user:
        return (
            "تعذر الاتصال بخدمة Grok حاليا، لذلك هذه إجابة محلية أولية اعتمادا على النصوص المسترجعة. "
            "يرجى التحقق من GROK_API_KEY واسم النموذج للحصول على إجابة أدق مع الاستشهادات." + suffix
        )
    return (
        "خطة أولية: 1) تحليل السؤال أو الوثيقة. 2) البحث في المصادر القانونية. "
        "3) تلخيص النتائج. 4) عرض المخاطر والتوصيات." + suffix
    )
