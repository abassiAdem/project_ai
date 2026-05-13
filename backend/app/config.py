from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(".env")
if not os.getenv("GROK_API_KEY"):
    load_dotenv(".env.example", override=False)


@dataclass
class Settings:
    grok_api_key: str = os.getenv("GROK_API_KEY", "")
    grok_base_url: str = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
    grok_chat_model: str = os.getenv("GROK_CHAT_MODEL", "grok-2")
    grok_embed_model: str = os.getenv("GROK_EMBED_MODEL", "grok-2-embedding")

    sources_dir: str = os.getenv("SOURCES_DIR", "./sources")
    chroma_dir: str = os.getenv("CHROMA_DIR", "./data/chroma")
    uploads_dir: str = os.getenv("UPLOADS_DIR", "./uploads")

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("TOP_K", "5"))

    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
