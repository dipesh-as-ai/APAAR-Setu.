import { FormEvent, ReactNode, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  FileCheck2,
  FileSpreadsheet,
  Fingerprint,
  History,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Menu,
  QrCode,
  ShieldCheck,
  Upload,
  Users,
  X,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

type User = {
  username: string;
  display_name: string;
  role: string;
  institution_id: string | null;
};

type Dashboard = {
  scope: string;
  enrolments: Record<string, number>;
  cases: Record<string, number>;
  active_enrolments?: number;
  approved_intake?: { regular_intake: number; supernumerary_limit: number } | null;
};

type Case = {
  id: string;
  case_type: string;
  severity: string;
  status: string;
  title: string;
  institution_id: string;
  decision?: string;
  reason?: string;
  evidence: { row_number?: number; apaar?: string | null; errors?: Array<{ message: string }> };
};

type Request = {
  id: string;
  enrolment_id: string;
  verifier_username: string;
  purpose: string;
  requested_fields_json: string;
  status: string;
  requested_fields?: string[];
};

async function api<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.error?.message || "The request could not be completed.");
  return body as T;
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusClass(value: string) {
  if (["verified", "accepted", "resolved", "approved", "valid"].includes(value)) return "status status-success";
  if (["rejected", "failed", "revoked"].includes(value)) return "status status-danger";
  if (["pending_review", "pending_consent", "validating"].includes(value)) return "status status-warning";
  return "status status-neutral";
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("apaar_token") || "");
  const [user, setUser] = useState<User | null>(null);
  const [view, setView] = useState("dashboard");
  const [menuOpen, setMenuOpen] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    api<User>("/api/v1/auth/me", {}, token).then(setUser).catch(() => {
      localStorage.removeItem("apaar_token");
      setToken("");
    });
  }, [token]);

  function signOut() {
    localStorage.removeItem("apaar_token");
    setToken("");
    setUser(null);
  }

  if (!token || !user) return <Login onLogin={(nextToken, nextUser) => { localStorage.setItem("apaar_token", nextToken); setToken(nextToken); setUser(nextUser); }} />;

  const canReview = ["aicte_admin", "aicte_reviewer", "auditor", "institution_operator"].includes(user.role);
  const isAicte = ["aicte_admin", "aicte_reviewer", "auditor"].includes(user.role);
  const nav = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    ...(user.role.startsWith("institution") ? [{ id: "upload", label: "Submit data", icon: Upload }] : []),
    ...(canReview ? [{ id: "review", label: "Review queue", icon: ClipboardCheck }] : []),
    ...(user.role === "verifier" ? [{ id: "verify", label: "Verify records", icon: ShieldCheck }] : []),
    ...(user.role === "student" ? [{ id: "consent", label: "Consent requests", icon: LockKeyhole }] : []),
    ...(canReview ? [{ id: "audit", label: "Audit trail", icon: History }] : []),
  ];

  return (
    <div className="app-shell">
      <aside className={menuOpen ? "sidebar sidebar-open" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark"><Fingerprint size={19} /></div>
          <div><strong>APAAR Setu</strong><span>Trust registry</span></div>
          <button className="icon-button close-menu" onClick={() => setMenuOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="scope-label">Workspace</div>
        <nav>
          {nav.map((item) => {
            const Icon = item.icon;
            return <button key={item.id} className={view === item.id ? "nav-item active" : "nav-item"} onClick={() => { setView(item.id); setMenuOpen(false); }}><Icon size={17} /><span>{item.label}</span></button>;
          })}
        </nav>
        <div className="sidebar-footer"><div className="secure-note"><ShieldCheck size={16} /><span>Prototype environment<br /><b>Synthetic data only</b></span></div></div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setMenuOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="breadcrumb">AICTE / <strong>{view === "dashboard" ? "Overview" : formatLabel(view)}</strong></div>
          <div className="topbar-actions"><div className="user-chip"><div className="avatar">{user.display_name[0]}</div><div><b>{user.display_name}</b><span>{formatLabel(user.role)}</span></div></div><button className="icon-button" onClick={signOut} aria-label="Sign out"><LogOut size={17} /></button></div>
        </header>
        {error && <div className="global-error"><AlertCircle size={17} />{error}<button onClick={() => setError("")} aria-label="Dismiss error"><X size={15} /></button></div>}
        <div className="content-wrap">
          {view === "dashboard" && <DashboardView token={token} isAicte={isAicte} user={user} onError={setError} />}
          {view === "upload" && <UploadView token={token} user={user} onError={setError} />}
          {view === "review" && <ReviewView token={token} onError={setError} />}
          {view === "verify" && <VerifierView token={token} onError={setError} />}
          {view === "consent" && <ConsentView token={token} onError={setError} />}
          {view === "audit" && <AuditView token={token} onError={setError} />}
        </div>
      </main>
    </div>
  );
}

function Login({ onLogin }: { onLogin: (token: string, user: User) => void }) {
  const [username, setUsername] = useState("operator-a");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError("");
    try { const result = await api<{ access_token: string; user: User }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }); onLogin(result.access_token, result.user); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Sign in failed"); }
    finally { setLoading(false); }
  }
  return <div className="login-page"><div className="login-aside"><div className="brand brand-light"><div className="brand-mark"><Fingerprint size={19} /></div><div><strong>APAAR Setu</strong><span>Trust registry</span></div></div><div className="login-message"><p className="eyebrow">AICTE student data exchange</p><h1>Make every enrolment accountable.</h1><p>One secure workspace for submission, validation, review, and authorized verification.</p></div><div className="login-aside-footer">SIH prototype · synthetic data environment</div></div><div className="login-panel"><form onSubmit={submit} className="login-form"><div><p className="eyebrow">Welcome back</p><h2>Sign in to the registry</h2><p className="muted">Use a seeded prototype account to explore a role-specific workspace.</p></div><label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" /></label>{error && <div className="form-error"><AlertCircle size={16} />{error}</div>}<button className="primary-button" disabled={loading}>{loading ? "Signing in..." : "Sign in"}<ArrowUpRight size={17} /></button><div className="demo-accounts"><span>Demo accounts</span><button type="button" onClick={() => setUsername("operator-a")}>Institution</button><button type="button" onClick={() => setUsername("reviewer")}>AICTE reviewer</button><button type="button" onClick={() => setUsername("verifier")}>Verifier</button><button type="button" onClick={() => setUsername("student")}>Student</button></div></form></div></div>;
}

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{action}</div>;
}

function Stat({ label, value, detail, icon: Icon, tone = "default" }: { label: string; value: string | number; detail: string; icon: typeof Users; tone?: string }) {
  return <div className={`stat-card tone-${tone}`}><div className="stat-top"><span>{label}</span><Icon size={18} /></div><strong>{value}</strong><small>{detail}</small></div>;
}

function DashboardView({ token, isAicte, user, onError }: { token: string; isAicte: boolean; user: User; onError: (message: string) => void }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const hasInstitutionScope = Boolean(user.institution_id);
  useEffect(() => { if (!isAicte && !hasInstitutionScope) { setLoading(false); return; } setLoading(true); api<Dashboard>(isAicte ? "/api/v1/dashboards/aicte" : "/api/v1/dashboards/institution", {}, token).then(setData).catch((error) => onError(error.message)).finally(() => setLoading(false)); }, [token, isAicte, hasInstitutionScope, onError]);
  if (!isAicte && !hasInstitutionScope) return <RoleLanding user={user} />;
  const counts = data?.enrolments || {};
  const cases = data?.cases || {};
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  return <><PageHeader eyebrow={isAicte ? "AICTE monitoring" : "Institution workspace"} title={isAicte ? "National enrolment overview" : "Your enrolment workspace"} description={isAicte ? "Monitor verified coverage, unresolved cases, and intake pressure across the network." : "Submit student data, resolve validation issues, and keep your institutional record current."} action={isAicte ? <button className="quiet-button"><BarChart3 size={16} />Export report</button> : <span className="data-status"><span className="pulse-dot" />Live prototype data</span>} />
    {loading ? <div className="loading-panel">Loading operational data...</div> : <><div className="stat-grid"><Stat label="Total records" value={total} detail="Current workspace" icon={Users} /><Stat label="Verified" value={counts.verified || 0} detail="Ready for verification" icon={ShieldCheck} tone="success" /><Stat label="Pending review" value={counts.pending_review || 0} detail={`${cases.open || 0} open cases`} icon={ClipboardCheck} tone="warning" /><Stat label="Rejected" value={counts.rejected || 0} detail="Requires correction" icon={AlertCircle} tone="danger" /></div><div className="dashboard-grid"><section className="panel utilization"><div className="panel-heading"><div><h2>Intake utilization</h2><p>Active enrolment against the current approval snapshot.</p></div><span className="mini-label">2026-27</span></div><div className="utilization-number"><strong>{data?.active_enrolments || total}</strong><span>active records</span></div><div className="progress-track"><span style={{ width: `${Math.min(100, ((data?.active_enrolments || total) / (data?.approved_intake?.regular_intake || 100)) * 100)}%` }} /></div><div className="utilization-meta"><span>Approved regular intake <b>{data?.approved_intake?.regular_intake || "-"}</b></span><span>Supernumerary limit <b>{data?.approved_intake?.supernumerary_limit || "-"}</b></span></div></section><section className="panel status-breakdown"><div className="panel-heading"><div><h2>Record states</h2><p>Every row stays traceable through its lifecycle.</p></div></div>{Object.entries(counts).length ? Object.entries(counts).map(([label, count]) => <div className="breakdown-row" key={label}><span className={statusClass(label)}>{formatLabel(label)}</span><strong>{count}</strong><div className="breakdown-line"><span style={{ width: `${Math.max(8, (count / Math.max(1, total)) * 100)}%` }} /></div></div>) : <div className="empty-state">No records yet. Submit a file to populate this workspace.</div>}</section></div><section className="panel next-action"><div className="next-icon"><FileCheck2 size={22} /></div><div><p className="eyebrow">Next action</p><h2>{isAicte ? "Review the open queue" : "Submit the admission batch"}</h2><p>{isAicte ? "Resolve flagged identity and intake cases before considering records verified." : "Use the standard CSV template. Validation results will appear row by row."}</p></div><ArrowUpRight size={20} /></section></>}</>;
}

function RoleLanding({ user }: { user: User }) {
  const isStudent = user.role === "student";
  return <><PageHeader eyebrow={isStudent ? "Student workspace" : "Authorized verifier"} title={isStudent ? "Control your academic sharing" : "Verify with consent"} description={isStudent ? "Review and approve requests before selected academic fields are shared." : "Request limited student fields for a defined purpose, then issue a signed verification after consent."} /><div className="role-landing"><div className="role-landing-mark">{isStudent ? <LockKeyhole size={25} /> : <ShieldCheck size={25} />}</div><div><h2>{isStudent ? "Your data stays purpose-bound" : "Verification is purpose-bound"}</h2><p>{isStudent ? "Use Consent requests in the left navigation to review pending access requests." : "Use Verify records in the left navigation to select a record and create a consent request."}</p></div><ArrowUpRight size={20} /></div></>;
}

function UploadView({ token, user, onError }: { token: string; user: User; onError: (message: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submission, setSubmission] = useState<Record<string, any> | null>(null);
  const [errors, setErrors] = useState<any[]>([]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!file) return;
    setSubmitting(true); setSubmission(null); setErrors([]);
    try {
      const body = new FormData(); body.append("file", file);
      const result = await api<{ submission_id: string }>(`/api/v1/institutions/${user.institution_id}/submissions?academic_cycle=2026-27&programme_id=prog_a_cse&idempotency_key=${encodeURIComponent(`${file.name}-${file.size}`)}`, { method: "POST", body }, token);
      let status: Record<string, any> = result; for (let index = 0; index < 12 && status.status === "validating"; index += 1) { await new Promise((resolve) => setTimeout(resolve, 350)); status = await api(`/api/v1/submissions/${result.submission_id}`, {}, token); }
      setSubmission(status); const errorResult = await api<{ items: any[] }>(`/api/v1/submissions/${result.submission_id}/errors`, {}, token); setErrors(errorResult.items.filter((item) => item.errors.length));
    } catch (error) { onError(error instanceof Error ? error.message : "Upload failed"); } finally { setSubmitting(false); }
  }
  return <><PageHeader eyebrow="Institution submission" title="Submit a student batch" description="Upload the completed admission template. Every row is checked before it enters the accepted enrolment record." action={<a className="quiet-button" href="/demo_students.csv" download><FileSpreadsheet size={16} />Template</a>} /><div className="upload-layout"><form className="panel upload-panel" onSubmit={submit}><div className="upload-step"><span className="step-number active">1</span><div><h2>Choose a file</h2><p>CSV only · up to 5 MB · synthetic data for this prototype</p></div></div><label className="dropzone"><input type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] || null)} />{file ? <><FileSpreadsheet size={30} /><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB selected</span></> : <><Upload size={30} /><strong>Drop the admission CSV here</strong><span>or choose a file from your device</span></>}</label><div className="upload-step muted-step"><span className={file ? "step-number active" : "step-number"}>2</span><div><h2>Validate and review</h2><p>APAAR matching, duplicates, intake, and category rules run automatically.</p></div></div><button className="primary-button full-width" disabled={!file || submitting}>{submitting ? "Processing submission..." : "Submit for validation"}<ArrowUpRight size={17} /></button></form><div className="panel upload-guide"><div className="guide-icon"><ClipboardCheck size={21} /></div><h2>What happens next</h2><ol><li>Schema and field checks</li><li>Mock APAAR identity match</li><li>Duplicate and conflict scan</li><li>Approval intake comparison</li><li>Accepted, rejected, or review state</li></ol><div className="callout"><AlertCircle size={16} /><span>Excess admissions are retained as review cases. They are not silently removed.</span></div></div></div>{submission && <section className="panel result-panel"><div className="panel-heading"><div><p className="eyebrow">Submission result</p><h2>{submission.file_name}</h2></div><span className={statusClass(submission.status)}>{formatLabel(submission.status)}</span></div><div className="result-stats"><span><b>{submission.total_rows}</b>Total rows</span><span className="success-text"><b>{submission.accepted_rows}</b>Accepted</span><span className="warning-text"><b>{submission.pending_rows}</b>Pending review</span><span className="danger-text"><b>{submission.rejected_rows}</b>Rejected</span></div>{errors.length > 0 && <div className="error-table"><h3>Rows requiring correction</h3>{errors.map((row) => <div className="error-row" key={row.row_number}><b>Row {row.row_number}</b><span>{row.errors.map((item: any) => item.message).join(" ")}</span></div>)}</div>}</section>}</>;
}

function ReviewView({ token, onError }: { token: string; onError: (message: string) => void }) {
  const [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState<Case | null>(null);
  const [decision, setDecision] = useState("dismissed");
  const [reason, setReason] = useState("");
  async function load() { try { const result = await api<{ items: Case[] }>("/api/v1/review-cases", {}, token); setCases(result.items); } catch (error) { onError(error instanceof Error ? error.message : "Could not load review cases"); } }
  useEffect(() => { load(); }, [token]);
  async function resolve() { if (!selected || !reason) return; try { await api(`/api/v1/review-cases/${selected.id}`, { method: "PATCH", body: JSON.stringify({ decision, reason }) }, token); setSelected(null); setReason(""); await load(); } catch (error) { onError(error instanceof Error ? error.message : "Could not resolve case"); } }
  return <><PageHeader eyebrow="AICTE review queue" title="Resolve flagged records" description="Review evidence before a record becomes verified. Every decision is retained in the audit trail." /><div className="review-layout"><section className="panel case-list"><div className="panel-heading"><div><h2>Open and resolved cases</h2><p>{cases.filter((item) => item.status === "open").length} cases currently need attention</p></div></div>{cases.length ? cases.map((item) => <button className={selected?.id === item.id ? "case-row selected" : "case-row"} key={item.id} onClick={() => { setSelected(item); setDecision("dismissed"); setReason(""); }}><div className="case-icon"><AlertCircle size={17} /></div><div className="case-copy"><strong>{item.title}</strong><span>Row {item.evidence?.row_number || "-"} · {item.case_type}</span></div><span className={statusClass(item.status)}>{formatLabel(item.status)}</span></button>) : <div className="empty-state">No review cases found.</div>}</section><section className="panel case-detail">{selected ? <><div className="case-detail-header"><div><p className="eyebrow">{selected.case_type} case</p><h2>{selected.title}</h2></div><span className={statusClass(selected.severity === "high" ? "rejected" : "pending_review")}>{selected.severity} severity</span></div><div className="evidence-box"><div><span>Upload row</span><b>{selected.evidence?.row_number || "-"}</b></div><div><span>APAAR reference</span><b>{selected.evidence?.apaar || "Pending"}</b></div><div><span>Institution</span><b>{selected.institution_id}</b></div></div>{selected.evidence?.errors?.length ? <div className="finding"><AlertCircle size={17} /><div><b>Validation findings</b><p>{selected.evidence.errors.map((item) => item.message).join(" ")}</p></div></div> : null}{selected.status === "open" ? <div className="decision-form"><label>Decision<select value={decision} onChange={(event) => setDecision(event.target.value)}><option value="dismissed">Dismiss as valid case</option><option value="confirmed">Confirm issue</option><option value="corrected">Mark corrected</option><option value="escalated">Escalate</option></select></label><label>Decision reason<textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Explain the evidence behind this decision" /></label><button className="primary-button" onClick={resolve} disabled={!reason}>Save decision <ArrowUpRight size={17} /></button></div> : <div className="resolved-note"><CheckCircle2 size={18} /><span>Resolved as <b>{selected.decision}</b>. {selected.reason}</span></div>}</> : <div className="empty-detail"><ClipboardCheck size={30} /><h2>Select a case</h2><p>Choose a case from the queue to inspect its evidence and record a decision.</p></div>}</section></div></>;
}

function VerifierView({ token, onError }: { token: string; onError: (message: string) => void }) {
  const [enrolments, setEnrolments] = useState<any[]>([]);
  const [selected, setSelected] = useState("");
  const [issued, setIssued] = useState<any>(null);
  const [requestId, setRequestId] = useState("");
  useEffect(() => { api<{ items: any[] }>("/api/v1/enrolments", {}, token).then((result) => setEnrolments(result.items)).catch((error) => onError(error.message)); }, [token, onError]);
  async function createRequest() { try { const result = await api<{ request_id: string }>("/api/v1/verification-requests", { method: "POST", body: JSON.stringify({ enrolment_id: selected, purpose: "employment_screening", requested_fields: ["name", "institution", "programme", "status"], expires_at: new Date(Date.now() + 86400000).toISOString() }) }, token); setRequestId(result.request_id); } catch (error) { onError(error instanceof Error ? error.message : "Could not create request"); } }
  async function issue() { try { const result = await api(`/api/v1/verification-requests/${requestId}/issue`, { method: "POST" }, token); setIssued(result); } catch (error) { onError(error instanceof Error ? error.message : "Consent is required before issuance"); } }
  return <><PageHeader eyebrow="Authorized verification" title="Request a verified record" description="Select a student record and ask for only the fields required for your stated purpose." /><div className="verify-layout"><section className="panel verify-form"><div className="guide-icon"><ShieldCheck size={21} /></div><h2>New verification request</h2><label>Student record<select value={selected} onChange={(event) => setSelected(event.target.value)}><option value="">Choose a record</option>{enrolments.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.student_institution_id}</option>)}</select></label><label>Purpose<input value="Employment screening" readOnly /></label><div className="requested-fields"><span className="field-heading">Requested fields</span>{["Name", "Institution", "Programme", "Status"].map((field) => <span className="field-pill" key={field}><CheckCircle2 size={14} />{field}</span>)}</div><button className="primary-button full-width" disabled={!selected || !!requestId} onClick={createRequest}>{requestId ? "Awaiting student consent" : "Request consent"}<ArrowUpRight size={17} /></button>{requestId && <div className="callout success-callout"><LockKeyhole size={16} /><span>Request <b>{requestId}</b> created. Switch to the Student account to approve it.</span></div>}</section><section className="panel verify-result">{issued ? <><div className="verified-mark"><CheckCircle2 size={35} /></div><p className="eyebrow">Signed verification issued</p><h2>Record is ready to share</h2><p className="muted">The verifier can use this opaque URL. It contains no APAAR or personal data.</p><div className="qr-placeholder"><QrCode size={66} /><span>QR preview</span></div><div className="token-box">{issued.url}</div><div className="claim-list">{Object.entries(issued.claims).map(([key, value]) => <div key={key}><span>{formatLabel(key)}</span><b>{String(value)}</b></div>)}</div></> : <><div className="empty-detail"><QrCode size={30} /><h2>Verification appears here</h2><p>After the student approves your request, issue a signed, expiry-bound verification artifact.</p>{requestId && <button className="quiet-button" onClick={issue}>Check consent and issue</button>}</div></>}</section></div></>;
}

function ConsentView({ token, onError }: { token: string; onError: (message: string) => void }) {
  const [requests, setRequests] = useState<Request[]>([]);
  async function load() { try { const result = await api<{ items: Request[] }>("/api/v1/verification-requests", {}, token); setRequests(result.items); } catch (error) { onError(error instanceof Error ? error.message : "Could not load consent requests"); } }
  useEffect(() => { load(); }, [token]);
  async function decide(id: string, decision: string) { try { await api(`/api/v1/verification-requests/${id}/decision`, { method: "POST", body: JSON.stringify({ decision, reason: decision === "approved" ? "Approved by student in prototype" : "Declined by student" }) }, token); await load(); } catch (error) { onError(error instanceof Error ? error.message : "Could not save consent decision"); } }
  return <><PageHeader eyebrow="Student consent" title="Control what you share" description="Review each verifier request and approve only the fields needed for its stated purpose." /><section className="panel consent-list">{requests.length ? requests.map((request) => <div className="consent-row" key={request.id}><div className="consent-icon"><LockKeyhole size={18} /></div><div className="consent-copy"><strong>{request.purpose.replaceAll("_", " ")}</strong><span>Requested by {request.verifier_username} · {request.enrolment_id}</span><div className="consent-fields">{(request.requested_fields || JSON.parse(request.requested_fields_json || "[]") as string[]).map((field: string) => <span key={field}>{formatLabel(field)}</span>)}</div></div><div className="consent-actions">{request.status === "pending_consent" ? <><button className="quiet-button" onClick={() => decide(request.id, "rejected")}>Decline</button><button className="primary-button" onClick={() => decide(request.id, "approved")}>Approve <ArrowUpRight size={16} /></button></> : <span className={statusClass(request.status)}>{formatLabel(request.status)}</span>}</div></div>) : <div className="empty-state">No consent requests are waiting for you.</div>}</section></>;
}

function AuditView({ token, onError }: { token: string; onError: (message: string) => void }) {
  const [events, setEvents] = useState<any[]>([]);
  useEffect(() => { api<{ items: any[] }>("/api/v1/audit-events", {}, token).then((result) => setEvents(result.items)).catch((error) => onError(error.message)); }, [token, onError]);
  return <><PageHeader eyebrow="Accountability" title="Audit trail" description="A chronological record of submissions, decisions, consent, verification, and access." /><section className="panel audit-panel">{events.length ? events.map((event) => <div className="audit-row" key={event.id}><div className="audit-dot" /><div className="audit-main"><strong>{formatLabel(event.action)}</strong><span>{event.actor_username} · {event.target_type} {event.target_id}</span></div><time>{new Date(event.created_at).toLocaleString()}</time><code>{event.correlation_id}</code></div>) : <div className="empty-state">No audit activity yet.</div>}</section></>;
}
