from pathlib import Path
from crewai import Agent
from backend.llm.oci_genai_llm import get_oci_llm

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"


def _load(filename: str) -> str:
    return (_PROMPT_DIR / filename).read_text()


def make_generator_agent() -> Agent:
    return Agent(
        role="OCI Infrastructure Architect",
        goal=(
            "Generate complete, production-ready OCI Terraform HCL code from a natural "
            "language description of the required infrastructure. Output ONLY valid HCL "
            "inside a single ```hcl code block — no prose, no partial stubs."
        ),
        backstory=_load("generator_backstory.md"),
        llm=get_oci_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def make_reviewer_agent() -> Agent:
    return Agent(
        role="OCI Security & Compliance Specialist",
        goal=(
            "Review Terraform code for CIS OCI Benchmark v2.0 violations. "
            "Output SECTION 1 (corrected HCL) and SECTION 2 (change summary) exactly."
        ),
        backstory=_load("reviewer_backstory.md"),
        llm=get_oci_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def make_cleanup_agent() -> Agent:
    return Agent(
        role="Infrastructure Cleanup Specialist",
        goal=(
            "Write a safe, idempotent bash cleanup script that destroys all OCI resources "
            "in the correct dependency order, with confirmation prompt and logging."
        ),
        backstory=_load("cleanup_backstory.md"),
        llm=get_oci_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
