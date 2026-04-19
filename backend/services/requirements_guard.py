"""
Guardrail for minimum infrastructure requirements clarity.

If requirements are too vague, we return targeted clarification questions
instead of starting Terraform generation.
"""

from __future__ import annotations

import re


_COMPONENT_KEYWORDS = {
    "vcn",
    "subnet",
    "nsg",
    "compute",
    "instance",
    "vm",
    "oke",
    "kubernetes",
    "database",
    "adb",
    "load balancer",
    "lb",
    "object storage",
    "bucket",
    "api gateway",
    "functions",
    "vault",
    "waf",
}

_ACCESS_SECURITY_KEYWORDS = {
    "public",
    "private",
    "internet",
    "ingress",
    "egress",
    "cidr",
    "firewall",
    "nsg",
    "security",
    "bastion",
    "vpn",
    "peering",
}

_CONSTRAINT_KEYWORDS = {
    "dev",
    "development",
    "test",
    "qa",
    "staging",
    "prod",
    "production",
    "ha",
    "high availability",
    "autoscaling",
    "availability domain",
    "fault domain",
    "multi-ad",
    "multi region",
    "dr",
    "disaster recovery",
}

_REGION_PATTERN = re.compile(r"\b[a-z]{2}-[a-z-]+-\d\b")


class RequirementsNotClearError(ValueError):
    """Raised when requirements are too vague to safely generate Terraform."""

    def __init__(
        self,
        message: str,
        missing_details: list[str],
        clarification_questions: list[str],
    ) -> None:
        super().__init__(message)
        self.message = message
        self.missing_details = missing_details
        self.clarification_questions = clarification_questions


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def evaluate_requirements_clarity(requirements: str, services: list[str]) -> dict:
    """
    Returns a decision payload:
    - is_clear: bool
    - missing_details: list[str]
    - clarification_questions: list[str]
    """
    text = requirements.strip().lower()
    words = re.findall(r"\w+", text)

    has_component_signal = bool(services) or _contains_any(text, _COMPONENT_KEYWORDS)
    has_access_signal = _contains_any(text, _ACCESS_SECURITY_KEYWORDS)
    has_constraint_signal = _contains_any(text, _CONSTRAINT_KEYWORDS) or bool(
        _REGION_PATTERN.search(text)
    )

    missing_details: list[str] = []
    questions: list[str] = []

    if len(words) < 5:
        missing_details.append("insufficient_description")
        questions.append(
            "What infrastructure do you want (for example: API service, database, VCN/subnets, OKE)?"
        )

    if not has_component_signal:
        missing_details.append("workload_components")
        questions.append(
            "Which OCI services/components should be provisioned (Compute, OKE, ADB, LB, Object Storage, etc.)?"
        )

    if not has_access_signal:
        missing_details.append("network_access_security")
        questions.append(
            "Should workloads be public or private, and what inbound access is required (ports/CIDRs)?"
        )

    if not has_constraint_signal:
        missing_details.append("environment_constraints")
        questions.append(
            "What environment/constraints apply (dev/test/prod, region, HA/scaling, DR/compliance)?"
        )

    return {
        "is_clear": len(missing_details) == 0,
        "missing_details": missing_details,
        "clarification_questions": questions,
    }


def ensure_requirements_clarity(requirements: str, services: list[str]) -> None:
    """
    Raise RequirementsNotClearError when requirements are not sufficiently clear.
    """
    clarity = evaluate_requirements_clarity(requirements, services)
    if clarity["is_clear"]:
        return

    raise RequirementsNotClearError(
        message=(
            "Requirements are not clear enough to safely generate Terraform. "
            "Please answer the clarification questions."
        ),
        missing_details=clarity["missing_details"],
        clarification_questions=clarity["clarification_questions"],
    )
