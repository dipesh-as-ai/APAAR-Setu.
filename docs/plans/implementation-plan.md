# APAAR Setu Implementation Plan

## 1. Delivery Strategy

Build one reliable vertical slice first, then expand. The first demonstrable path is:

`Institution login -> CSV upload -> validation -> review case -> AICTE dashboard -> consent -> signed QR verification -> audit trail`

Do not start with advanced analytics, live government integrations, Kafka, Kubernetes, or a complete ERP connector suite.

## 2. Workstreams

1. Product and domain foundation.
2. Backend and database.
3. Frontend and design system.
4. Validation and identity adapters.
5. Review, consent, and verification.
6. Reports, audit, and demo data.
7. Testing, packaging, and demonstration readiness.

## 3. Phase 0: Project Bootstrap

### Tasks

- Create the web, API, worker, packages, and infrastructure folders described in `logical-structure.md`.
- Add environment templates and Docker Compose services.
- Configure formatting, linting, type checking, and test commands.
- Add a health endpoint and a basic frontend shell.
- Add PostgreSQL migrations and a seed command.

### Exit criteria

- The local stack starts with one documented command.
- Web, API, database, Redis, and worker health are visible.
- A seed command can create a clean development database.
- No secrets are committed.

## 4. Phase 1: Identity, Access, and Institution Setup

### Tasks

- Add seeded users for every prototype persona.
- Implement session handling and role checks.
- Implement institution and programme records.
- Implement academic cycles and versioned approval snapshots.
- Add organization-scope authorization tests.

### Exit criteria

- Institution users see only their own institution.
- AICTE users can see the configured scope.
- Unauthorized API requests fail server-side.
- Approval snapshots can be selected for a submission.

## 5. Phase 2: Submission Pipeline

### Tasks

- Define the student-enrolment CSV schema.
- Build the upload form and sample-template download.
- Add file checksum and idempotency handling.
- Store the original file and submission metadata.
- Parse rows without executing formulas or macros.
- Add asynchronous processing status.
- Implement row-level schema errors and downloadable error reports.

### Exit criteria

- A 500-row file can be uploaded.
- A repeated request with the same idempotency key does not duplicate records.
- Invalid columns, dates, values, and missing fields are reported by row and field.
- Processing failures show retryable versus non-retryable state.

## 6. Phase 3: Identity and Validation Engine

### Tasks

- Implement the mock APAAR adapter with synthetic records.
- Implement APAAR normalization and format checks.
- Implement provisional identity state and follow-up date.
- Add deterministic rule definitions and execution.
- Add duplicate checks.
- Add intake and supernumerary validation.
- Add NRI, OCI, and FN consistency checks.
- Add active enrolment overlap detection.
- Add review-only fuzzy candidate matching.

### Exit criteria

- Every seeded invalid case is detected with a stable rule code.
- Fuzzy matching creates a review candidate and never auto-merges.
- Intake excess is held for review instead of deleting the row.
- External adapter unavailability is represented separately from invalid data.
- Rule results are persisted and visible in the API.

## 7. Phase 4: Review and Institution Workflows

### Tasks

- Build the institution results screen.
- Build the AICTE review queue.
- Build case detail with evidence and activity timeline.
- Add decisions: confirm, dismiss, correct, escalate.
- Add optimistic concurrency for case decisions.
- Add correction events without overwriting the original upload.

### Exit criteria

- A reviewer can resolve the seeded duplicate and intake cases.
- Every decision requires a reason.
- A resolved case changes the correct dashboard count.
- Original data remains traceable after correction.

## 8. Phase 5: Dashboards and Reporting

### Tasks

- Build institution dashboard.
- Build AICTE dashboard.
- Add intake utilization by institution and programme.
- Add status and validation summaries.
- Add review workload and conflict indicators.
- Add filtered CSV or Excel export.
- Add report-generation status for larger exports.

### Exit criteria

- Dashboard counts distinguish submitted, accepted, verified, rejected, and pending-review.
- Filters are scoped to the caller's permissions.
- Export results match the selected filters.
- Empty, loading, and error states are implemented.

## 9. Phase 6: Consent, Verification, and Certificates

### Tasks

- Build verifier registration or seeded verifier access.
- Build field-selection verification request.
- Build student consent screen.
- Implement Ed25519 signing and verification.
- Generate opaque QR verification tokens.
- Build public verification status page.
- Add expiry and revocation.
- Build certificate preview and print-safe rendering.
- Add audit events for request, decision, issue, view, and revoke.

### Exit criteria

- A verifier cannot see unapproved fields.
- A student can approve or reject a request.
- The signed response fails verification if changed.
- Expired and revoked tokens show the correct status.
- The certificate preview includes institution student ID, configured APAAR display, and QR.

## 10. Phase 7: Audit and Operational Hardening

### Tasks

- Add append-only audit event storage.
- Add correlation IDs through frontend, API, worker, and adapter calls.
- Add sensitive-field redaction to logs.
- Add rate limits and upload limits.
- Add readiness and liveness checks.
- Add structured error handling.
- Add database backup instructions for local evaluation.

### Exit criteria

- The complete demo can be traced using one correlation ID.
- Sensitive values do not appear in logs, URLs, or errors.
- Privileged actions have audit events.
- Restarting the worker does not duplicate processing.

## 11. Phase 8: Testing and Demo Readiness

### Automated tests

- Validation rule unit tests.
- Identity adapter contract tests.
- Submission API integration tests.
- Idempotency tests.
- Authorization and institution-isolation tests.
- Review decision concurrency tests.
- Signed verification and revocation tests.
- Report-filter tests.
- Audit-event tests.
- Frontend component and accessibility tests.
- Playwright end-to-end demo test.

### Manual checks

- Keyboard-only navigation.
- 360px, 768px, 1280px, and 1440px layouts.
- Long names and long validation messages.
- Empty database state.
- Failed mock adapter state.
- Duplicate upload retry.
- Expired consent request.
- Revoked verification token.
- Certificate print preview.

### Exit criteria

- The seeded end-to-end scenario passes from clean database to QR verification.
- The demo can be reset with one command.
- Setup documentation is accurate on a fresh machine.
- No real personal or government identity data is present.

## 12. Recommended Build Order by Team

### Backend developer

1. Database models and migrations.
2. Seed data and auth scope.
3. Submission pipeline.
4. Validation rules.
5. Review APIs.
6. Verification APIs.
7. Reports and audit.

### Frontend developer

1. Shell, navigation, tokens, and auth state.
2. Upload workflow.
3. Results and error report.
4. Dashboards.
5. Review queue and case detail.
6. Consent and verification.
7. Certificate preview and responsive polish.

### Integration or platform developer

1. Docker Compose and environment setup.
2. Mock adapters.
3. Worker runtime.
4. API contract generation.
5. Logging and health checks.
6. CI test pipeline.

## 13. Demo Dataset Design

Create a deterministic dataset with:

- Institution A with approved intake 100 and 92 valid active students.
- Institution B with approved intake 80 and a separate programme.
- One duplicated APAAR within Institution A.
- One student active in both institutions with overlapping dates.
- One student with invalid APAAR format.
- One student missing APAAR and marked provisional.
- One NRI row missing sponsor data.
- One OCI row with inconsistent nationality.
- One FN row with missing nationality reference.
- Twelve additional admissions over the approved intake.
- One legitimate withdrawn-then-reenrolled case.
- One fuzzy candidate pair without APAAR that requires manual review.

All values must be clearly synthetic and documented as demo data.

## 14. Definition of Done

A feature is complete only when:

- The API behavior is documented.
- Authorization is tested.
- Loading, empty, error, and success UI states exist.
- Audit behavior is defined for privileged actions.
- Database migration and seed changes are included.
- Unit and integration tests cover the main path and at least one failure path.
- The feature works with the demo dataset.
- Sensitive values are not exposed in logs or URLs.
- The implementation follows `implementation-rules.md` and `design.md`.

## 15. First Execution Sprint

Start with the smallest executable slice:

1. Bootstrap Docker Compose, frontend, API, PostgreSQL, and Redis.
2. Add migrations for users, institutions, programmes, cycles, approvals, submissions, rows, and audit events.
3. Add seeded login accounts and institution scope.
4. Implement CSV upload and submission status.
5. Implement schema validation and row-level error display.
6. Add the first dashboard showing upload counts.
7. Add the mock APAAR adapter and one duplicate rule.

The first sprint is successful when Institution A can log in, upload the seeded CSV, see processing progress, and receive a persisted row-level result.

## 16. Future Production Work

After the SIH prototype is stable, plan separately for:

- External API onboarding and contract verification.
- Institutional ERP integration kits.
- Formal privacy and security review.
- High-volume ingestion and analytics projections.
- Key management and signing-key rotation.
- Disaster recovery and retention operations.
- Accessibility audit and user research with institutions.
