import logging
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.agents.crew import run_generate_only
from backend.db.repositories import GenerationLogRepository
from backend.services.requirements_guard import (
    RequirementsNotClearError,
    ensure_requirements_clarity,
)

router = APIRouter()
_log_repo = GenerationLogRepository()
_logger = logging.getLogger(__name__)


class GenerateRequest(BaseModel):
    requirements: str
    services: list[str] = []


class GenerateResponse(BaseModel):
    session_id: str
    generated_terraform: str
    reviewed_terraform: str
    change_summary: str
    cleanup_script: str
    mermaid_diagram: str


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    if not req.requirements.strip():
        raise HTTPException(status_code=400, detail="requirements cannot be empty")

    try:
        ensure_requirements_clarity(req.requirements, req.services)
    except RequirementsNotClearError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": exc.message,
                "missing_details": exc.missing_details,
                "clarification_questions": exc.clarification_questions,
            },
        )

    session_id = str(uuid.uuid4())
    generated_terraform = run_generate_only(req.requirements, req.services)
    reviewed_terraform = ""
    change_summary = ""
    cleanup_script = ""

    # DB may not be ready during early integration; do not block LLM response.
    try:
        _log_repo.log(
            session_id=session_id,
            requirements=req.requirements,
            services=req.services,
            generated_terraform=generated_terraform,
            reviewed_terraform=reviewed_terraform,
            change_summary=change_summary,
            cleanup_script=cleanup_script,
        )
    except Exception as exc:  # pragma: no cover - best-effort logging path
        _logger.warning("Skipping generation log persistence: %s", exc)

    from backend.services.diagram_service import generate_mermaid_diagram
    diagram = generate_mermaid_diagram(req.services)

    return GenerateResponse(
        session_id=session_id,
        generated_terraform=generated_terraform,
        reviewed_terraform=reviewed_terraform,
        change_summary=change_summary,
        cleanup_script=cleanup_script,
        mermaid_diagram=diagram,
    )
