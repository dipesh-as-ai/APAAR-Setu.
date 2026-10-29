from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[2]
if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/apaar.db")
else:
    DB_PATH = Path(os.getenv("APAAR_DB_PATH", str(ROOT / "data" / "apaar.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MOCK_APAAR = {
    "APAAR-10000001": {"name": "Aarav Sharma", "dob": "2004-05-17", "gender": "M"},
    "APAAR-10000002": {"name": "Meera Nair", "dob": "2003-11-09", "gender": "F"},
    "APAAR-10000003": {"name": "Kabir Das", "dob": "2004-02-20", "gender": "M"},
    "APAAR-10000004": {"name": "Ishita Rao", "dob": "2003-09-01", "gender": "F"},
    "APAAR-10000005": {"name": "Rohan Mehta", "dob": "2004-01-14", "gender": "M"},
    "APAAR-10000006": {"name": "Ananya Sen", "dob": "2004-06-23", "gender": "F"},
}

@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_db()
    yield


app = FastAPI(title="APAAR Setu API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def ensure_db_middleware(request, call_next):
    if not DB_PATH.exists():
        seed_db()
    return await call_next(request)
cors_origins = [x.strip() for x in os.getenv("APAAR_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)
signing_key = Ed25519PrivateKey.generate()
tokens: dict[str, str] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def json_value(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def init_db() -> None:
    connection = connect()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS institutions (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, code TEXT UNIQUE NOT NULL, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, display_name TEXT NOT NULL,
            role TEXT NOT NULL, institution_id TEXT REFERENCES institutions(id)
        );
        CREATE TABLE IF NOT EXISTS programmes (
            id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES institutions(id), name TEXT NOT NULL, code TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES institutions(id), programme_id TEXT NOT NULL REFERENCES programmes(id),
            academic_cycle TEXT NOT NULL, regular_intake INTEGER NOT NULL, supernumerary_limit INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES institutions(id), programme_id TEXT NOT NULL REFERENCES programmes(id),
            academic_cycle TEXT NOT NULL, file_name TEXT NOT NULL, file_digest TEXT NOT NULL, idempotency_key TEXT NOT NULL,
            status TEXT NOT NULL, total_rows INTEGER NOT NULL DEFAULT 0, accepted_rows INTEGER NOT NULL DEFAULT 0,
            rejected_rows INTEGER NOT NULL DEFAULT 0, pending_rows INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
            UNIQUE(institution_id, idempotency_key)
        );
        CREATE TABLE IF NOT EXISTS identities (
            id TEXT PRIMARY KEY, apaar_digest TEXT, apaar_value TEXT, provisional_id TEXT, name TEXT NOT NULL, dob TEXT,
            gender TEXT, state TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS enrolments (
            id TEXT PRIMARY KEY, institution_id TEXT NOT NULL REFERENCES institutions(id), programme_id TEXT NOT NULL REFERENCES programmes(id),
            academic_cycle TEXT NOT NULL, student_institution_id TEXT NOT NULL, identity_id TEXT NOT NULL REFERENCES identities(id),
            name TEXT NOT NULL, apaar_value TEXT, category TEXT NOT NULL, is_supernumerary INTEGER NOT NULL DEFAULT 0,
            admission_date TEXT, status TEXT NOT NULL, validation_state TEXT NOT NULL, identity_state TEXT NOT NULL, source_submission_id TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS submission_rows (
            id TEXT PRIMARY KEY, submission_id TEXT NOT NULL REFERENCES submissions(id), row_number INTEGER NOT NULL,
            raw_json TEXT NOT NULL, validation_state TEXT NOT NULL, errors_json TEXT NOT NULL, enrolment_id TEXT REFERENCES enrolments(id)
        );
        CREATE TABLE IF NOT EXISTS review_cases (
            id TEXT PRIMARY KEY, case_type TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL, institution_id TEXT NOT NULL,
            enrolment_id TEXT REFERENCES enrolments(id), related_enrolment_id TEXT, title TEXT NOT NULL, evidence_json TEXT NOT NULL,
            decision TEXT, reason TEXT, created_at TEXT NOT NULL, resolved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS verification_requests (
            id TEXT PRIMARY KEY, enrolment_id TEXT NOT NULL REFERENCES enrolments(id), verifier_username TEXT NOT NULL,
            purpose TEXT NOT NULL, requested_fields_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL, decision_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS verifications (
            id TEXT PRIMARY KEY, request_id TEXT NOT NULL REFERENCES verification_requests(id), token_hash TEXT UNIQUE NOT NULL,
            payload_json TEXT NOT NULL, signature TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY, actor_username TEXT NOT NULL, actor_role TEXT NOT NULL, action TEXT NOT NULL,
            target_type TEXT NOT NULL, target_id TEXT NOT NULL, details_json TEXT NOT NULL, correlation_id TEXT NOT NULL, created_at TEXT NOT NULL
        );
        """
    )
    connection.commit()
    connection.close()


def seed_db() -> None:
    init_db()
    connection = connect()
    if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        connection.close()
        return
    institution_a = "inst_a"
    institution_b = "inst_b"
    programme_a = "prog_a_cse"
    programme_b = "prog_b_cse"
    connection.executemany("INSERT INTO institutions(id,name,code) VALUES(?,?,?)", [
        (institution_a, "Aster Institute of Technology", "AIT-001"),
        (institution_b, "Bharat School of Engineering", "BSE-002"),
    ])
    connection.executemany("INSERT INTO users(id,username,password,display_name,role,institution_id) VALUES(?,?,?,?,?,?)", [
        ("usr_operator", "operator-a", "demo123", "Aster Data Operator", "institution_operator", institution_a),
        ("usr_reviewer", "reviewer", "demo123", "AICTE Regional Reviewer", "aicte_reviewer", None),
        ("usr_student", "student", "demo123", "Demo Student", "student", None),
        ("usr_verifier", "verifier", "demo123", "Demo Employer", "verifier", None),
        ("usr_admin", "admin", "demo123", "AICTE Administrator", "aicte_admin", None),
    ])
    connection.executemany("INSERT INTO programmes(id,institution_id,name,code) VALUES(?,?,?,?)", [
        (programme_a, institution_a, "Bachelor of Technology - Computer Science", "BTECH-CSE"),
        (programme_b, institution_b, "Bachelor of Technology - Computer Science", "BTECH-CSE"),
    ])
    connection.executemany("INSERT INTO approvals(id,institution_id,programme_id,academic_cycle,regular_intake,supernumerary_limit,version) VALUES(?,?,?,?,?,?,?)", [
        ("approval_a_2026", institution_a, programme_a, "2026-27", 5, 1, 1),
        ("approval_b_2026", institution_b, programme_b, "2026-27", 10, 2, 1),
    ])
    identity_id = "identity_conflict"
    connection.execute("INSERT INTO identities(id,apaar_digest,apaar_value,name,dob,gender,state,created_at) VALUES(?,?,?,?,?,?,?,?)", (
        identity_id, digest("APAAR-10000001"), "APAAR-10000001", "Aarav Sharma", "2004-05-17", "M", "matched", now()
    ))
    connection.execute("INSERT INTO enrolments(id,institution_id,programme_id,academic_cycle,student_institution_id,identity_id,name,apaar_value,category,is_supernumerary,admission_date,status,validation_state,identity_state,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        "enr_b_seed", institution_b, programme_b, "2026-27", "BSE-001", identity_id, "Aarav Sharma", "APAAR-10000001", "GEN", 0, "2026-07-02", "active", "verified", "matched", now()
    ))
    connection.commit()
    connection.close()


def audit(actor: dict[str, Any], action: str, target_type: str, target_id: str, details: Any, correlation_id: str | None = None) -> None:
    connection = connect()
    connection.execute("INSERT INTO audit_events(id,actor_username,actor_role,action,target_type,target_id,details_json,correlation_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (
        new_id("audit"), actor["username"], actor["role"], action, target_type, target_id, json_text(details), correlation_id or new_id("corr"), now()
    ))
    connection.commit()
    connection.close()


def user_from_token(credentials: HTTPAuthorizationCredentials | None) -> dict[str, Any]:
    if not credentials or credentials.credentials not in tokens:
        raise HTTPException(status_code=401, detail="Authentication required")
    connection = connect()
    row = connection.execute("SELECT * FROM users WHERE username=?", (tokens[credentials.credentials],)).fetchone()
    connection.close()
    if not row:
        raise HTTPException(status_code=401, detail="User session is invalid")
    return dict(row)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict[str, Any]:
    return user_from_token(credentials)


def require_roles(*roles: str):
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="This role cannot perform the requested action")
        return user
    return dependency


def field(row: dict[str, str], *names: str) -> str:
    normalized = {str(key).strip().lower().replace(" ", "_"): (value or "").strip() for key, value in row.items()}
    for name in names:
        if normalized.get(name):
            return normalized[name]
    return ""


def process_submission(submission_id: str, content: bytes, actor: dict[str, Any]) -> None:
    connection = connect()
    submission = connection.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
    if not submission:
        connection.close()
        return
    submission = dict(submission)
    approval = connection.execute("SELECT * FROM approvals WHERE institution_id=? AND programme_id=? AND academic_cycle=?", (
        submission["institution_id"], submission["programme_id"], submission["academic_cycle"]
    )).fetchone()
    if not approval:
        connection.execute("UPDATE submissions SET status='integration_pending' WHERE id=?", (submission_id,))
        connection.commit()
        connection.close()
        return
    approval = dict(approval)
    connection.commit()
    connection.close()
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        active_count = get_active_count(submission["institution_id"], submission["programme_id"], submission["academic_cycle"])
        regular_count = active_count
        seen: set[str] = set()
        counts = {"accepted": 0, "rejected": 0, "pending_review": 0}
        for row_number, raw in enumerate(rows, start=2):
            raw = {str(k): (v or "") for k, v in raw.items()}
            name = field(raw, "student_name", "name")
            dob = field(raw, "date_of_birth", "dob")
            gender = field(raw, "gender")
            apaar = field(raw, "apaar_id", "apaar")
            category = field(raw, "admission_category", "category") or "GEN"
            supernumerary = field(raw, "supernumerary", "is_supernumerary").lower() in {"yes", "true", "1"}
            student_id = field(raw, "student_institution_id", "student_id") or f"ROW-{row_number}"
            admission_date = field(raw, "admission_date") or submission["academic_cycle"][:4] + "-07-01"
            errors: list[dict[str, str]] = []
            review_types: list[tuple[str, str, str]] = []
            identity_state = "matched"
            provisional_id = None
            if not name:
                errors.append({"field": "student_name", "code": "required", "message": "Student name is required."})
            if apaar:
                if not re.fullmatch(r"APAAR-\d{8}", apaar):
                    errors.append({"field": "apaar_id", "code": "invalid_format", "message": "APAAR must match the prototype format APAAR-########."})
                    identity_state = "mismatch"
                elif apaar not in MOCK_APAAR:
                    errors.append({"field": "apaar_id", "code": "not_found", "message": "The mock identity service could not match this APAAR."})
                    identity_state = "mismatch"
                elif apaar in seen:
                    errors.append({"field": "apaar_id", "code": "duplicate_upload", "message": "This APAAR appears more than once in the upload."})
                    review_types.append(("duplicate", "high", "Duplicate APAAR in the same upload"))
                else:
                    seen.add(apaar)
                existing = find_active_enrolments(apaar)
                if existing:
                    if any(item["institution_id"] == submission["institution_id"] for item in existing):
                        errors.append({"field": "apaar_id", "code": "duplicate_enrolment", "message": "This APAAR already has an active enrolment in this institution and cycle."})
                        review_types.append(("duplicate", "high", "Duplicate active enrolment"))
                    else:
                        review_types.append(("cross_institution", "high", "Possible cross-institution active enrolment"))
            else:
                identity_state = "pending"
                provisional_id = new_id("prov")
                if not dob:
                    errors.append({"field": "date_of_birth", "code": "required_for_provisional", "message": "Date of birth is required when APAAR is pending."})
                else:
                    review_types.append(("identity", "medium", "APAAR is pending and requires follow-up"))
            if category.upper() == "NRI" and not field(raw, "sponsor_name", "nri_sponsor"):
                errors.append({"field": "sponsor_name", "code": "required_for_nri", "message": "NRI records require sponsor information."})
            if category.upper() == "OCI" and field(raw, "nationality").lower() in {"", "indian"}:
                errors.append({"field": "nationality", "code": "inconsistent_oci", "message": "OCI records require a non-Indian nationality in the prototype."})
            if category.upper() == "FN" and not field(raw, "nationality"):
                errors.append({"field": "nationality", "code": "required_for_fn", "message": "Foreign national records require nationality."})
            if not supernumerary:
                regular_count += 1
                if regular_count > approval["regular_intake"]:
                    review_types.append(("intake", "high", "Regular enrolment exceeds approved intake"))
            else:
                super_count = get_supernumerary_count(submission["institution_id"], submission["programme_id"], submission["academic_cycle"]) + 1
                if super_count > approval["supernumerary_limit"]:
                    review_types.append(("intake", "high", "Supernumerary enrolment exceeds approved limit"))
            validation_state = "rejected" if errors else ("pending_review" if review_types else "accepted")
            identity_id = new_id("identity")
            connection = connect()
            connection.execute("INSERT INTO identities(id,apaar_digest,apaar_value,provisional_id,name,dob,gender,state,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (
                identity_id, digest(apaar) if apaar else None, apaar or None, provisional_id, name or "Unnamed student", dob or None, gender or None, identity_state, now()
            ))
            enrolment_id = new_id("enr")
            connection.execute("INSERT INTO enrolments(id,institution_id,programme_id,academic_cycle,student_institution_id,identity_id,name,apaar_value,category,is_supernumerary,admission_date,status,validation_state,identity_state,source_submission_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                enrolment_id, submission["institution_id"], submission["programme_id"], submission["academic_cycle"], student_id, identity_id, name or "Unnamed student", apaar or None, category, int(supernumerary), admission_date, "active", validation_state, identity_state, submission_id, now()
            ))
            for case_type, severity, title in review_types:
                case_id = new_id("case")
                connection.execute("INSERT INTO review_cases(id,case_type,severity,status,institution_id,enrolment_id,related_enrolment_id,title,evidence_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (
                    case_id, case_type, severity, "open", submission["institution_id"], enrolment_id, None, title, json_text({"row_number": row_number, "apaar": apaar or None, "errors": errors}), now()
                ))
            connection.execute("INSERT INTO submission_rows(id,submission_id,row_number,raw_json,validation_state,errors_json,enrolment_id) VALUES(?,?,?,?,?,?,?)", (
                new_id("row"), submission_id, row_number, json_text(raw), validation_state, json_text(errors), enrolment_id
            ))
            connection.commit()
            connection.close()
            if validation_state == "accepted":
                counts["accepted"] += 1
            elif validation_state == "rejected":
                counts["rejected"] += 1
            else:
                counts["pending_review"] += 1
        connection = connect()
        connection.execute("UPDATE submissions SET status='completed',total_rows=?,accepted_rows=?,rejected_rows=?,pending_rows=? WHERE id=?", (
            len(rows), counts["accepted"], counts["rejected"], counts["pending_review"], submission_id
        ))
        connection.commit()
        connection.close()
        audit(actor, "submission_processed", "submission", submission_id, counts)
    except Exception as error:
        connection = connect()
        connection.execute("UPDATE submissions SET status='failed' WHERE id=?", (submission_id,))
        connection.commit()
        connection.close()
        audit(actor, "submission_failed", "submission", submission_id, {"error": str(error)})


def get_active_count(institution_id: str, programme_id: str, cycle: str) -> int:
    connection = connect()
    result = connection.execute("SELECT COUNT(*) FROM enrolments WHERE institution_id=? AND programme_id=? AND academic_cycle=? AND status='active' AND validation_state IN ('accepted','verified','pending_review') AND is_supernumerary=0", (institution_id, programme_id, cycle)).fetchone()[0]
    connection.close()
    return int(result)


def get_supernumerary_count(institution_id: str, programme_id: str, cycle: str) -> int:
    connection = connect()
    result = connection.execute("SELECT COUNT(*) FROM enrolments WHERE institution_id=? AND programme_id=? AND academic_cycle=? AND status='active' AND is_supernumerary=1", (institution_id, programme_id, cycle)).fetchone()[0]
    connection.close()
    return int(result)


def find_active_enrolments(apaar: str) -> list[dict[str, Any]]:
    connection = connect()
    rows = connection.execute("SELECT * FROM enrolments WHERE apaar_value=? AND status='active' AND validation_state IN ('accepted','verified','pending_review')", (apaar,)).fetchall()
    connection.close()
    return [dict(row) for row in rows]


class LoginRequest(BaseModel):
    username: str
    password: str


class ReviewDecision(BaseModel):
    decision: str = Field(pattern="^(confirmed|dismissed|corrected|escalated)$")
    reason: str = Field(min_length=3, max_length=1000)


class VerificationRequestIn(BaseModel):
    enrolment_id: str
    purpose: str = Field(min_length=3, max_length=120)
    requested_fields: list[str] = Field(min_length=1)
    expires_at: str


class ConsentDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str = ""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "apaar-setu-api", "database": str(DB_PATH)}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    connection = connect()
    user = connection.execute("SELECT * FROM users WHERE username=? AND password=?", (payload.username, payload.password)).fetchone()
    connection.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid prototype credentials")
    token = secrets.token_urlsafe(24)
    tokens[token] = payload.username
    actor = dict(user)
    audit(actor, "login", "user", actor["id"], {})
    return {"access_token": token, "token_type": "bearer", "user": {k: actor[k] for k in ("username", "display_name", "role", "institution_id")}}


@app.get("/api/v1/auth/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {k: user[k] for k in ("username", "display_name", "role", "institution_id")}


@app.get("/api/v1/institutions")
def institutions(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    if user["role"].startswith("institution"):
        rows = connection.execute("SELECT * FROM institutions WHERE id=?", (user["institution_id"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM institutions ORDER BY name").fetchall()
    connection.close()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/v1/institutions/{institution_id}/approvals")
def approvals(institution_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user["role"].startswith("institution") and user["institution_id"] != institution_id:
        raise HTTPException(status_code=403, detail="Institution scope violation")
    connection = connect()
    rows = connection.execute("SELECT * FROM approvals WHERE institution_id=? ORDER BY academic_cycle DESC", (institution_id,)).fetchall()
    connection.close()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/v1/programmes")
def programmes(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    if user["role"].startswith("institution"):
        rows = connection.execute("SELECT * FROM programmes WHERE institution_id=? ORDER BY name", (user["institution_id"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM programmes ORDER BY name").fetchall()
    connection.close()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/v1/institutions/{institution_id}/submissions", status_code=202)
async def create_submission(institution_id: str, academic_cycle: str, programme_id: str, idempotency_key: str, file: UploadFile = File(...), background_tasks: BackgroundTasks = None, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user["role"] not in {"institution_operator", "institution_nodal", "aicte_admin"}:
        raise HTTPException(status_code=403, detail="Only institution or AICTE users can submit data")
    if user["role"].startswith("institution") and user["institution_id"] != institution_id:
        raise HTTPException(status_code=403, detail="Institution scope violation")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds the prototype size limit")
    connection = connect()
    institution = connection.execute("SELECT id FROM institutions WHERE id=?", (institution_id,)).fetchone()
    approval = connection.execute("SELECT id FROM approvals WHERE institution_id=? AND programme_id=? AND academic_cycle=?", (institution_id, programme_id, academic_cycle)).fetchone()
    existing = connection.execute("SELECT * FROM submissions WHERE institution_id=? AND idempotency_key=?", (institution_id, idempotency_key)).fetchone()
    if existing:
        connection.close()
        return {"submission_id": existing["id"], "status": existing["status"], "duplicate_request": True}
    if not institution or not approval:
        connection.close()
        raise HTTPException(status_code=404, detail="Institution or approval snapshot not found")
    submission_id = new_id("sub")
    connection.execute("INSERT INTO submissions(id,institution_id,programme_id,academic_cycle,file_name,file_digest,idempotency_key,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (
        submission_id, institution_id, programme_id, academic_cycle, file.filename or "upload.csv", digest(content.decode("utf-8", errors="replace")), idempotency_key, "validating", now()
    ))
    connection.commit()
    connection.close()
    if background_tasks is None:
        process_submission(submission_id, content, user)
    else:
        background_tasks.add_task(process_submission, submission_id, content, user)
    audit(user, "submission_created", "submission", submission_id, {"file_name": file.filename, "academic_cycle": academic_cycle})
    return {"submission_id": submission_id, "status": "validating", "status_url": f"/api/v1/submissions/{submission_id}"}


@app.get("/api/v1/submissions/{submission_id}")
def submission_status(submission_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    row = connection.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
    connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    result = dict(row)
    if user["role"].startswith("institution") and result["institution_id"] != user["institution_id"]:
        raise HTTPException(status_code=403, detail="Institution scope violation")
    return result


@app.get("/api/v1/submissions/{submission_id}/errors")
def submission_errors(submission_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    submission = connection.execute("SELECT institution_id FROM submissions WHERE id=?", (submission_id,)).fetchone()
    if not submission:
        connection.close()
        raise HTTPException(status_code=404, detail="Submission not found")
    if user["role"].startswith("institution") and submission["institution_id"] != user["institution_id"]:
        connection.close()
        raise HTTPException(status_code=403, detail="Institution scope violation")
    rows = connection.execute("SELECT row_number,validation_state,errors_json FROM submission_rows WHERE submission_id=? ORDER BY row_number", (submission_id,)).fetchall()
    connection.close()
    return {"items": [{"row_number": row["row_number"], "validation_state": row["validation_state"], "errors": json_value(row["errors_json"], [])} for row in rows]}


@app.get("/api/v1/enrolments")
def enrolments(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    if user["role"].startswith("institution"):
        rows = connection.execute("SELECT * FROM enrolments WHERE institution_id=? ORDER BY created_at DESC", (user["institution_id"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM enrolments ORDER BY created_at DESC").fetchall()
    connection.close()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/v1/enrolments/{enrolment_id}/validation-results")
def enrolment_validation_results(enrolment_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    row = connection.execute("SELECT * FROM enrolments WHERE id=?", (enrolment_id,)).fetchone()
    if not row:
        connection.close()
        raise HTTPException(status_code=404, detail="Enrolment not found")
    if user["role"].startswith("institution") and row["institution_id"] != user["institution_id"]:
        connection.close()
        raise HTTPException(status_code=403, detail="Institution scope violation")
    submission_row = connection.execute("SELECT errors_json,validation_state FROM submission_rows WHERE enrolment_id=? ORDER BY row_number DESC LIMIT 1", (enrolment_id,)).fetchone()
    connection.close()
    return {"enrolment_id": enrolment_id, "validation_state": row["validation_state"], "errors": json_value(submission_row["errors_json"], []) if submission_row else []}


@app.get("/api/v1/review-cases")
def review_cases(user: dict[str, Any] = Depends(require_roles("aicte_admin", "aicte_reviewer", "auditor", "institution_operator"))) -> dict[str, Any]:
    connection = connect()
    if user["role"] == "institution_operator":
        rows = connection.execute("SELECT * FROM review_cases WHERE institution_id=? ORDER BY created_at DESC", (user["institution_id"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM review_cases ORDER BY created_at DESC").fetchall()
    connection.close()
    return {"items": [{**dict(row), "evidence": json_value(row["evidence_json"], {})} for row in rows]}


@app.get("/api/v1/review-cases/{case_id}")
def review_case(case_id: str, user: dict[str, Any] = Depends(require_roles("aicte_admin", "aicte_reviewer", "auditor", "institution_operator"))) -> dict[str, Any]:
    connection = connect()
    row = connection.execute("SELECT * FROM review_cases WHERE id=?", (case_id,)).fetchone()
    connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Review case not found")
    if user["role"] == "institution_operator" and row["institution_id"] != user["institution_id"]:
        raise HTTPException(status_code=403, detail="Institution scope violation")
    return {**dict(row), "evidence": json_value(row["evidence_json"], {})}


@app.patch("/api/v1/review-cases/{case_id}")
def resolve_case(case_id: str, payload: ReviewDecision, user: dict[str, Any] = Depends(require_roles("aicte_admin", "aicte_reviewer"))) -> dict[str, Any]:
    connection = connect()
    case = connection.execute("SELECT * FROM review_cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        connection.close()
        raise HTTPException(status_code=404, detail="Review case not found")
    resolved_status = "resolved" if payload.decision in {"confirmed", "dismissed", "corrected"} else "escalated"
    connection.execute("UPDATE review_cases SET status=?,decision=?,reason=?,resolved_at=? WHERE id=?", (resolved_status, payload.decision, payload.reason, now(), case_id))
    if resolved_status == "resolved" and case["enrolment_id"]:
        connection.execute("UPDATE enrolments SET validation_state='verified' WHERE id=? AND identity_state='matched'", (case["enrolment_id"],))
    connection.commit()
    connection.close()
    audit(user, "review_case_resolved", "review_case", case_id, {"decision": payload.decision, "reason": payload.reason})
    return {"case_id": case_id, "status": resolved_status, "decision": payload.decision}


@app.get("/api/v1/dashboards/institution")
def institution_dashboard(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if not user["institution_id"]:
        raise HTTPException(status_code=403, detail="Institution context required")
    return dashboard_for(user["institution_id"])


@app.get("/api/v1/dashboards/aicte")
def aicte_dashboard(user: dict[str, Any] = Depends(require_roles("aicte_admin", "aicte_reviewer", "auditor"))) -> dict[str, Any]:
    connection = connect()
    rows = connection.execute("SELECT validation_state,COUNT(*) AS count FROM enrolments GROUP BY validation_state").fetchall()
    cases = connection.execute("SELECT status,COUNT(*) AS count FROM review_cases GROUP BY status").fetchall()
    institutions = connection.execute("SELECT id,name FROM institutions ORDER BY name").fetchall()
    connection.close()
    return {"scope": "aicte", "enrolments": {row["validation_state"]: row["count"] for row in rows}, "cases": {row["status"]: row["count"] for row in cases}, "institutions": [dict(row) for row in institutions]}


def dashboard_for(institution_id: str) -> dict[str, Any]:
    connection = connect()
    counts = connection.execute("SELECT validation_state,COUNT(*) AS count FROM enrolments WHERE institution_id=? GROUP BY validation_state", (institution_id,)).fetchall()
    cases = connection.execute("SELECT status,COUNT(*) AS count FROM review_cases WHERE institution_id=? GROUP BY status", (institution_id,)).fetchall()
    approval = connection.execute("SELECT regular_intake,supernumerary_limit FROM approvals WHERE institution_id=? LIMIT 1", (institution_id,)).fetchone()
    active = connection.execute("SELECT COUNT(*) FROM enrolments WHERE institution_id=? AND status='active'", (institution_id,)).fetchone()[0]
    connection.close()
    return {"scope": "institution", "institution_id": institution_id, "enrolments": {row["validation_state"]: row["count"] for row in counts}, "cases": {row["status"]: row["count"] for row in cases}, "active_enrolments": active, "approved_intake": dict(approval) if approval else None}


@app.get("/api/v1/verification-requests")
def list_verification_requests(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    if user["role"] == "verifier":
        rows = connection.execute("SELECT * FROM verification_requests WHERE verifier_username=? ORDER BY created_at DESC", (user["username"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM verification_requests ORDER BY created_at DESC").fetchall()
    connection.close()
    return {"items": [{**dict(row), "requested_fields": json_value(row["requested_fields_json"], [])} for row in rows]}


@app.post("/api/v1/verification-requests")
def create_verification_request(payload: VerificationRequestIn, user: dict[str, Any] = Depends(require_roles("verifier"))) -> dict[str, Any]:
    allowed_fields = {"name", "institution", "programme", "academic_cycle", "status", "student_institution_id"}
    if not set(payload.requested_fields).issubset(allowed_fields):
        raise HTTPException(status_code=400, detail="One or more requested fields are not verifiable")
    connection = connect()
    enrolment = connection.execute("SELECT id FROM enrolments WHERE id=?", (payload.enrolment_id,)).fetchone()
    if not enrolment:
        connection.close()
        raise HTTPException(status_code=404, detail="Enrolment not found")
    request_id = new_id("vreq")
    connection.execute("INSERT INTO verification_requests(id,enrolment_id,verifier_username,purpose,requested_fields_json,status,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?)", (
        request_id, payload.enrolment_id, user["username"], payload.purpose, json_text(payload.requested_fields), "pending_consent", now(), payload.expires_at
    ))
    connection.commit()
    connection.close()
    audit(user, "verification_requested", "verification_request", request_id, {"fields": payload.requested_fields, "purpose": payload.purpose})
    return {"request_id": request_id, "status": "pending_consent"}


@app.post("/api/v1/verification-requests/{request_id}/decision")
def consent_decision(request_id: str, payload: ConsentDecision, user: dict[str, Any] = Depends(require_roles("student"))) -> dict[str, Any]:
    connection = connect()
    request = connection.execute("SELECT * FROM verification_requests WHERE id=?", (request_id,)).fetchone()
    if not request:
        connection.close()
        raise HTTPException(status_code=404, detail="Verification request not found")
    status = "approved" if payload.decision == "approved" else "rejected"
    connection.execute("UPDATE verification_requests SET status=?,decision_reason=? WHERE id=?", (status, payload.reason, request_id))
    connection.commit()
    connection.close()
    audit(user, "consent_decision", "verification_request", request_id, {"decision": payload.decision})
    return {"request_id": request_id, "status": status}


@app.post("/api/v1/verification-requests/{request_id}/issue")
def issue_verification(request_id: str, user: dict[str, Any] = Depends(require_roles("verifier", "aicte_admin"))) -> dict[str, Any]:
    connection = connect()
    request = connection.execute("SELECT * FROM verification_requests WHERE id=? AND status='approved'", (request_id,)).fetchone()
    if not request:
        connection.close()
        raise HTTPException(status_code=409, detail="Request is not approved for issuance")
    enrolment = connection.execute("SELECT e.*,i.name AS institution_name,p.name AS programme_name FROM enrolments e JOIN institutions i ON i.id=e.institution_id JOIN programmes p ON p.id=e.programme_id WHERE e.id=?", (request["enrolment_id"],)).fetchone()
    if not enrolment:
        connection.close()
        raise HTTPException(status_code=404, detail="Enrolment not found")
    requested = json_value(request["requested_fields_json"], [])
    source = {"name": enrolment["name"], "institution": enrolment["institution_name"], "programme": enrolment["programme_name"], "academic_cycle": enrolment["academic_cycle"], "status": enrolment["status"], "student_institution_id": enrolment["student_institution_id"]}
    claims = {key: source[key] for key in requested if key in source}
    expires_at = request["expires_at"]
    payload = {"claims": claims, "request_id": request_id, "issued_at": now(), "expires_at": expires_at}
    token = secrets.token_urlsafe(28)
    signature = base64.urlsafe_b64encode(signing_key.sign(json_text(payload).encode())).decode()
    verification_id = new_id("ver")
    connection.execute("INSERT INTO verifications(id,request_id,token_hash,payload_json,signature,status,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?)", (
        verification_id, request_id, digest(token), json_text(payload), signature, "valid", now(), expires_at
    ))
    connection.commit()
    connection.close()
    audit(user, "verification_issued", "verification", verification_id, {"request_id": request_id, "field_count": len(claims)})
    return {"verification_id": verification_id, "token": token, "url": f"/verify/{token}", "claims": claims, "signature": signature}


@app.get("/verify/{token}")
def public_verify(token: str) -> dict[str, Any]:
    connection = connect()
    row = connection.execute("SELECT * FROM verifications WHERE token_hash=?", (digest(token),)).fetchone()
    connection.close()
    if not row:
        return {"status": "not_found", "claims": {}}
    status = row["status"]
    try:
        if datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc) and status == "valid":
            status = "expired"
    except ValueError:
        status = "unknown"
    return {"status": status, "verification_id": row["id"], "claims": json_value(row["payload_json"], {}).get("claims", {}), "signed": True, "expires_at": row["expires_at"]}


@app.post("/api/v1/verification/{verification_id}/revoke")
def revoke_verification(verification_id: str, user: dict[str, Any] = Depends(require_roles("aicte_admin", "aicte_reviewer"))) -> dict[str, str]:
    connection = connect()
    row = connection.execute("SELECT id FROM verifications WHERE id=?", (verification_id,)).fetchone()
    if not row:
        connection.close()
        raise HTTPException(status_code=404, detail="Verification not found")
    connection.execute("UPDATE verifications SET status='revoked' WHERE id=?", (verification_id,))
    connection.commit()
    connection.close()
    audit(user, "verification_revoked", "verification", verification_id, {})
    return {"verification_id": verification_id, "status": "revoked"}


@app.get("/api/v1/certificates/{enrolment_id}/preview")
def certificate_preview(enrolment_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    connection = connect()
    row = connection.execute("SELECT e.*,i.name AS institution_name,p.name AS programme_name FROM enrolments e JOIN institutions i ON i.id=e.institution_id JOIN programmes p ON p.id=e.programme_id WHERE e.id=?", (enrolment_id,)).fetchone()
    connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Enrolment not found")
    if user["role"].startswith("institution") and user["institution_id"] != row["institution_id"]:
        raise HTTPException(status_code=403, detail="Institution scope violation")
    return {"student_institution_id": row["student_institution_id"], "student_name": row["name"], "institution": row["institution_name"], "programme": row["programme_name"], "academic_cycle": row["academic_cycle"], "status": row["validation_state"], "apaar_display": row["apaar_value"] or "APAAR pending"}


@app.get("/api/v1/audit-events")
def audit_events(user: dict[str, Any] = Depends(require_roles("aicte_admin", "aicte_reviewer", "auditor", "institution_operator"))) -> dict[str, Any]:
    connection = connect()
    if user["role"] == "institution_operator":
        rows = connection.execute("SELECT * FROM audit_events WHERE target_id IN (SELECT id FROM submissions WHERE institution_id=?) ORDER BY created_at DESC LIMIT 100", (user["institution_id"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 100").fetchall()
    connection.close()
    return {"items": [{**dict(row), "details": json_value(row["details_json"], {})} for row in rows]}


@app.get("/api/v1/reports/enrolment")
def enrolment_report(user: dict[str, Any] = Depends(require_roles("aicte_admin", "aicte_reviewer", "auditor", "institution_operator"))) -> dict[str, Any]:
    connection = connect()
    if user["role"] == "institution_operator":
        rows = connection.execute("SELECT * FROM enrolments WHERE institution_id=?", (user["institution_id"],)).fetchall()
    else:
        rows = connection.execute("SELECT * FROM enrolments").fetchall()
    connection.close()
    return {"generated_at": now(), "items": [dict(row) for row in rows]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="initialize the synthetic prototype database")
    parser.add_argument("--reset", action="store_true", help="remove the local prototype database before seeding")
    args = parser.parse_args()
    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()
    seed_db() if args.seed else init_db()
    import uvicorn
    uvicorn.run(app, host=os.getenv("APAAR_API_HOST", "127.0.0.1"), port=int(os.getenv("APAAR_API_PORT", "8000")))
