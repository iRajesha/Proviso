import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.main import app

client = TestClient(app)


@patch("backend.routers.generate.run_generate_only")
@patch("backend.routers.generate.GenerationLogRepository")
def test_generate_success(mock_log_cls, mock_generate):
    mock_generate.return_value = 'resource "oci_core_vcn" "vcn" {}'
    mock_log_cls.return_value.log.return_value = None

    response = client.post(
        "/api/v1/generate",
        json={
            "requirements": (
                "Create a production OCI setup with one VCN, one public subnet, "
                "one private subnet, and a private compute instance. "
                "Allow inbound HTTPS from the internet and SSH only from "
                "10.10.0.0/24 in ap-hyderabad-1."
            ),
            "services": ["Networking", "Compute"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["generated_terraform"].startswith('resource "oci_core_vcn"')
    assert data["reviewed_terraform"] == ""
    assert data["change_summary"] == ""
    assert data["cleanup_script"] == ""
    assert "reviewed_terraform" in data
    assert "mermaid_diagram" in data
    assert "session_id" in data


def test_generate_empty_requirements():
    response = client.post(
        "/api/v1/generate",
        json={"requirements": "", "services": []},
    )
    assert response.status_code == 400


@patch("backend.routers.generate.run_generate_only")
def test_generate_requires_clarification(mock_generate):
    response = client.post(
        "/api/v1/generate",
        json={"requirements": "Hello", "services": []},
    )
    assert response.status_code == 422
    payload = response.json()
    assert "detail" in payload
    assert "clarification_questions" in payload["detail"]
    assert len(payload["detail"]["clarification_questions"]) > 0
    mock_generate.assert_not_called()
