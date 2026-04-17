import pytest
from backend.services.diagram_service import generate_mermaid_diagram


def test_empty_services_returns_default():
    result = generate_mermaid_diagram([])
    assert "graph TB" in result
    assert "No services selected" in result


def test_vcn_only():
    result = generate_mermaid_diagram(["vcn"])
    assert "VCN" in result
    assert "graph TB" in result


def test_compute_and_adb():
    result = generate_mermaid_diagram(["compute", "adb"])
    assert "COMPUTE" in result
    assert "ADB" in result
    assert "COMPUTE --> ADB" in result


def test_full_stack():
    services = ["vcn", "compute", "adb", "lb", "object_storage", "kms"]
    result = generate_mermaid_diagram(services)
    assert "LB" in result
    assert "KMS" in result
    assert "OBJ" in result
