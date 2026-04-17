from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.repositories import GoldScriptRepository

router = APIRouter()
_repo = GoldScriptRepository()


class SaveRequest(BaseModel):
    title: str
    use_case: str
    services: list[str]
    terraform_code: str
    cleanup_script: str
    change_summary: str


class SaveResponse(BaseModel):
    id: int
    message: str


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


@router.post("/scripts/save", response_model=SaveResponse)
async def save_script(req: SaveRequest):
    if not req.title.strip() or not req.terraform_code.strip():
        raise HTTPException(status_code=400, detail="title and terraform_code are required")
    script_id = _repo.save(
        title=req.title,
        use_case=req.use_case,
        services=req.services,
        terraform_code=req.terraform_code,
        cleanup_script=req.cleanup_script,
        change_summary=req.change_summary,
    )
    return SaveResponse(id=script_id, message="Script saved successfully")


@router.post("/scripts/search")
async def search_scripts(req: SearchRequest):
    results = _repo.hybrid_search(req.query, req.limit)
    return [
        {
            "id": r.id,
            "title": r.title,
            "use_case": r.use_case,
            "services": r.services,
            "score": r.score,
            "snippet": r.snippet,
        }
        for r in results
    ]


@router.get("/scripts/{script_id}")
async def get_script(script_id: int):
    script = _repo.get_by_id(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {
        "id": script.id,
        "title": script.title,
        "use_case": script.use_case,
        "services": script.services,
        "terraform_code": script.terraform_code,
        "cleanup_script": script.cleanup_script,
        "change_summary": script.change_summary,
        "created_at": script.created_at,
    }
