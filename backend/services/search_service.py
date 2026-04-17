"""
Search service: wraps GoldScriptRepository.hybrid_search with query preprocessing.
"""
from backend.db.repositories import GoldScriptRepository
from backend.db.models import SearchResult

_repo = GoldScriptRepository()


def search_gold_scripts(query: str, limit: int = 10) -> list[SearchResult]:
    query = query.strip()
    if not query:
        return []
    return _repo.hybrid_search(query, limit)
