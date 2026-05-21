from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class SourceCitation(BaseModel):
    source: str
    page: int
    chunk_id: str
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[SourceCitation]


class AgentRequest(BaseModel):
    session_id: str
    message: str
    document_id: Optional[str] = None


class AgentResponse(BaseModel):
    plan: List[str]
    answer: str
    citations: List[SourceCitation]
    notes: List[str]


class ModifyRequest(BaseModel):
    session_id: str
    instructions: str
    document_id: Optional[str] = None


class ModifyResponse(BaseModel):
    status: str
    file_id: Optional[str] = None
    message: Optional[str] = None
