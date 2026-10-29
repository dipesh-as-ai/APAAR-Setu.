# APAAR Setu APIs and Gateway Design

## 1. Gateway Responsibilities

The gateway is the single public entry point for the web application and institution integrations. It should be a thin policy boundary, not a second business-logic implementation.

The gateway is responsible for:

- TLS termination in deployed environments.
- Authentication token validation.
- Request size and rate limits.
- Correlation ID creation and propagation.
- CORS policy for approved origins.
- Route-level access policy.
- Idempotency-key forwarding.
- Redaction-aware request logging.
- API version routing.
- Health and readiness endpoints.

The FastAPI application remains responsible for authorization decisions, validation, transactions, and domain behavior. The gateway must not be the only place where access is enforced.

## 2. Route Groups

Base path: `/api/v1`

| Group | Purpose |
|---|---|
| `/auth` | Session and current-user information |
| `/institutions` | Institution and user-scoped data |
| `/programmes` | Programme and approval context |
| `/submissions` | Upload, processing status, and errors |
| `/enrolments` | Student enrolment records |
| `/validation` | Validation results and rule metadata |
| `/review-cases` | AICTE review workflow |
| `/dashboards` | Aggregated operational views |
| `/verification-requests` | Consent-based field requests |
| `/verification` | Signed and public verification |
| `/certificates` | Certificate preview and print payload |
| `/reports` | Filtered exports |
| `/audit-events` | Authorized audit access |
| `/integrations` | Adapter health and administration |

## 3. Common API Conventions

### Request headers

- `Authorization: Bearer <token>` for protected routes.
- `X-Correlation-Id: <uuid>` optional from clients; generated if absent.
- `Idempotency-Key: <opaque-key>` required for retriable create or upload operations.
- `If-Match: <version>` required for concurrent review-case updates.

### Response headers

- `X-Correlation-Id` on every response.
- `Retry-After` for rate limits and explicitly retryable processing states.

### Error envelope

```json
{
  "error": {
    "code": "submission_validation_failed",
    "message": "The submission contains rows that require correction.",
    "field_errors": [
      {
        "row": 12,
        "field": "apaar_id",
        "code": "invalid_format",
        "message": "The APAAR value is not valid for this schema."
      }
    ],
    "correlation_id": "4bcf6a43-8e3a-4bd8-9234-5dcb6bd8e2a1"
  }
}
```

## 4. Authentication APIs

### `GET /api/v1/auth/me`

Returns the authenticated user, organization scope, roles, and permissions.

### `POST /api/v1/auth/logout`

Revokes the local session or refresh token where the selected authentication provider supports it.

The prototype may use seeded accounts. Production should use OIDC and MFA for privileged users.

## 5. Institution and Approval APIs

### `GET /api/v1/institutions`

AICTE administrators list institutions. Institution users receive only their own organization unless explicitly authorized.

### `GET /api/v1/institutions/{institution_id}`

Returns institution metadata and active status.

### `GET /api/v1/institutions/{institution_id}/approvals`

Returns versioned approval snapshots filtered by programme and academic cycle.

### `POST /api/v1/institutions/{institution_id}/approvals`

AICTE administrator-only operation to create a new approval snapshot. Existing submissions retain their attached snapshot.

## 6. Submission APIs

### `POST /api/v1/institutions/{institution_id}/submissions`

Accepts CSV, JSON, or a multipart upload.

Expected metadata:

```json
{
  "academic_cycle": "2026-27",
  "programme_id": "prog-btech-cse",
  "schema_version": "student-enrolment-v1",
  "source_system": "web-upload",
  "idempotency_key": "institution-a-2026-07-001"
}
```

Response: `202 Accepted`

```json
{
  "submission_id": "sub_01J...",
  "status": "validating",
  "status_url": "/api/v1/submissions/sub_01J...",
  "correlation_id": "4bcf6a43-8e3a-4bd8-9234-5dcb6bd8e2a1"
}
```

### `GET /api/v1/submissions/{submission_id}`

Returns processing state, row totals, accepted, rejected, pending-review, and retry information.

### `GET /api/v1/submissions/{submission_id}/errors`

Returns paginated row-level errors and supports CSV error-report download.

### `POST /api/v1/submissions/{submission_id}/retry`

Retries only a submission that has a retryable infrastructure or integration failure. It does not bypass domain validation.

## 7. Enrolment APIs

### `GET /api/v1/enrolments`

Supports filters for institution, programme, cycle, status, category, and validation state. Results are scoped to the caller.

### `GET /api/v1/enrolments/{enrolment_id}`

Returns fields permitted by the caller role. Sensitive identity values are masked by default.

### `PATCH /api/v1/enrolments/{enrolment_id}`

Creates a correction event rather than mutating the original submission. Requires a reason and concurrency version.

### `POST /api/v1/enrolments/{enrolment_id}/status-events`

Creates a transfer, withdrawal, or completion event with effective date and supporting reason.

## 8. Validation and Review APIs

### `GET /api/v1/enrolments/{enrolment_id}/validation-results`

Returns rule results, severity, explanation, and current resolution state.

### `GET /api/v1/review-cases`

Lists cases filtered by type, severity, status, institution, and assigned reviewer.

### `GET /api/v1/review-cases/{case_id}`

Returns affected records, validation evidence, source submission, history, and permitted identity comparison fields.

### `PATCH /api/v1/review-cases/{case_id}`

Resolves or escalates a case. Requires `If-Match` and a decision reason.

Example:

```json
{
  "decision": "dismissed",
  "reason": "The earlier enrolment was withdrawn before this admission date.",
  "resolution_code": "valid_transfer_or_reentry"
}
```

## 9. Dashboard APIs

### `GET /api/v1/dashboards/institution`

Returns upload health, processing counts, intake utilization, pending identity follow-up, and open institution cases.

### `GET /api/v1/dashboards/aicte`

Returns aggregate counts, intake excess, conflict counts, regional filters, and review workload.

### `GET /api/v1/dashboards/aicte/stream`

Optional Server-Sent Events endpoint for dashboard updates. The first prototype may use polling every 5 to 10 seconds instead of SSE.

## 10. Consent and Verification APIs

### `POST /api/v1/verification-requests`

Creates a purpose-bound request.

```json
{
  "enrolment_id": "enr_01J...",
  "purpose": "employment_screening",
  "requested_fields": ["name", "institution", "programme", "status"],
  "expires_at": "2026-11-01T12:00:00Z"
}
```

### `GET /api/v1/verification-requests/{request_id}`

Returns request state without exposing unapproved fields.

### `POST /api/v1/verification-requests/{request_id}/decision`

Student-only decision endpoint with `approved` or `rejected` and optional reason.

### `POST /api/v1/verification-requests/{request_id}/issue`

Issues a signed verification artifact after consent and eligibility checks.

### `GET /verify/{opaque_token}`

Public or verifier-facing endpoint. Returns minimal status and approved claims only. It never derives identity information from a sequential token.

### `POST /api/v1/verification/{verification_id}/revoke`

Authorized revocation endpoint. Revocation is audited and reflected by QR verification.

## 11. Certificate APIs

### `GET /api/v1/certificates/{enrolment_id}/preview`

Returns a print-safe certificate model with institution student ID, approved APAAR display mode, programme, status, issue date, and QR token.

### `POST /api/v1/certificates/{enrolment_id}/render`

Prototype endpoint that generates a PDF or browser print view. Production rendering can be moved to a dedicated document service.

## 12. Reports and Audit APIs

### `POST /api/v1/reports/enrolment`

Creates an asynchronous filtered report job.

### `GET /api/v1/reports/{report_id}`

Returns report status and download link when ready.

### `GET /api/v1/audit-events`

Auditor and authorized administrators can filter by actor, action, target, date, institution, and correlation ID.

## 13. External Adapter Gateways

External services are called through internal adapter interfaces, not directly from route handlers.

### Identity gateway

```text
IdentityAdapter
  -> MockIdentityProvider in prototype
  -> APAAR/approved provider adapter in production
```

Normalized response:

```json
{
  "state": "matched",
  "provider": "mock-apaar",
  "provider_reference": "mock_ref_123",
  "matched_fields": ["name", "date_of_birth"],
  "retryable": false,
  "observed_at": "2026-10-26T10:00:00Z"
}
```

### Approval gateway

Provides the approval snapshot needed for intake validation. If unavailable, the submission becomes `integration_pending`; it is not classified as invalid.

### Notification gateway

Supports in-app notification first, with email or SMS as replaceable providers later.

## 14. Gateway Security Controls

- Allow only known content types.
- Limit upload size and request body size.
- Rate-limit public verification and failed authentication.
- Apply stricter limits to report generation and bulk uploads.
- Reject unexpected fields where strict schemas are required.
- Redact authorization and identity values in gateway logs.
- Add security headers and CSRF protection where cookie sessions are used.
- Validate CORS against an allowlist.
- Set request timeouts and return explicit timeout errors.
