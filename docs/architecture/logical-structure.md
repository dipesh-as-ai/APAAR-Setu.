# APAAR Setu Logical Structure

## 1. Architecture Style

Use a modular monolith with a worker process for the prototype. The modules are separated by domain boundaries and interfaces, but they can run in one API deployment. This keeps the build understandable while preserving a path to independent services later.

## 2. Runtime Components

```text
Browser
  |
  v
Web Frontend
  |
  v
API Gateway / Reverse Proxy
  |
  v
FastAPI Application
  |       |        |       |
  v       v        v       v
Postgres Redis  Object   Adapters
                   Store  (identity, approval, notify)
  ^
  |
Validation and Report Worker
```

## 3. Proposed Repository Layout

```text
apaar-setu/
├── apps/
│   └── web/
│       ├── src/
│       │   ├── app/
│       │   ├── components/
│       │   ├── features/
│       │   │   ├── auth/
│       │   │   ├── submissions/
│       │   │   ├── enrolments/
│       │   │   ├── review-cases/
│       │   │   ├── dashboards/
│       │   │   ├── verification/
│       │   │   ├── certificates/
│       │   │   └── audit/
│       │   ├── lib/
│       │   └── styles/
│       └── tests/
├── services/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── auth/
│   │   │   ├── domain/
│   │   │   ├── submissions/
│   │   │   ├── validation/
│   │   │   ├── enrolments/
│   │   │   ├── review_cases/
│   │   │   ├── verification/
│   │   │   ├── certificates/
│   │   │   ├── reports/
│   │   │   ├── audit/
│   │   │   ├── adapters/
│   │   │   ├── db/
│   │   │   └── settings.py
│   │   └── tests/
│   └── worker/
│       ├── jobs/
│       └── tests/
├── packages/
│   ├── api-contracts/
│   ├── design-tokens/
│   └── fixture-factory/
├── infra/
│   ├── compose/
│   ├── migrations/
│   └── seed/
├── docs/
├── .env.example
├── compose.yml
└── README.md
```

The exact directory names can change during implementation, but domain modules must not collapse into one unstructured `utils` or `services` folder.

## 4. Domain Modules

### Identity module

Owns APAAR state, provisional identities, identity-link history, masking, and adapter responses.

### Institution module

Owns institutions, users, organization scope, programmes, cycles, and approval snapshots.

### Submission module

Owns upload metadata, source files, parsed rows, idempotency, processing state, and row errors.

### Validation module

Owns rule definitions, rule execution, validation results, and severity classification.

### Enrolment module

Owns accepted student-enrolment records, status events, effective dates, category data, and intake reservations or counts.

### Review module

Owns duplicate cases, identity cases, intake cases, anomaly cases, assignments, decisions, and escalations.

### Verification module

Owns verifier requests, consent, signed claims, opaque tokens, expiry, and revocation.

### Reporting module

Owns dashboard projections, report jobs, filters, and export files.

### Audit module

Owns append-only audit events, correlation IDs, event digests, and authorized audit queries.

## 5. Core Relationships

```text
Institution
  -> Programme
  -> ApprovalSnapshot
  -> UserScope

Submission
  -> AcademicCycle
  -> Programme
  -> ApprovalSnapshot
  -> SubmissionRow

SubmissionRow
  -> StudentIdentity
  -> Enrolment
  -> ValidationResult
  -> ReviewCase

Enrolment
  -> VerificationRequest
  -> ConsentDecision
  -> SignedVerification
  -> Certificate

All privileged actions
  -> AuditEvent
```

## 6. Processing Flow

```text
Upload request
  -> create submission and checksum
  -> persist original file
  -> parse rows
  -> schema validation
  -> identity adapter validation
  -> deterministic business rules
  -> exact duplicate checks
  -> conflict candidate checks
  -> create review cases
  -> accept, reject, or hold each row
  -> update dashboard projection
  -> emit audit events
```

Each stage records a stage status and failure reason. A failed adapter call is distinguishable from a failed student-data rule.

## 7. State Ownership

| State or fact | Owning module |
|---|---|
| User role and organization scope | Auth and Institution |
| APAAR or provisional identity | Identity |
| Original uploaded bytes | Submission and Storage |
| Row validation result | Validation |
| Accepted enrolment status | Enrolment |
| Intake calculation | Enrolment and Approval |
| Case decision | Review |
| Student sharing decision | Verification |
| Signed token status | Verification |
| Dashboard aggregate | Reporting |
| Immutable action history | Audit |

## 8. Database Transaction Boundaries

- Create submission metadata and idempotency record in one transaction.
- Persist parsed row records in batches.
- Apply validation results independently so a single invalid row does not hide other results.
- Accept an enrolment and update intake counters in one transaction.
- Resolve a review case and record its audit event in one transaction.
- Issue a signed verification only after consent and eligibility are committed.
- Create a revocation and audit event in one transaction.

## 9. Read Models

The prototype can use PostgreSQL views or materialized views for:

- Institution intake utilization.
- AICTE regional summary.
- Validation workload.
- Open review cases.
- APAAR coverage.
- Verification activity.

The reporting module must label whether values are submitted, accepted, verified, active, or pending-review.

## 10. External Boundaries

No domain module directly imports an external provider SDK. Adapters translate provider responses into internal types and return explicit availability and retry state.

## 11. Security Boundaries

- Gateway: network and request protection.
- API: authentication, authorization, and field filtering.
- Domain: business invariants.
- Database: constraints and transaction integrity.
- Worker: isolated processing of untrusted files.
- Storage: access-controlled original submissions.
- Verification endpoint: minimal public response and token checks.
