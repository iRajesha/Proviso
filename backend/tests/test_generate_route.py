import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app

client = TestClient(app)


@patch("backend.routers.generate.run_crew")
@patch("backend.routers.generate.GenerationLogRepository")
def test_generate_success(mock_log_cls, mock_crew):
    mock_crew.return_value = MagicMock(
        generated_terraform='resource "oci_core_vcn" "vcn" {}',
        reviewed_terraform='resource "oci_core_vcn" "vcn" {}',
        change_summary="No changes required.",
        cleanup_script="#!/bin/bash\nterraform destroy -auto-approve",
    )
    mock_log_cls.return_value.log.return_value = None

    response = client.post(
        "/api/v1/generate",
        json={"requirements": "Create a VCN with 2 subnets", "services": ["vcn"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "reviewed_terraform" in data
    assert "mermaid_diagram" in data
    assert "session_id" in data


def test_generate_empty_requirements():
    response = client.post(
        "/api/v1/generate",
        json={"requirements": "", "services": []},
    )
    assert response.status_code == 400
