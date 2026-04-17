from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DiffRequest(BaseModel):
    original: str
    modified: str


class DiffResponse(BaseModel):
    original: str
    modified: str
    diff_lines: list[str]


@router.post("/review/diff", response_model=DiffResponse)
async def compute_diff(req: DiffRequest):
    import difflib
    diff = list(
        difflib.unified_diff(
            req.original.splitlines(),
            req.modified.splitlines(),
            fromfile="generated",
            tofile="reviewed",
            lineterm="",
        )
    )
    return DiffResponse(original=req.original, modified=req.modified, diff_lines=diff)
