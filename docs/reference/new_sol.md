# APAAR Setu
## APAAR ID-Based Student Data Management and Verification Platform

## 1. Solution Summary

APAAR Setu is a central student-data platform for AICTE-approved institutions. It allows institutions to submit student-level admission and enrolment data, validates the data against configured rules, identifies duplicates and possible conflicts, and gives AICTE a live view of institutional enrolment.

The platform does not treat every uploaded row as immediately verified. Each record moves through a controlled lifecycle:

`Submitted -> Validating -> Accepted / Rejected / Pending Review -> Verified / Withdrawn / Completed`

This distinction is important. A student record can be retained for an audit even when the institution has exceeded its approved intake or when an identity conflict requires investigation. The platform records the issue and routes it to an authorized reviewer instead of silently deleting or falsely approving the record.

The system uses APAAR ID as the preferred academic identity key. Students who do not yet have an APAAR ID are handled through a provisional identity process and can be linked later after verification. This makes the platform useful during real admission operations without weakening the identity controls.

## 2. Problems Addressed

The solution directly addresses the following problems:

- AICTE receives only aggregate numbers from many institutions.
- Student records are difficult to compare across institutions and academic years.
- Duplicate or conflicting enrolments are discovered late.
- Approved intake and actual enrolment are not continuously monitored.
- Institutions use different ERP systems and data formats.
- Manual verification is slow and creates inconsistent decisions.
- Employers and regulators cannot easily verify an authentic student record.
- Reports for policy-making and accreditation require manual compilation.
- There is limited visibility into who submitted, changed, viewed, or verified data.

## 3. Main Users

### Institution Nodal Officer

Uploads or submits student records, reviews validation errors, confirms corrections, and responds to AICTE queries.

### Institution Data Operator

Performs data entry and upload operations but cannot approve institution-level exceptions or alter audit history.

### AICTE Administrator

Manages institutions, programmes, approval limits, validation rules, users, reports, and system configuration.

### AICTE Regional Officer

Reviews intake violations, duplicate-enrolment cases, anomaly alerts, and institution responses.

### Authorized Verifier

An employer, university, regulator, or other approved organization that verifies a limited student record with the required consent.

### Student

Views the records linked to their identity and approves or rejects sharing requests where consent is required.

### Auditor

Reads immutable audit records and compliance reports without changing operational data.

## 4. End-to-End Workflow

### Step 1: Institution onboarding

1. AICTE creates or imports the approved institution and programme information.
2. Each institution receives an organization account and one or more authorized users.
3. The institution selects its academic year, programme, shift, intake category, and upload method.
4. The system loads the applicable approved-intake snapshot for that institution and programme.

The approved-intake snapshot is versioned. If AICTE changes an approval later, old submissions still point to the approval version that was active at that time.

### Step 2: Student data submission

Institutions can submit data through:

- A web form for individual records.
- A fixed Excel or CSV template for bulk upload.
- A versioned REST API for ERP integration.
- A secure file drop for legacy systems in a future production phase.

Every submission receives an upload ID, institution ID, academic year, schema version, submitter ID, timestamp, and idempotency key. Repeating the same upload does not create duplicate records.

The original uploaded file is retained in restricted object storage for traceability. Parsed rows are stored separately so that individual corrections do not overwrite the original submission.

### Step 3: Staging and basic validation

The upload first enters a staging area. It is not visible as an accepted student record until validation begins.

The system checks:

- Required columns and supported schema version.
- Valid field types and date formats.
- Valid category values.
- Maximum file size and row count.
- Required fields for NRI, OCI, FN, lateral-entry, and supernumerary cases.
- Duplicate rows inside the same upload.
- Whether the submitter is authorized for the selected institution.

The institution receives a row-level result containing the row number, field name, error code, explanation, and correction suggestion.

### Step 4: Identity validation

APAAR is the preferred identity key, but it must not be assumed that every student has an immediately usable APAAR ID.

The identity workflow is:

1. Normalize the submitted APAAR value without changing its original value in the audit record.
2. Check format, presence, and checksum or service response where the real integration is available.
3. Use an APAAR adapter to query the approved identity service. The prototype uses a mock adapter with synthetic records.
4. Compare only the permitted identity attributes returned by the adapter, such as name, date of birth, or gender.
5. Mark the result as `Identity Matched`, `Identity Mismatch`, `APAAR Pending`, or `Manual Review`.

For a student without APAAR, the institution submits a provisional identity record containing the minimum required information and a reason code. The record receives a non-APAAR provisional ID and an expiry or follow-up date. Once APAAR becomes available, the linking operation requires an authorized review and creates an immutable link-history event.

The platform must never use a provisional ID as proof that the student has an APAAR ID.

### Step 5: Business-rule validation

The rule engine validates each row and the complete submission against the institution's approval data.

The main rules are:

- APAAR is present, correctly formatted, and not already linked to an incompatible active enrolment.
- The same APAAR is not duplicated for the same institution, programme, academic year, and enrolment instance.
- Actual enrolment does not exceed the relevant approved intake without creating an exception case.
- Supernumerary seats are counted separately from regular seats and are checked against the applicable limit.
- NRI, OCI, and FN classifications contain their required supporting fields.
- Category and nationality fields are not contradictory.
- Programme, academic year, shift, and admission type match the approved institution configuration.
- Lateral-entry and transfer records contain the required source and previous-status information.
- A withdrawn, transferred, or completed record cannot be counted as an active enrolment.
- Corrections preserve the previous value and the reason for change.

An intake violation does not destroy the student record. The record is retained as `Pending Review`, the excess count is shown separately, and an AICTE officer receives a case to resolve.

### Step 6: Duplicate and cross-institution checks

The platform performs three levels of duplicate analysis:

1. Exact duplicate detection using normalized APAAR and enrolment context.
2. Cross-institution conflict detection for overlapping active full-time enrolments.
3. Candidate matching for records without a usable APAAR, using normalized name, date of birth, parent or guardian name, and other permitted attributes.

Candidate matching never automatically merges or rejects a student. It creates a review case with the matched fields, similarity score, and reason. An authorized reviewer can confirm, dismiss, or request more information.

Legitimate situations such as transfer, withdrawal followed by re-admission, dual programmes, part-time study, and completed enrolment are represented through an enrolment-status and effective-date model rather than hard-coded exceptions.

### Step 7: Review and resolution

AICTE officers see cases grouped by severity:

- Blocking data error.
- Identity mismatch.
- Possible duplicate.
- Intake excess.
- Missing supporting information.
- Suspicious submission pattern.

Each case contains the source upload, affected records, rule results, institution response, officer decision, timestamps, and related evidence. Resolutions are `Confirmed`, `Dismissed`, `Corrected`, or `Escalated`.

The system never permits a reviewer to erase an original submission or audit event.

### Step 8: Acceptance and repository update

After validation, a row receives one of these states:

- `Accepted`: structurally valid and not awaiting a decision.
- `Verified`: identity and required business checks are complete.
- `Pending Review`: retained but requires an authorized decision.
- `Rejected`: cannot be processed until corrected.
- `Withdrawn`: institution has reported that the enrolment is no longer active.
- `Completed`: the academic relationship has ended.

Dashboards count these states separately. This prevents pending or rejected records from being presented as verified enrolment.

## 5. Core Data Model

The prototype should use a relational model with these main entities:

- `institution`: AICTE institution identity and status.
- `programme`: programme, level, mode, duration, and institution relationship.
- `approval_snapshot`: approved intake, category limits, shift, effective dates, and source version.
- `academic_cycle`: academic year and admission cycle.
- `student_identity`: normalized identity reference, APAAR state, provisional identity, and link history.
- `enrolment`: institution, programme, cycle, category, admission date, status, and effective dates.
- `submission`: upload metadata, source, schema version, checksum, and submitter.
- `submission_row`: original row reference, parsed values, validation state, and row-level errors.
- `validation_result`: rule ID, result, severity, explanation, and evidence reference.
- `review_case`: duplicate, mismatch, intake, or anomaly case with its lifecycle.
- `consent_request`: verifier, student, purpose, selected fields, expiry, and decision.
- `verification_record`: opaque verification token, signed claims, status, expiry, and revocation state.
- `audit_event`: actor, action, object, before/after digest, time, and correlation ID.

Important constraints include:

- Unique submission idempotency key per institution and source system.
- Unique active enrolment identity for the same institution, programme, cycle, and enrolment instance.
- No deletion of accepted records through the normal application API.
- Effective dates on enrolments so overlap checks are deterministic.
- Versioned approval snapshots rather than a single mutable intake number.

## 6. Dashboards and Reports

### Institution dashboard

- Upload status and processing progress.
- Accepted, rejected, and pending-review row counts.
- Intake utilization by programme, shift, category, and academic year.
- Missing APAAR and provisional-identity follow-up list.
- Downloadable correction report.
- Open AICTE queries and required response dates.

### AICTE dashboard

- Institution and programme coverage.
- Approved intake versus actual verified enrolment.
- Regular, supernumerary, NRI, OCI, and FN distribution.
- Pending identity and duplicate cases.
- State, region, programme, and academic-year filters.
- Institution risk indicators with explanations.
- Upload processing health and integration failures.

### Reports

- Academic-year enrolment report.
- Intake utilization and excess-admission report.
- Duplicate and cross-institution review report.
- APAAR coverage and pending-identity report.
- Institution response and case-resolution report.
- Audit and access report.
- Export to CSV or Excel in the prototype, with PDF generation as an enhancement.

Reports must identify whether a number represents submitted, accepted, verified, pending-review, or active enrolment data.

## 7. Verification and Verifiable Records

When a student record is verified, the platform can issue a signed verification artifact containing only the required claims, for example:

- Student name.
- Institution.
- Programme.
- Academic cycle or attendance period.
- Enrolment status.
- Verification timestamp and expiry.

The QR code should contain an opaque verification URL or token. It must not contain the full APAAR ID, date of birth, or other sensitive data.

The verification flow is:

1. The verifier registers and signs in.
2. The verifier selects the purpose and requests specific fields.
3. The student approves the request through the available consent channel.
4. The platform issues a short-lived, signed verification result.
5. The verifier sees only the approved fields.
6. Every request, approval, display, and revocation is audited.

AICTE and authorized regulatory users can have broader access through role-based and purpose-based policies. Public QR scanning should show only a minimal status such as `Valid`, `Expired`, `Revoked`, or `Not Found`, unless the student has explicitly authorized more information.

The certificate-print API should return the verified APAAR reference according to the configured institutional format. The system should support masking or partial display where displaying the complete identifier is unnecessary.

## 8. Security and Privacy Design

- Use OIDC or SSO for institutional and AICTE users.
- Require MFA for administrators, reviewers, auditors, and verifier administrators.
- Apply role-based access control with institution and region boundaries.
- Add purpose-based restrictions for student-data viewing.
- Encrypt data in transit and at rest.
- Store a keyed digest for exact APAAR lookup and protect any displayable value separately.
- Do not store Aadhaar data as part of this platform.
- Minimize collected identity fields and retain them only for the defined purpose.
- Use opaque tokens for public verification URLs.
- Record every create, update, review, view, export, consent, and verification action.
- Use correlation IDs to trace an upload from ingestion through validation and dashboard aggregation.
- Rate-limit APIs and restrict file types, sizes, and row counts.
- Run validation on untrusted uploaded data without executing formulas or macros from spreadsheets.
- Provide revocation and correction workflows rather than silently changing signed records.
- Use synthetic data in development and prototype demonstrations.

This design supports privacy and security requirements, but formal legal, security, and government-integration approval remains a production deployment activity rather than a prototype claim.

## 9. Anomaly Detection

The first version should rely primarily on deterministic rules because they are easier to explain and verify. An optional anomaly layer can prioritize inspections using signals such as:

- Sudden enrolment change compared with the institution's own history.
- Unusual concentration of submissions immediately before a deadline.
- Repeated correction and resubmission patterns.
- Unusual category distribution compared with comparable institutions.
- Repeated identity conflicts or intake violations.

Anomaly scores are investigation priorities, not evidence of fraud. The system must show the contributing reasons, allow an officer to dismiss or confirm the alert, and preserve the officer's decision. It must not reject a student solely because of a model score.

For the prototype, seeded anomaly cases and an explainable weighted score are sufficient. A machine-learning model can be evaluated later when enough historical, quality-controlled data exists.

## 10. Integration Architecture

Use adapters so that external services do not control the core domain logic:

- `ApprovalAdapter`: reads institution and programme approval snapshots.
- `IdentityAdapter`: validates APAAR through the real service or the mock service.
- `InstitutionAdapter`: accepts REST or file-based submissions.
- `CredentialAdapter`: signs and verifies records.
- `NotificationAdapter`: sends email, SMS, or portal notifications.

Every adapter returns a normalized result with source, timestamp, request ID, response state, and error details. External service downtime creates `Integration Pending` or `Retryable Failure`; it must not be confused with an invalid student record.

The prototype should use:

- Synthetic institution, programme, approval, and student datasets.
- A local mock APAAR service.
- A documented REST API.
- A local signed-verification service.

The prototype must not claim live access to APAAR, DigiLocker, ABC, or AICTE systems unless such access is actually available in the demonstration environment.

## 11. Prototype Scope

The prototype should implement one complete vertical slice:

1. AICTE creates two synthetic institutions and their approved-intake snapshots.
2. Institution A logs in and uploads a CSV containing valid and invalid rows.
3. The system displays row-level schema and identity errors.
4. The mock APAAR adapter validates synthetic APAAR values.
5. The rule engine detects an exact duplicate, an intake excess, a category inconsistency, and a cross-institution conflict.
6. The duplicate and intake cases appear in the AICTE review queue.
7. The officer dismisses one legitimate conflict and confirms one intake exception.
8. The institution dashboard updates accepted, verified, rejected, and pending-review counts.
9. A synthetic employer requests selected fields.
10. The student approves the request using a prototype consent screen.
11. The system produces a signed verification result and QR code.
12. The verifier scans or opens the QR URL and sees the permitted fields.
13. The audit viewer shows the upload, validation, review, consent, and verification events.

The demo should include a visible processing status so that asynchronous work is understandable. It should also allow the evaluator to inspect the rejected row and the reason for each flag.

## 12. Suggested Technical Stack

### Prototype

- Frontend: React with Vite and TypeScript.
- UI: a simple component library with accessible tables, forms, and status badges.
- Backend: Python FastAPI with Pydantic schemas.
- Database: PostgreSQL.
- Background processing: Redis and Celery, or a simple worker process for the first demo.
- File processing: Pandas and openpyxl with formula and macro handling disabled.
- Authentication: Keycloak for realistic OIDC and RBAC, or a small JWT service if setup time is limited.
- Rules: Python service with database-backed rule definitions.
- Duplicate candidates: RapidFuzz plus normalized comparison fields.
- Signing: Python cryptography library using Ed25519.
- QR generation: a standard QR-code library containing an opaque verification URL.
- Charts: Apache ECharts.
- Packaging: Docker Compose.
- Testing: Pytest, FastAPI test client, and Playwright for the main user flows.

### Production evolution

- API gateway and institution-specific credentials or mTLS.
- Object storage for original submissions and generated reports.
- Kafka or a managed queue when upload volume requires it.
- Read replicas or an analytics store for large dashboard workloads.
- Centralized logs, metrics, tracing, alerting, and backup recovery.
- Managed key storage or an HSM for signing keys.
- Independent security testing and operational monitoring.

Kubernetes and a large analytics platform are not necessary for the SIH prototype. They can be described as the scale-out path after the vertical slice works.

## 13. API Examples

### Upload submission

`POST /api/v1/institutions/{institution_id}/submissions`

The request includes the academic cycle, programme, schema version, idempotency key, and CSV or JSON payload. The response returns a submission ID and `processing` status.

### Submission status

`GET /api/v1/submissions/{submission_id}`

Returns processing progress, accepted rows, rejected rows, pending-review rows, and downloadable error-report links.

### Student record

`GET /api/v1/enrolments/{enrolment_id}`

Returns only fields allowed for the caller's role and institution scope.

### Verification request

`POST /api/v1/verification-requests`

Creates a purpose-bound request with selected fields and an expiry time.

### Public verification

`GET /verify/{opaque_token}`

Returns a minimal verification result and signed status without exposing the token's underlying student identifier.

All write APIs should support idempotency and return a correlation ID.

## 14. How the Solution Solves the Actual Issue

| Existing issue | Platform response |
|---|---|
| Only aggregate institutional data is available | Institutions submit student-level records linked to enrolment and approval context |
| Duplicate records are discovered late | Exact, cross-institution, and review-based candidate matching runs during ingestion |
| Intake excess is detected after the fact | Approved-intake snapshots are checked during submission and produce immediate review cases |
| Institutions use different systems | Web upload, REST API, and adapter-based integration are supported |
| Manual verification is slow | Signed, consent-based, purpose-limited verification is available through QR and API |
| Data corrections are hard to trace | Versioned submissions and append-only audit events preserve the history |
| Reports require manual work | Dashboards and filtered exports are generated from validated states |
| Students may not have APAAR immediately | Provisional identity with a later controlled-link process avoids blocking legitimate admission |
| AICTE cannot prioritize inspections | Explainable risk indicators prioritize cases without making unsupported fraud claims |

## 15. Success Criteria for the Demonstration

The prototype is successful if an evaluator can:

- Log in as an institution and submit a supplied CSV.
- See exact row-level validation errors.
- See the difference between accepted, verified, rejected, and pending-review records.
- Observe intake utilization change after processing.
- Find a duplicate and cross-institution conflict.
- Resolve a review case with an auditable decision.
- Request and approve limited student-data sharing.
- Verify a signed QR record and see its revocation or expiry behavior.
- Open the audit trail and trace the complete transaction.
- Use synthetic mock adapters without requiring unavailable government credentials.

The most important outcome is not the number of technologies shown. It is a reliable, demonstrable flow from institution submission to AICTE validation, review, monitoring, and authorized verification.
