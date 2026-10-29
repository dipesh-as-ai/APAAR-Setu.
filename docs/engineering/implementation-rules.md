# APAAR Setu Implementation Rules

## 1. Scope Rules

- Build the complete submission-to-verification vertical slice before adding advanced integrations.
- Use synthetic data only in the prototype.
- Treat external integrations as adapters with explicit unavailable, retryable, and failed states.
- Do not claim that a mock APAAR service is a live government identity verification service.
- Prefer deterministic rules over machine learning for decisions in the first release.

## 2. Domain Rules

- A submitted row is not automatically a verified enrolment.
- `Pending Review` records remain retained but are excluded from verified counts.
- Never delete an original submission through the normal application API.
- Every correction creates a new version or correction event.
- Every enrolment has institution, programme, academic cycle, admission type, status, and effective dates.
- Intake validation uses the approval snapshot attached to the submission, not the current mutable value.
- Supernumerary seats are counted separately from regular seats.
- Transfers, withdrawals, dual programmes, and completed records are represented by status and effective dates.
- Fuzzy identity matching creates candidates for review only.
- An anomaly score prioritizes review and never proves fraud.
- A provisional identity is never shown as an APAAR ID.
- Linkage from a provisional identity to APAAR requires an authorized action and an audit event.

## 3. Data Protection Rules

- Never use real APAAR, Aadhaar, passport, phone, email, or student data in development fixtures.
- Never log raw APAAR IDs or sensitive identity values.
- Use a keyed digest for exact lookup and store displayable values separately under encryption when required.
- Do not put APAAR, date of birth, or sensitive fields in QR payloads or public URLs.
- Verification tokens must be opaque, expiring, revocable, and non-sequential.
- Redact secrets, tokens, cookies, authorization headers, and uploaded row values from logs.
- Enforce data access by role and organization scope on the server.
- Store consent purpose, selected fields, decision, expiry, and actor.
- Do not expose more fields than the caller needs.

## 4. API Rules

- All write endpoints must support idempotency where retries can create records.
- All responses include a correlation ID.
- Use versioned paths such as `/api/v1`.
- Return consistent error envelopes with code, message, field errors, and correlation ID.
- Validate input with server-side schemas.
- Use cursor pagination for potentially large collections.
- Use explicit filters for institution, programme, cycle, status, and date range.
- Do not allow clients to select unauthorized institution IDs.
- Use optimistic concurrency or version checks for review-case updates.
- Return `202 Accepted` for background submissions and expose a status endpoint.
- Keep external service failures separate from domain validation failures.

## 5. Database Rules

- Use migrations for every schema change.
- Use foreign keys and database constraints for core invariants.
- Use explicit status values, not free-form strings, for lifecycle state.
- Use UTC timestamps in storage and ISO 8601 in APIs.
- Add created, updated, and actor metadata to mutable operational entities.
- Keep original upload files and parsed rows linked by submission ID.
- Add indexes for APAAR digest, institution, programme, academic cycle, status, and review state.
- Use transactions for acceptance, intake counters, and review decisions.
- Never rely on a frontend check for uniqueness or intake limits.

## 6. Frontend Rules

- Use the design tokens in `design.md`; do not introduce arbitrary colors or radii.
- Every form field has a visible label, helper text where needed, and an inline error state.
- Every page supports loading, empty, error, success, and permission-denied states.
- Tables expose their underlying data accessibly and have a mobile fallback.
- Statuses use text and icon in addition to color.
- Do not hide critical actions in hover-only controls.
- Do not use fake precision or invented operational metrics in the UI; label seeded values as sample data.
- Preserve filters and pagination when returning from a detail page.
- Avoid automatic refresh that steals focus.
- Support keyboard navigation and visible focus rings.
- Respect reduced-motion preferences.

## 7. Upload Rules

- Accept only allowlisted extensions and MIME types.
- Enforce maximum file size and row count.
- Reject macros and formulas; treat cell contents as untrusted values.
- Store a checksum of the original file.
- Validate the complete file before changing operational records.
- Return row and field references in error reports.
- Make retries safe using an idempotency key and file checksum.
- Do not silently truncate a file or skip invalid rows.

## 8. Testing Rules

- Unit test every validation rule with positive, negative, malformed, cancellation, and teardown cases where applicable.
- Test idempotent upload retry.
- Test institution data isolation.
- Test role and field-level authorization.
- Test cross-institution conflict detection with transfer and withdrawal exceptions.
- Test signed verification, expiry, and revocation.
- Test audit event creation for every privileged workflow.
- Use API integration tests for the primary upload flow.
- Use Playwright for the complete demo journey.
- Run accessibility checks on every main screen.
- Use fixture factories rather than hard-coded test rows scattered across tests.

## 9. Error and Retry Rules

- A failed external adapter call is not an invalid student record.
- Retry only operations explicitly marked retryable.
- Use bounded exponential backoff for background jobs.
- Make worker jobs idempotent.
- Show users whether an action failed, is pending, or requires correction.
- Preserve partial processing results with clear row-level state.
- Never automatically retry a destructive operation.

## 10. Review and Change Rules

- A review decision requires a reason.
- A reviewer cannot approve their own institution's exception unless explicitly enabled by policy and visibly marked.
- All rule changes are versioned and affect only new validation runs unless a revalidation is requested.
- Any change to identity linking, intake calculation, or verification claims requires tests and an updated decision record.
- Keep implementation work small enough to verify in one pull request.
