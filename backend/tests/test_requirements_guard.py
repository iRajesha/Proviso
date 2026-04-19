import pytest

from backend.agents.crew import run_crew
from backend.services.requirements_guard import RequirementsNotClearError


def test_run_crew_blocks_vague_requirements():
    with pytest.raises(RequirementsNotClearError):
        run_crew("Hello", [])

