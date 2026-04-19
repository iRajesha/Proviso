from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Optional
import copy
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChatMessage:
    id: str
    role: str
    content: str
    created_at: str
    intent: Optional[str] = None


@dataclass
class ChatSession:
    session_id: str
    services: list[str]
    created_at: str
    updated_at: str
    messages: list[ChatMessage] = field(default_factory=list)
    requirements_context: str = ""
    generated_terraform: str = ""
    reviewed_terraform: str = ""
    change_summary: str = ""
    cleanup_script: str = ""
    mermaid_diagram: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "services": list(self.services),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "requirements_context": self.requirements_context,
            "generated_terraform": self.generated_terraform,
            "reviewed_terraform": self.reviewed_terraform,
            "change_summary": self.change_summary,
            "cleanup_script": self.cleanup_script,
            "mermaid_diagram": self.mermaid_diagram,
            "messages": [asdict(m) for m in self.messages],
        }


class InlineChatMemory:
    """
    Process-local temporary memory for chat sessions.
    Designed for iterative UX context; data is intentionally ephemeral.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}
        self._lock = RLock()

    def create_session(self, services: Optional[list[str]] = None) -> ChatSession:
        now = _now_iso()
        session = ChatSession(
            session_id=str(uuid.uuid4()),
            services=list(services or []),
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return copy.deepcopy(session)

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            return copy.deepcopy(session) if session else None

    def _get_session_ref(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def set_services(self, session_id: str, services: list[str]) -> Optional[ChatSession]:
        with self._lock:
            session = self._get_session_ref(session_id)
            if not session:
                return None
            session.services = list(services)
            session.updated_at = _now_iso()
            return copy.deepcopy(session)

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
    ) -> Optional[ChatSession]:
        with self._lock:
            session = self._get_session_ref(session_id)
            if not session:
                return None
            session.messages.append(
                ChatMessage(
                    id=str(uuid.uuid4()),
                    role=role,
                    content=content,
                    created_at=_now_iso(),
                    intent=intent,
                )
            )
            session.updated_at = _now_iso()
            return copy.deepcopy(session)

    def update_requirements_context(
        self,
        session_id: str,
        requirements_context: str,
    ) -> Optional[ChatSession]:
        with self._lock:
            session = self._get_session_ref(session_id)
            if not session:
                return None
            session.requirements_context = requirements_context
            session.updated_at = _now_iso()
            return copy.deepcopy(session)

    def update_artifacts(
        self,
        session_id: str,
        *,
        generated_terraform: str,
        reviewed_terraform: str,
        change_summary: str,
        cleanup_script: str,
        mermaid_diagram: str,
    ) -> Optional[ChatSession]:
        with self._lock:
            session = self._get_session_ref(session_id)
            if not session:
                return None
            session.generated_terraform = generated_terraform
            session.reviewed_terraform = reviewed_terraform
            session.change_summary = change_summary
            session.cleanup_script = cleanup_script
            session.mermaid_diagram = mermaid_diagram
            session.updated_at = _now_iso()
            return copy.deepcopy(session)


chat_memory = InlineChatMemory()
