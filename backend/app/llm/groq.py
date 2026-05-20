from __future__ import annotations

from typing import List

import requests

from backend.app.config import settings


GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def chat_completion(messages: List[dict], temperature: float = 0) -> str:
    if settings.llm_provider.lower() != "groq":
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    if not settings.groq_api_key:
        return _fallback_chat(messages, reason="GROQ_API_KEY is not set")

    payload = {
        "model": settings.groq_chat_model,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            json=payload,
            timeout=60,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return _extract_text(data) or _fallback_chat(messages, reason="Empty Groq response")
    except Exception as exc:
        return _fallback_chat(messages, reason=str(exc))


def _extract_text(response: dict) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    return content.strip()


def _fallback_chat(messages: List[dict], reason: str | None = None) -> str:
    user_messages = [m["content"] for m in messages if m.get("role") == "user"]
    last_user = user_messages[-1] if user_messages else ""
    suffix = f" Technical reason: {reason}." if reason else ""
    if "السياق القانوني" in last_user or "السؤال" in last_user:
        return (
            "تعذر الاتصال بـ Groq حاليا، لذلك هذه إجابة محلية أولية اعتمادا على النصوص المسترجعة. "
            "يرجى التحقق من GROQ_API_KEY واسم النموذج للحصول على إجابة أدق مع الاستشهادات."
            + suffix
        )
    return (
        "خطة أولية: 1) تحليل السؤال أو الوثيقة. 2) البحث في المصادر القانونية. "
        "3) تلخيص النتائج. 4) عرض المخاطر والتوصيات."
        + suffix
    )
