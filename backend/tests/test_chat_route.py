from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app
from backend.agents.crew import GenerationResult

client = TestClient(app)


def _create_session() -> str:
    response = client.post("/api/v1/chat/sessions", json={"services": ["Networking", "Compute"]})
    assert response.status_code == 200
    return response.json()["session_id"]


@patch("backend.services.chat_service.run_generate_only")
def test_chat_generate_flow(mock_run_generate_only):
    mock_run_generate_only.return_value = 'resource "oci_core_vcn" "main" {}'

    session_id = _create_session()
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "message": (
                "Create a production environment in ap-hyderabad-1 with one VCN and private "
                "compute. SSH from 10.10.0.0/24 only and HA-ready setup."
            ),
            "intent": "auto",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_intent"] == "generate"
    assert payload["generated_terraform"].startswith('resource "oci_core_vcn"')
    assert payload["reviewed_terraform"] == ""
    assert payload["cleanup_script"] == ""
    assert len(payload["messages"]) >= 3


@patch("backend.services.chat_service.chat_with_oci")
@patch("backend.services.chat_service.run_refinement_draft")
@patch("backend.services.chat_service.run_generate_only")
def test_chat_refine_and_conversation(mock_run_generate_only, mock_run_refinement_draft, mock_chat):
    mock_run_generate_only.return_value = 'resource "oci_core_vcn" "main" {}'
    mock_run_refinement_draft.return_value = 'resource "oci_core_vcn" "main" { dns_label = "prod" }'
    mock_chat.return_value = "This is a contextual OCI chat answer."

    session_id = _create_session()

    first = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "message": (
                "Create a production setup in ap-hyderabad-1 with private networking and "
                "restricted SSH from 10.10.0.0/24."
            ),
            "intent": "generate",
        },
    )
    assert first.status_code == 200

    refine = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "Add DNS label prod to the VCN.", "intent": "auto"},
    )
    assert refine.status_code == 200
    refine_payload = refine.json()
    assert refine_payload["resolved_intent"] == "refine"
    assert 'dns_label = "prod"' in refine_payload["generated_terraform"]
    assert refine_payload["reviewed_terraform"] == ""

    chat = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "Why was this change required?", "intent": "chat"},
    )
    assert chat.status_code == 200
    chat_payload = chat.json()
    assert chat_payload["resolved_intent"] == "chat"
    assert chat_payload["messages"][-1]["content"] == "This is a contextual OCI chat answer."


def test_chat_clarification_required():
    session_id = _create_session()
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "Create infra", "intent": "generate"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolved_intent"] == "generate"
    assert payload["clarification"] is not None
    assert len(payload["clarification"]["clarification_questions"]) > 0


@patch("backend.services.chat_service.run_cleanup_only")
@patch("backend.services.chat_service.run_review_only")
@patch("backend.services.chat_service.run_generate_only")
def test_chat_explicit_review_and_cleanup(
    mock_run_generate_only,
    mock_run_review_only,
    mock_run_cleanup_only,
):
    mock_run_generate_only.return_value = 'resource "oci_core_vcn" "main" {}'
    mock_run_review_only.return_value = (
        'resource "oci_core_vcn" "main" { display_name = "secure" }',
        "- hardened security settings",
    )
    mock_run_cleanup_only.return_value = "#!/bin/bash\necho cleanup"

    session_id = _create_session()

    first = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "message": (
                "Create production infra in ap-hyderabad-1 with private networking and "
                "SSH from 10.10.0.0/24."
            ),
            "intent": "generate",
        },
    )
    assert first.status_code == 200

    review = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "", "intent": "review"},
    )
    assert review.status_code == 200
    review_payload = review.json()
    assert review_payload["resolved_intent"] == "review"
    assert "secure" in review_payload["reviewed_terraform"]
    assert "hardened" in review_payload["change_summary"]

    cleanup = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "", "intent": "cleanup"},
    )
    assert cleanup.status_code == 200
    cleanup_payload = cleanup.json()
    assert cleanup_payload["resolved_intent"] == "cleanup"
    assert cleanup_payload["cleanup_script"].startswith("#!/bin/bash")
