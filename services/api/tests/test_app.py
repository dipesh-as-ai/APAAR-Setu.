from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api import app as api_module


@pytest.fixture()
def client(tmp_path: Path):
    api_module.DB_PATH = tmp_path / "test.db"
    api_module.tokens.clear()
    api_module.seed_db()
    with TestClient(api_module.app) as test_client:
        yield test_client


def login(client: TestClient, username: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "demo123"})
    assert response.status_code == 200
    return response.json()


def test_institution_upload_creates_row_level_results(client: TestClient):
    session = login(client, "operator-a")
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    fixture = Path(__file__).resolve().parents[3] / "infra" / "seed" / "demo_students.csv"
    with fixture.open("rb") as stream:
        response = client.post(
            "/api/v1/institutions/inst_a/submissions",
            params={
                "academic_cycle": "2026-27",
                "programme_id": "prog_a_cse",
                "idempotency_key": "pytest-upload",
            },
            headers=headers,
            files={"file": (fixture.name, stream, "text/csv")},
        )
    assert response.status_code == 202
    submission_id = response.json()["submission_id"]
    status = client.get(f"/api/v1/submissions/{submission_id}", headers=headers)
    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    assert status.json()["total_rows"] == 9
    errors = client.get(f"/api/v1/submissions/{submission_id}/errors", headers=headers)
    assert errors.status_code == 200
    assert len(errors.json()["items"]) == 9


def test_institution_scope_is_enforced(client: TestClient):
    session = login(client, "operator-a")
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    response = client.get("/api/v1/dashboards/institution", headers=headers)
    assert response.status_code == 200
    assert response.json()["institution_id"] == "inst_a"


def test_signed_verification_requires_consent(client: TestClient):
    verifier = login(client, "verifier")
    student = login(client, "student")
    verifier_headers = {"Authorization": f"Bearer {verifier['access_token']}"}
    student_headers = {"Authorization": f"Bearer {student['access_token']}"}
    enrolments = client.get("/api/v1/enrolments", headers=verifier_headers).json()["items"]
    request = client.post(
        "/api/v1/verification-requests",
        headers=verifier_headers,
        json={
            "enrolment_id": enrolments[0]["id"],
            "purpose": "employment_screening",
            "requested_fields": ["name", "institution", "status"],
            "expires_at": "2099-01-01T00:00:00+00:00",
        },
    )
    assert request.status_code == 200
    request_id = request.json()["request_id"]
    before_consent = client.post(f"/api/v1/verification-requests/{request_id}/issue", headers=verifier_headers)
    assert before_consent.status_code == 409
    consent = client.post(
        f"/api/v1/verification-requests/{request_id}/decision",
        headers=student_headers,
        json={"decision": "approved", "reason": "Approved for the demo"},
    )
    assert consent.status_code == 200
    issued = client.post(f"/api/v1/verification-requests/{request_id}/issue", headers=verifier_headers)
    assert issued.status_code == 200
    public_result = client.get(f"/verify/{issued.json()['token']}")
    assert public_result.status_code == 200
    assert public_result.json()["status"] == "valid"
    reviewer = login(client, "reviewer")
    reviewer_headers = {"Authorization": f"Bearer {reviewer['access_token']}"}
    revoked = client.post(f"/api/v1/verification/{issued.json()['verification_id']}/revoke", headers=reviewer_headers)
    assert revoked.status_code == 200
    assert client.get(f"/verify/{issued.json()['token']}").json()["status"] == "revoked"
