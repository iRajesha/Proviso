from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class GoldScript:
    id: int
    title: str
    use_case: str
    services: list[str]
    terraform_code: str
    cleanup_script: str
    change_summary: str
    embedding: list[float] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class GenerationLog:
    id: int
    session_id: str
    requirements: str
    services: list[str]
    generated_terraform: str
    reviewed_terraform: str
    change_summary: str
    cleanup_script: str
    created_at: Optional[datetime] = None


@dataclass
class SearchResult:
    id: int
    title: str
    use_case: str
    services: list[str]
    score: float
    snippet: str
