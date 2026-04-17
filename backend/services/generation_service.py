"""
Generation service: thin orchestration layer between router and CrewAI crew.
Provides caching/short-circuit logic for repeat requests.
"""
from backend.agents.crew import run_crew, GenerationResult


def generate_infrastructure(requirements: str, services: list[str]) -> GenerationResult:
    return run_crew(requirements, services)
