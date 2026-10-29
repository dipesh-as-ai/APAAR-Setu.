# APAAR Setu Product Requirements Document

## 1. Product

APAAR Setu is an APAAR ID-based student data management and verification platform for AICTE-approved institutions. It converts institution submissions into validated, auditable student enrolment records and gives AICTE an operational view of intake, enrolment, identity conflicts, and verification activity.

The first release is an SIH prototype. It must demonstrate a complete working flow with synthetic data and mock external services. It must not depend on live APAAR, DigiLocker, ABC, or AICTE credentials.

## 2. Problem

AICTE receives detailed student data from some institutions but mostly aggregate enrolment information from others. This makes it difficult to detect duplicate enrolment, invalid records, intake excess, category inconsistencies, and changes to institutional data. Verification and reporting are consequently delayed and manual.

## 3. Product Goal

Provide a trusted, reviewable path from institution submission to AICTE monitoring and authorized student-record verification.

## 4. Objectives

- Collect student-level data through a simple web upload and a documented API.
- Validate uploaded data before it becomes accepted enrolment data.
- Use APAAR as the preferred identity key while supporting controlled provisional identities.
- Detect duplicate, conflicting, incomplete, and intake-exceeding records.
- Give AICTE and institutions role-scoped dashboards.
- Provide consent-based, limited-field verification for authorized verifiers.
- Preserve submission history, review decisions, consent, and access events.
- Produce actionable reports for monitoring and policy work.

## 5. Success Measures

- An institution can upload a valid or invalid CSV and receive row-level results.
- A 500-row synthetic upload completes without duplicate creation on retry.
- The system detects seeded duplicate, invalid identity, intake excess, category mismatch, and cross-institution conflict cases.
- AICTE can resolve a review case without deleting the original data.
- Dashboard counts distinguish submitted, accepted, verified, rejected, and pending-review records.
- A verifier can receive only consented fields through a signed QR verification flow.
- An auditor can trace the upload, validation, review, consent, and verification events.
- The prototype can run locally with documented setup commands.

## 6. Personas and Permissions

| Persona | Primary capabilities |
|---|---|
| Institution Data Operator | Upload files, view own errors, view own records |
| Institution Nodal Officer | All operator actions, submit corrections, respond to AICTE cases |
| AICTE Administrator | Manage institutions, programmes, approvals, users, rules, reports |
| AICTE Reviewer | Review conflicts, intake exceptions, and anomaly cases |
| Student | View linked records and approve or reject sharing requests |
| Authorized Verifier | Request and view consented verification fields |
| Auditor | Read audit events and reports without changing operational data |

## 7. Core Record Lifecycle

```text
Submitted
  -> Validating
  -> Accepted
  -> Verified

Validating -> Rejected
Validating -> Pending Review
Pending Review -> Verified
Pending Review -> Rejected
Verified -> Withdrawn
Verified -> Completed
```

`Pending Review` means the record is retained but must not be counted as verified enrolment until an authorized decision is made.

## 8. Functional Requirements

### FR-01 Institution and programme setup

AICTE administrators can create institutions, programmes, academic cycles, shifts, categories, and versioned approved-intake snapshots.

### FR-02 Authentication and authorization

Users sign in and receive permissions based on role and organization scope. Institution users can access only their institution's data. Privileged actions require an audit event.

### FR-03 Student data submission

Institutions can submit individual records and bulk CSV files. The API accepts versioned JSON submissions. Each submission has an idempotency key, checksum, submitter, schema version, academic cycle, and processing status.

### FR-04 Schema validation

The system validates column names, data types, required fields, allowed values, date ranges, file size, row count, and category-specific fields. Errors identify row, field, error code, message, and correction guidance.

### FR-05 Identity validation

The system validates APAAR format and calls an identity adapter. The prototype adapter uses synthetic records. Results are `matched`, `mismatch`, `pending`, or `manual_review`. A provisional identity is allowed only with a reason and follow-up date.

### FR-06 Business-rule validation

The rule engine validates duplicate identity, intake, supernumerary limits, category consistency, programme eligibility, transfer state, and active enrolment status.

### FR-07 Duplicate and conflict detection

The system detects exact duplicates and possible cross-institution conflicts. Fuzzy matches create review candidates and never auto-merge or auto-reject students.

### FR-08 Review workflow

Authorized AICTE reviewers can view case evidence, communicate a decision, add a reason, and resolve or escalate the case. Original uploads and audit events are immutable through the application.

### FR-09 Dashboards

Institution dashboards show processing status, errors, intake use, and open cases. AICTE dashboards show coverage, enrolment, intake excess, category distribution, conflicts, and unresolved cases.

### FR-10 Consent and verification

An authorized verifier can request selected fields for a stated purpose. A student can approve or reject the request. The verification response is signed, expiry-bound, and limited to approved fields.

### FR-11 QR and certificate support

The system generates a QR containing an opaque verification token. The certificate preview shows institution student ID, APAAR display value according to policy, programme, status, and verification QR. The public endpoint must not expose sensitive data by default.

### FR-12 Reports and exports

Users with permission can export filtered CSV or Excel reports. Reports must identify the underlying record state and filter scope.

### FR-13 Audit trail

The system records submission, validation, review, correction, consent, verification, export, and access events with actor, organization, timestamp, correlation ID, target, action, and before/after digests where applicable.

## 9. Required Data Fields

The initial student submission schema includes:

- Institution ID
- Programme ID
- Academic cycle
- Student institution ID
- Student name
- APAAR ID or provisional identity reference
- Date of birth
- Gender, where required by the configured schema
- Admission date
- Enrolment status
- Admission category
- Regular or supernumerary classification
- NRI status and required sponsor fields
- OCI status and required reference fields
- FN status and required nationality or passport reference fields
- Previous institution and transfer details, where applicable

## 10. Non-Functional Requirements

- The local prototype starts with one documented command.
- A 500-row upload is processed within an acceptable demo interval and reports progress.
- API responses include correlation IDs.
- All protected endpoints enforce authentication and authorization server-side.
- The UI is keyboard accessible and usable at desktop and mobile widths.
- Sensitive values never appear in logs, URLs, or error messages.
- Processing failures are retryable and do not create duplicate records.
- The system displays integration downtime separately from invalid student data.
- The design supports synthetic data only during prototype development.

## 11. Prototype Scope

### In scope

- Seeded users, institutions, programmes, approvals, and synthetic students.
- CSV upload and row-level error report.
- Mock APAAR adapter.
- Deterministic validation rules.
- Review queue and case resolution.
- Institution and AICTE dashboards.
- Student consent and verifier flow.
- Ed25519 signed QR verification.
- Audit log and CSV export.
- Certificate preview.

### Out of scope for the first prototype

- Live government APIs.
- Real student or Aadhaar data.
- Full ERP connector catalogue.
- Machine-learning fraud decisions.
- Production multi-region hosting.
- Production legal or security certification.
- Kubernetes and Kafka deployment.

## 12. Acceptance Demo

1. Log in as Institution A.
2. Upload the seeded CSV.
3. Show row-level errors and processing progress.
4. Show one exact duplicate, one identity mismatch, one intake excess, and one cross-institution conflict.
5. Log in as an AICTE reviewer and resolve one case.
6. Show changed dashboard totals.
7. Log in as a verifier and request limited fields.
8. Approve the request as the student.
9. Verify the signed QR.
10. Open the audit log and certificate preview.
