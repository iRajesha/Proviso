from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from backend.agents.crew import (
    run_cleanup_only,
    run_generate_only,
    run_refinement_draft,
    run_review_only,
)
from backend.llm.oci_genai_llm import chat_with_oci
from backend.services.chat_memory import ChatSession, chat_memory
from backend.services.diagram_service import generate_mermaid_diagram
from backend.services.requirements_guard import (
    RequirementsNotClearError,
    ensure_requirements_clarity,
)

ChatIntent = Literal["auto", "generate", "refine", "review", "cleanup", "chat"]
ResolvedIntent = Literal["generate", "refine", "review", "cleanup", "chat"]


class SessionNotFoundError(ValueError):
    pass


@dataclass
class ClarificationRequired:
    message: str
    missing_details: list[str]
    clarification_questions: list[str]


_GREETING_TOKENS = {
    "hi",
    "hello",
    "hey",
    "yo",
    "hola",
    "thanks",
    "thank you",
}


def _compose_requirements_from_history(session: ChatSession) -> str:
    user_items = [m.content.strip() for m in session.messages if m.role == "user" and m.content.strip()]
    if not user_items:
        return session.requirements_context.strip()
    if len(user_items) == 1:
        return user_items[0]
    return "\n".join(
        [
            user_items[0],
            "",
            "Refinements:",
            *[f"{idx + 1}. {item}" for idx, item in enumerate(user_items[1:])],
        ]
    ).strip()


def _looks_like_small_talk(message: str) -> bool:
    lowered = message.strip().lower()
    if not lowered:
        return False
    normalized = " ".join(lowered.split())
    if normalized in _GREETING_TOKENS:
        return True
    if len(normalized) <= 20 and any(token in normalized for token in _GREETING_TOKENS):
        return True
    return False


def _append_clarification_assistant_message(
    session_id: str,
    clarification: ClarificationRequired,
) -> None:
    questions = "\n".join(f"- {q}" for q in clarification.clarification_questions)
    text = (
        f"{clarification.message}\n"
        "Please clarify:\n"
        f"{questions}"
    ).strip()
    chat_memory.append_message(
        session_id,
        role="assistant",
        content=text,
        intent="generate",
    )


def _resolve_intent(
    session: ChatSession,
    message: str,
    requested_intent: ChatIntent,
) -> ResolvedIntent:
    if requested_intent != "auto":
        return requested_intent  # type: ignore[return-value]

    has_draft = bool(session.generated_terraform.strip() or session.reviewed_terraform.strip())
    if not has_draft:
        if _looks_like_small_talk(message):
            return "chat"
        return "generate"

    lowered = message.strip().lower()
    chat_markers = ("why ", "how ", "what ", "explain", "summary", "difference", "?")
    if lowered.startswith(chat_markers) or lowered.endswith("?"):
        return "chat"

    return "refine"


def create_session(services: Optional[list[str]] = None) -> ChatSession:
    session = chat_memory.create_session(services=services or [])
    chat_memory.append_message(
        session.session_id,
        role="assistant",
        content=(
            "Session initialized. Share requirements to generate Terraform, "
            "then run review and cleanup only when you request them."
        ),
        intent="chat",
    )
    updated = chat_memory.get_session(session.session_id)
    assert updated is not None
    return updated


def get_session(session_id: str) -> ChatSession:
    session = chat_memory.get_session(session_id)
    if not session:
        raise SessionNotFoundError(f"session not found: {session_id}")
    return session


def process_user_message(
    session_id: str,
    message: str,
    *,
    intent: ChatIntent = "auto",
    services: Optional[list[str]] = None,
) -> tuple[ChatSession, ResolvedIntent, Optional[ClarificationRequired]]:
    session = chat_memory.get_session(session_id)
    if not session:
        raise SessionNotFoundError(f"session not found: {session_id}")

    if services is not None:
        session = chat_memory.set_services(session_id, services) or session

    text = message.strip()
    resolved = _resolve_intent(session, text, intent)

    if text:
        session = chat_memory.append_message(
            session_id,
            role="user",
            content=text,
            intent=resolved,
        ) or session

    if resolved == "chat":
        history = [
            {"role": m.role, "content": m.content}
            for m in session.messages[-10:]
            if m.role in {"user", "assistant"}
        ]
        system_prompt = (
            "You are Proviso assistant. Answer briefly and accurately about OCI infra design, "
            "Terraform draft changes, and next refinements. If Terraform exists, keep recommendations "
            "consistent with current reviewed draft."
        )
        if session.reviewed_terraform.strip():
            snapshot = session.reviewed_terraform
        else:
            snapshot = session.generated_terraform
        if snapshot.strip():
            history.append(
                {
                    "role": "system",
                    "content": (
                        "Current Terraform snapshot:\n"
                        f"{snapshot[:5000]}"
                    ),
                }
            )
        assistant_text = chat_with_oci(
            message=text or "Give a brief status update of current infrastructure draft.",
            history=history,
            system_prompt=system_prompt,
        )
        session = chat_memory.append_message(
            session_id,
            role="assistant",
            content=assistant_text.strip(),
            intent="chat",
        ) or session
        final_session = chat_memory.get_session(session_id)
        assert final_session is not None
        return final_session, resolved, None

    if resolved == "generate":
        requirements = _compose_requirements_from_history(session)
        if not requirements:
            raise ValueError("No requirements available to generate infrastructure.")
        try:
            ensure_requirements_clarity(requirements, session.services)
        except RequirementsNotClearError as exc:
            clarification = ClarificationRequired(
                message=exc.message,
                missing_details=exc.missing_details,
                clarification_questions=exc.clarification_questions,
            )
            _append_clarification_assistant_message(session_id, clarification)
            refreshed = chat_memory.get_session(session_id)
            assert refreshed is not None
            return refreshed, resolved, clarification

        generated_tf = run_generate_only(requirements, session.services)
        session = chat_memory.update_requirements_context(session_id, requirements) or session
        session = chat_memory.update_artifacts(
            session_id,
            generated_terraform=generated_tf,
            reviewed_terraform="",
            change_summary="",
            cleanup_script="",
            mermaid_diagram=generate_mermaid_diagram(session.services),
        ) or session
        session = chat_memory.append_message(
            session_id,
            role="assistant",
            content=(
                "Terraform draft generated. Request refinements, then run review/cleanup "
                "when you are ready."
            ),
            intent="generate",
        ) or session
        final_session = chat_memory.get_session(session_id)
        assert final_session is not None
        return final_session, resolved, None

    if resolved == "refine":
        source_draft = session.generated_terraform or session.reviewed_terraform
        if not source_draft.strip():
            requirements = _compose_requirements_from_history(session)
            if not requirements:
                raise ValueError("No requirements available to generate infrastructure.")
            try:
                ensure_requirements_clarity(requirements, session.services)
            except RequirementsNotClearError as exc:
                clarification = ClarificationRequired(
                    message=exc.message,
                    missing_details=exc.missing_details,
                    clarification_questions=exc.clarification_questions,
                )
                _append_clarification_assistant_message(session_id, clarification)
                refreshed = chat_memory.get_session(session_id)
                assert refreshed is not None
                return refreshed, "generate", clarification

            generated_tf = run_generate_only(requirements, session.services)
            session = chat_memory.update_requirements_context(session_id, requirements) or session
            session = chat_memory.update_artifacts(
                session_id,
                generated_terraform=generated_tf,
                reviewed_terraform="",
                change_summary="",
                cleanup_script="",
                mermaid_diagram=generate_mermaid_diagram(session.services),
            ) or session
            session = chat_memory.append_message(
                session_id,
                role="assistant",
                content=(
                    "No draft existed, so a new Terraform draft was generated first. "
                    "Re-send refinement to apply changes."
                ),
                intent="generate",
            ) or session
            final_session = chat_memory.get_session(session_id)
            assert final_session is not None
            return final_session, "generate", None

        refined_tf = run_refinement_draft(
            current_generated_terraform=source_draft,
            refinement_request=text,
            services=session.services,
        )
        session = chat_memory.update_artifacts(
            session_id,
            generated_terraform=refined_tf,
            reviewed_terraform="",  # previous review is now stale
            change_summary="",
            cleanup_script="",  # previous cleanup is now stale
            mermaid_diagram=generate_mermaid_diagram(session.services),
        ) or session
        session = chat_memory.append_message(
            session_id,
            role="assistant",
            content=(
                "Applied refinement to Terraform draft. Run review when you want security "
                "hardening, then run cleanup generation."
            ),
            intent="refine",
        ) or session
        final_session = chat_memory.get_session(session_id)
        assert final_session is not None
        return final_session, resolved, None

    if resolved == "review":
        source = session.generated_terraform or session.reviewed_terraform
        if not source.strip():
            raise ValueError("No Terraform draft available. Generate infrastructure first.")

        reviewed_tf, summary = run_review_only(source)
        session = chat_memory.update_artifacts(
            session_id,
            generated_terraform=session.generated_terraform or source,
            reviewed_terraform=reviewed_tf,
            change_summary=summary,
            cleanup_script="",  # stale after new review
            mermaid_diagram=generate_mermaid_diagram(session.services),
        ) or session
        session = chat_memory.append_message(
            session_id,
            role="assistant",
            content="Review complete. Draft hardened and change summary updated.",
            intent="review",
        ) or session
        final_session = chat_memory.get_session(session_id)
        assert final_session is not None
        return final_session, resolved, None

    # resolved == "cleanup"
    source = session.reviewed_terraform or session.generated_terraform
    if not source.strip():
        raise ValueError("No Terraform available. Generate infrastructure first.")

    cleanup_script = run_cleanup_only(source)
    session = chat_memory.update_artifacts(
        session_id,
        generated_terraform=session.generated_terraform,
        reviewed_terraform=session.reviewed_terraform,
        change_summary=session.change_summary,
        cleanup_script=cleanup_script,
        mermaid_diagram=generate_mermaid_diagram(session.services),
    ) or session
    session = chat_memory.append_message(
        session_id,
        role="assistant",
        content="Cleanup script generated for the current Terraform snapshot.",
        intent="cleanup",
    ) or session
    final_session = chat_memory.get_session(session_id)
    assert final_session is not None
    return final_session, resolved, None
