# APAAR Setu Design System

## 1. Design Read

This is a trust-first public-sector operations product for AICTE officers, institutional administrators, students, and authorized verifiers. The interface should feel calm, precise, accountable, and professional rather than futuristic or consumer-oriented.

Design direction: civic precision with an evidence-led data workspace.

## 2. Design Principles

- Make status and ownership visible at every step.
- Prefer clear tables, timelines, and review evidence over decorative cards.
- Use color to communicate state, not to decorate the page.
- Keep the primary action obvious and the destructive action difficult to trigger accidentally.
- Preserve context when moving between upload, validation, review, and verification.
- Show why a record was flagged, not only that it was flagged.
- Use plain language suitable for a government and institutional audience.
- Optimize for keyboard use, readable density, and low-bandwidth conditions.

## 3. Visual Theme

### Theme name

`Civic Precision`

### Palette

Use one restrained primary accent and separate semantic colors only for status communication.

| Token | Value | Use |
|---|---|---|
| Ink | `#172033` | Main text and navigation |
| Ink muted | `#506078` | Supporting text |
| Canvas | `#F4F7FA` | Application background |
| Surface | `#FFFFFF` | Panels and forms |
| Border | `#D6DEE8` | Dividers and input borders |
| Primary | `#0F766E` | Primary actions, links, active state |
| Primary dark | `#115E59` | Hover and focus emphasis |
| Warning | `#B45309` | Pending review and attention |
| Danger | `#B42318` | Rejected and critical errors |
| Success | `#16794C` | Verified and accepted |
| Info | `#2457A6` | Informational state |

Avoid gradients, neon effects, decorative glow, and excessive rounded cards. Semantic colors must never be the only way a state is communicated; pair them with labels and icons.

## 4. Typography

- Primary font: IBM Plex Sans or an equivalent self-hosted accessible sans-serif.
- Numeric and code font: IBM Plex Mono.
- Body size: 15px or 16px with comfortable line height.
- Data table size: 13px to 14px, never below 12px.
- Headings use weight and spacing rather than oversized marketing typography.
- Use sentence case for labels and actions.
- Use all caps only for short system labels such as status metadata, not headings.

## 5. Application Shell

### Desktop

- Persistent left navigation, 248px wide.
- Top bar with institution or AICTE scope, search, notifications, help, and user menu.
- Main content constrained to approximately 1400px.
- Breadcrumbs on detail and review pages.
- Page title, one-sentence context, and one primary action.

### Mobile and narrow screens

- Collapse navigation into a drawer.
- Convert wide tables into stacked record rows or horizontal scrolling with pinned identity columns.
- Keep primary action visible near the page title.
- Preserve status, error, and consent information without relying on hover.

## 6. Page Patterns

### Dashboard

Use a short metric row, a dominant operational chart or queue, and a compact recent-activity list. Do not fill the page with equal-size metric cards. The most urgent unresolved work appears first.

### Upload workspace

Use a three-step progress rail:

`Choose file -> Validate -> Review results`

Show accepted, rejected, and pending-review counts separately. Include a downloadable error report and a sample-template link.

### Review case

Use a split workspace on desktop:

- Left: case summary, severity, status, affected student or enrolment.
- Center: evidence comparison and validation findings.
- Right: decision controls, notes, and activity timeline.

On mobile, stack these sections in the same order.

### Verification

Show verifier identity, purpose, requested fields, consent state, expiry, signature status, and revocation state. Do not display a full sensitive identity value by default.

### Audit log

Use a dense, filterable timeline with actor, action, target, timestamp, correlation ID, and event details. Make the event digest available in an expandable detail view.

## 7. Components

- Status badge with text, icon, and semantic color.
- Data table with visible column definitions and empty state.
- Filter bar with saved filter state.
- Upload dropzone with keyboard-accessible file picker.
- Validation summary with counts and severity grouping.
- Review timeline.
- Consent field selector.
- QR verification result panel.
- Certificate preview with print-safe layout.
- Toasts only for transient success or failure; persistent errors stay inline.

## 8. Interaction Rules

- Primary buttons use the primary teal fill with high-contrast text.
- Secondary actions use an outlined or quiet button style.
- Destructive actions require a confirmation dialog with the affected record and reason.
- Loading states use skeleton rows or progress bars that match the final layout.
- Empty states explain how to populate the page.
- Error messages state what happened, which field is affected, and how to fix it.
- Focus rings must be visible against both canvas and surface colors.
- No important action depends on hover, drag-only input, color, or animation.
- Motion is restrained to state transition and feedback; respect `prefers-reduced-motion`.

## 9. Accessibility Requirements

- WCAG 2.2 AA target.
- Full keyboard navigation.
- Visible focus state.
- Proper label and error association for every form control.
- Table headers and row relationships exposed to assistive technology.
- Status text available to screen readers.
- Contrast ratio at least 4.5:1 for normal text.
- No auto-refresh that steals focus.
- Announce upload progress and validation completion.
- Provide text alternative for charts and expose the underlying data table.

## 10. Responsive Breakpoints

- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

Multi-column layouts collapse to one column below 768px. Data-heavy tables use intentional horizontal scrolling or a mobile record layout rather than shrinking text until it becomes unreadable.

## 11. Design Quality Gate

Before a screen is considered complete:

- Verify loading, empty, error, success, and permission-denied states.
- Test keyboard navigation and screen-reader labels.
- Test at 360px, 768px, 1280px, and 1440px widths.
- Test with long institution names, long student names, and long validation messages.
- Check light-theme contrast and print layout for the certificate.
- Confirm that statuses remain understandable without color.
