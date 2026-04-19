from __future__ import annotations

from typing import Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.chat_service import (
    ChatIntent,
    SessionNotFoundError,
    create_session,
    get_session,
    process_user_message,
)

router = APIRouter()


class SessionCreateRequest(BaseModel):
    services: list[str] = []


class ChatMessageRequest(BaseModel):
    message: str = ""
    intent: ChatIntent = "auto"
    services: Optional[list[str]] = None


class SessionResponse(BaseModel):
    session_id: str
    services: list[str]
    created_at: str
    updated_at: str
    requirements_context: str
    generated_terraform: str
    reviewed_terraform: str
    change_summary: str
    cleanup_script: str
    mermaid_diagram: str
    messages: list[dict]


class ChatMessageResponse(SessionResponse):
    resolved_intent: Literal["generate", "refine", "review", "cleanup", "chat"]
    clarification: Optional[dict] = None


@router.post("/chat/sessions", response_model=SessionResponse)
async def create_chat_session(req: SessionCreateRequest):
    session = create_session(services=req.services)
    return SessionResponse(**session.to_dict())


@router.get("/chat/sessions/{session_id}", response_model=SessionResponse)
async def get_chat_session(session_id: str):
    try:
        session = get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")
    return SessionResponse(**session.to_dict())


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def post_chat_message(session_id: str, req: ChatMessageRequest):
    try:
        session, resolved_intent, clarification = process_user_message(
            session_id=session_id,
            message=req.message,
            intent=req.intent,
            services=req.services,
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="session not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    payload = {
        **session.to_dict(),
        "resolved_intent": resolved_intent,
        "clarification": None,
    }
    if clarification:
        payload["clarification"] = {
            "message": clarification.message,
            "missing_details": clarification.missing_details,
            "clarification_questions": clarification.clarification_questions,
        }
    return ChatMessageResponse(**payload)
