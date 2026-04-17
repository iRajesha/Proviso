import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.agents.crew import run_crew
from backend.db.repositories import GenerationLogRepository

router = APIRouter()
_log_repo = GenerationLogRepository()


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

    session_id = str(uuid.uuid4())
    result = run_crew(req.requirements, req.services)

    _log_repo.log(
        session_id=session_id,
        requirements=req.requirements,
        services=req.services,
        generated_terraform=result.generated_terraform,
        reviewed_terraform=result.reviewed_terraform,
        change_summary=result.change_summary,
        cleanup_script=result.cleanup_script,
    )

    from backend.services.diagram_service import generate_mermaid_diagram
    diagram = generate_mermaid_diagram(req.services)

    return GenerateResponse(
        session_id=session_id,
        generated_terraform=result.generated_terraform,
        reviewed_terraform=result.reviewed_terraform,
        change_summary=result.change_summary,
        cleanup_script=result.cleanup_script,
        mermaid_diagram=diagram,
    )
