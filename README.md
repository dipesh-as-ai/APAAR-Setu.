# APAAR Setu

APAAR Setu is an SIH prototype for APAAR-based student data submission, validation, review, monitoring, and consent-based verification.

## Repository Layout

```text
apps/web                 React + Vite frontend
services/api             FastAPI backend and SQLite development store
services/worker          Worker boundary for future background jobs
packages                 Shared contracts and fixture helpers
infra/seed               Synthetic demo data
docs                     Product, design, architecture, API, and implementation plans
problem                  Original problem statement
```

## Local Requirements

- Node.js 20 or later
- Python 3.12 or later
- Docker is optional for the local fallback

## Start the Prototype

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r services\api\requirements.txt
python services\api\app.py --seed --reset
```

The API runs at `http://127.0.0.1:8000`.

### Frontend

```powershell
cd apps\web
npm install
npm run dev
```

The web app runs at `http://127.0.0.1:5173`.

## Demo Accounts

All prototype accounts use the password `demo123`.

| Username | Role | Scope |
|---|---|---|
| `operator-a` | Institution operator | Institution A |
| `reviewer` | AICTE reviewer | All institutions |
| `student` | Student | Consent demo |
| `verifier` | Authorized verifier | Verification demo |
| `admin` | AICTE administrator | All institutions |

## Demo Flow

1. Sign in as `operator-a`.
2. Upload `infra/seed/demo_students.csv`.
3. Review row-level validation results.
4. Sign in as `reviewer` and resolve a review case.
5. Open the AICTE dashboard.
6. Sign in as `verifier`, request fields, then sign in as `student` and approve the request.
7. Issue and open the signed verification URL.

The prototype uses synthetic identity values and a mock APAAR adapter. It does not contact government services.
