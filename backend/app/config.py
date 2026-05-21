from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(".env")


@dataclass
class Settings:
    # Providers
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "chroma")

    # Groq (chat)
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_chat_model: str = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")

    sources_dir: str = os.getenv("SOURCES_DIR", "./sources")
    chroma_dir: str = os.getenv("CHROMA_DIR", "./data/chroma")
    uploads_dir: str = os.getenv("UPLOADS_DIR", "./uploads")

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("TOP_K", "5"))

    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
