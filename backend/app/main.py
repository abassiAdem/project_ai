from __future__ import annotations

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.models.schemas import (
    ChatRequest,
    ChatResponse,
    AgentRequest,
    AgentResponse,
    ModifyRequest,
    ModifyResponse,
)
from backend.app.ingest.loader import load_pdfs_from_sources
from backend.app.rag.qa import answer_with_rag
from backend.app.agent.planner import run_agent
from backend.app.memory.conversation import memory_store
from backend.app.agent.tools.contract_analyzer import save_upload, modify_contract


app = FastAPI(title="LegalMind Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def root() -> dict:
    return {
        "name": "LegalMind Agent API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.post("/ingest")
def ingest_sources() -> dict:
    if not os.path.isdir(settings.sources_dir):
        raise HTTPException(status_code=400, detail="Sources directory not found")
    count = load_pdfs_from_sources()
    return {"status": "ok", "documents_indexed": count}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    history = memory_store.get(req.session_id)
    answer, citations = answer_with_rag(req.message, history)
    memory_store.append(req.session_id, "user", req.message)
    memory_store.append(req.session_id, "assistant", answer)
    return ChatResponse(answer=answer, citations=citations)


@app.post("/agent/analyze", response_model=AgentResponse)
def agent_analyze(req: AgentRequest) -> AgentResponse:
    history = memory_store.get(req.session_id)
    response = run_agent(req.message, history, req.document_id)
    memory_store.append(req.session_id, "user", req.message)
    memory_store.append(req.session_id, "assistant", response.answer)
    return response


@app.post("/uploads")
def upload_document(file: UploadFile = File(...)) -> dict:
    document_id = save_upload(file)
    return {"status": "ok", "document_id": document_id}


@app.post("/agent/modify", response_model=ModifyResponse)
def modify_document(req: ModifyRequest) -> ModifyResponse:
    if not req.document_id:
        return ModifyResponse(status="error", message="يرجى رفع عقد قبل التعديل.")

    result = modify_contract(req.document_id, req.instructions)
    if result.get("status") != "ok":
        return ModifyResponse(status="error", message=result.get("message", "تعذر تعديل العقد."))

    return ModifyResponse(status="ok", file_id=result.get("file_id"))


@app.get("/downloads/{file_id}")
def download_document(file_id: str) -> FileResponse:
    safe_name = os.path.basename(file_id)
    if safe_name != file_id:
        raise HTTPException(status_code=400, detail="Invalid file id")

    path = os.path.join(settings.uploads_dir, "modified", safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, filename=safe_name)
