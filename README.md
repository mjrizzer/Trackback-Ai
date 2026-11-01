# TraceBack AI

Autonomous Industrial Incident Investigation Platform. A working local full-stack MVP for fictional **NovaFoods Manufacturing**: incidents → persisted five-agent workflow → verified SQL supply chain trace → evidence gaps and contradictions → human approvals → downloadable PDF.

**Reviewed and hardened edition:** [interviewer findings and fixes](docs/INTERVIEW_REVIEW.md), [deployment and Supabase setup](docs/DEPLOYMENT.md), [verification record](docs/QA.md). The application now supports entering your own manufacturing chain, protected cookie sessions, account session revocation, login throttling, safer uploads, release verification, investigation retries, and full proposal revision history.

## Windows 11 quick start

For a one-command local launch that installs locked dependencies, builds React, creates a local session secret, migrates the database and serves the complete web application:

```powershell
cd C:\Users\HP\traceback-ai
powershell -ExecutionPolicy Bypass -File .\start.ps1 -SeedDemo
```

Open **http://127.0.0.1:8000**. `-SeedDemo` explicitly enables fictional demo seeding; omit it for a new empty organization. The manual two-server development workflow follows.

Prerequisites: Python 3.11+ (tested with 3.14.3), Node.js 22+ (tested with 24.20.0), PowerShell and optionally Docker Desktop. No paid database or API key is needed for Demo Mode.

Run from PowerShell in the project root:

```powershell
cd C:\Users\HP\traceback-ai
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.seed
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open a second terminal:

```powershell
cd C:\Users\HP\traceback-ai\frontend
npm.cmd ci
npm.cmd run dev
```

Visit **http://127.0.0.1:5173**. API documentation: **http://127.0.0.1:8000/docs**. Health endpoint: **http://127.0.0.1:8000/health**. Using `npm.cmd` avoids PowerShell's disabled-script error; virtual-environment activation is unnecessary with the explicit Python path.

The seed command is idempotent and does not overwrite an existing NovaFoods organization. Registration creates a separate empty organization, not an invitation into NovaFoods. Migrations must run before API startup. Run SQLite from the project root so a relative `DATABASE_URL` resolves consistently.

### Demo accounts

| Email | Password | Permission |
| --- | --- | --- |
| `admin@novafoods.demo` | `NovaFoods!2026` | Users, investigations and approvals |
| `reviewer@novafoods.demo` | `NovaFoods!2026` | Investigations and approvals |
| `analyst@novafoods.demo` | `NovaFoods!2026` | Investigation and proposal drafting; cannot approve |

These credentials belong only to the fictional local demonstration. Passwords are stored with Argon2 hashing. Administrators can create workspace members and change another member's role in Settings.

## Demonstrate both scenarios

### A: contaminated ingredient lot

1. Open **Incidents**, then the supplier alert about **RM-042**.
2. Inspect its graph; select RM-042 and choose **Highlight downstream impact**. Source references identify the actual relational rows. Export the graph as JSON.
3. Click **Start investigation**. The workspace polls persisted events and agent statuses; a fast local Demo Mode run may finish before the next refresh.
4. Inspect the five agent outputs, evidence references, risk and missing-record findings.
5. The SQL trace must identify **PB-001, PB-002, PB-003, PB-004** and shipments **SHP-0001…0004 and SHP-0061…0064**, with **4 unique customers** and **4,800 potentially exposed shipped units**. Unrelated shipments are excluded.
6. **PB-003** intentionally lacks an inspection. Contamination is not confirmed by the dataset.
7. In **Approval center**, supply reviewer justification and approve the precautionary hold. Only those batches change to `held_simulated`. An analyst gets a server-side 403 if they attempt the same action.
8. Download the PDF from the workspace or Reports. Review the approval and report-download entries in Audit history.

### B: conflicting quality records

1. Open the **PB-012** conflicting-record incident and start its investigation.
2. Two microbiology records disagree: a CSV says **pass**, and an external PDF certificate says **fail**, two hours later. Both actual documents and inspection IDs are cited.
3. In Evidence & documents, search **PB-012** and inspect or download the originals.
4. The system flags the contradiction as unresolved. A later timestamp is not treated as proof that one certificate is correct.
5. Reject the proposed action or **Request revision** with a comment. A revised justification can be resubmitted; the previous review remains in the approval table and audit log.

Each completed investigation retains a findings snapshot. Reopening it displays the same findings. Failed runs without finalized findings can be retried using **Retry investigation**; prior attempts, tool calls and events remain in history. For new evidence after completion, or a fresh live run, create a follow-up incident with the same lot/batch and upload its evidence **before** starting. This prevents later evidence from silently rewriting existing findings.

### New incidents and uploads

**Report incident** accepts category, severity, description, and optional validated material/batch IDs. Its detail page supports incident-linked PDF/CSV uploads. Uploading a CSV does not silently modify validated manufacturing records. Its claims can generate missing-value, unknown-identifier, and contradictory-result findings. CSV inspection fields are `batch_code,test,result,timestamp`; lot evidence can use `lot_code`. PDFs must have extractable text; scans require external OCR.

The action draft form supports inventory holds, inventory releases, supplier escalation, customer notification drafts, and corrective assignments. The investigation supplies the target batch IDs and evidence; users cannot select targets outside that verified trace. All start pending. Approved holds/releases update simulated batch statuses only. Other approved actions remain internal approved drafts; no external API or email transport exists.

Inventory releases additionally require explicit reviewer attestation that original evidence and outstanding gaps were reviewed. Pending overlapping hold proposals block a release. The attestation is a human assertion, not automatic proof that a defect has been resolved. Revision history preserves the old and new justification in the application and PDF.

### Enter your own manufacturing data

Use **Add record** in Suppliers → Material lots → Production batches, then Customers → Shipments. Batch creation reserves material quantity and persists the lot-to-batch relationship. Shipments check remaining finished units and block held batches. Quality inspections require reviewer permission and a source document identifying the batch and recorded pass/fail result. Existing validated trace edges are retained; the app does not expose destructive delete operations. The UI supports a single material/batch line per entry; the REST API accepts multiple lines.

## Architecture

```text
frontend/                 React + TypeScript + Vite + Tailwind
  src/main.tsx            Application shell and routing
  src/pages/              Authentication, dashboard and functional module pages
  src/components/         shadcn-style Button, trace graph, action/user forms
  e2e/                    Desktop/mobile Playwright tests
backend/
  api/routes.py           JWT-protected REST endpoints
  agents/orchestrator.py  Five persisted stages; live Responses tool loop
  tools/investigation.py  Server-bound investigation tools; pending drafts only
  services/               SQL trace, evidence analysis, ingestion, reports, tenant checks
  models/                 20 normalized SQLAlchemy tables
  schemas/                Validated inputs and structured agent output
  migrations/             Frozen initial schema and safety/inventory revisions
  tests/                  Unit, API, integration and mocked-provider tests
  seed.py                 Idempotent fictional dataset and source documents
demo_data/                Sample supplier CSV and conflicting PDF
docs/                     Architecture, security and QA notes
docker-compose.yml        Optional local PostgreSQL
.env.example              Backend-only runtime configuration
```

React Router supplies every navigation destination, TanStack Query fetches and refreshes API data, Recharts displays database-derived metrics, and Lucide supplies icons. The accessible button primitive follows shadcn's Radix Slot/CVA composition. The responsive UI supports light/dark themes, searchable record tables, source details, a selectable supply chain graph, JSON graph export, document extraction previews, approval decisions, members, and audit history.

SQLAlchemy joins `batch_material_usage` and `shipment_items`; neither the model nor the frontend creates trace links. The orchestrator runs Incident Triage → Evidence Intelligence → Supply Chain Traceability → Risk and Impact → Response Planning and passes structured outputs forward. Agent runs, tool arguments/results, timeline events, findings, proposals, approval decisions and audits persist in the database. Tool context binds organization and incident on the server. Models cannot issue SQL or approve actions.

## Live AI configuration

Edit the backend `.env`:

```dotenv
AI_MODE=live
AI_PROVIDER=openai
AI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-key-here
JWT_SECRET=use-a-long-random-secret-of-at-least-32-characters
```

Restart the backend, then create a **new incident**. All five stages use the configured model, select controlled function tools through the OpenAI **Responses API**, and return Pydantic-validated outputs. Existing Demo Mode snapshots remain labeled demo. Without a key, keep `AI_MODE=demo`; an explicitly requested live run without credentials is rejected rather than silently simulated.

The optional `AI_BASE_URL` supports a provider implementing the same Responses API and strict function schema behavior; `AI_PROVIDER` is a descriptive label, not a provider-specific adapter. Unsupported APIs need a separate adapter. The implementation uses the OpenAI Python SDK directly rather than the Agents SDK to keep orchestration, persistence and tool authorization explicit. See [official function calling documentation](https://developers.openai.com/api/docs/guides/function-calling).

Each stage requires tool use, has at most 6 response turns and 12 tool calls, a 120-second soft deadline checked between requests, a 35-second request timeout, and one SDK retry for safe provider requests. Final references must have been observed through controlled tools or validated prior stage outputs. Documents are bounded excerpts, marked when truncated. Provider or validation failures stop the investigation with a persisted failure event; they do not generate simulated live output. The server drafts the final containment proposal deterministically; no model tool can execute inventory changes.

Keys never go to the frontend. Do not put them in `VITE_` variables or commit `.env`. With no JWT secret, a random per-process development secret invalidates sessions when the server restarts; configure one for stable sessions.

## Optional PostgreSQL / Supabase

```powershell
docker compose up -d postgres
```

Set `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://traceback:local-development-only@localhost:5432/traceback
```

For Supabase, use its PostgreSQL connection URI with `postgresql+psycopg://` and `?sslmode=require`; URL-encode password special characters. Then run the same Alembic migration and seed commands. The REST API still enforces JWT authorization; this app does not use the Supabase browser SDK or expose database credentials. PostgreSQL migrations and the backend suite have passed in GitHub Actions; a hosted Supabase project has not been connected.

## Verification

```powershell
cd C:\Users\HP\traceback-ai
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic current
cd frontend
npm.cmd run build
npm.cmd test
npm.cmd audit
```

Backend tests use a separate temporary SQLite database and temporary upload/sample directories. `backend/requirements.lock.txt` records the exact Python versions used for validation and can be installed instead of the ranged requirements for reproducibility. The browser tests use the running demonstration server and **modify its fictional data** (approve a simulated hold and create a QA incident). With both servers running:

```powershell
npm.cmd exec -- playwright test
```

The browser configuration uses installed Microsoft Edge in headless mode. On other platforms change/remove `channel: 'msedge'` and install Playwright Chromium with `npm.cmd exec -- playwright install chromium`. Screenshots are written to `docs/dashboard-desktop.png` and `docs/dashboard-mobile.png`. See [QA notes](docs/QA.md) for results and verification limits.

## Scope and limitations

This is a functional demonstration and pilot foundation, not an industrial production authorization system. It has no ERP integration, outbound messaging, legally authorized recall execution, malware scanning, OCR, SSO/MFA, email-based password recovery or durable distributed queue. Browser sessions use HttpOnly, SameSite cookies; production also enables Secure cookies and requires a strong persistent secret and HTTPS. Password changes, role changes and logout revoke existing account sessions. Local authentication throttling is per process; multi-replica hosting needs a shared limiter. CORS/Origin validation is restricted to configured origins. PostgreSQL migrations enable RLS and deny Supabase browser roles access to backend-owned tables; the backend uses a private database connection, not Supabase browser authentication.

The background worker is designed for a **single API process**. Interrupted runs are marked failed on restart and can be retried; no durable mid-stage resume is claimed. Provider retries cover safe reads, not arbitrary operational writes. Prompt-injection defenses bind context, restrict tools, treat sources as untrusted, verify observed references, and require approval; model narrative accuracy still needs human review. Arbitrary PDF prose is extracted and available to the live model but only structured inspection records and recognized CSV fields receive deterministic contradiction analysis.

The initial Alembic revision is a frozen schema snapshot; future schema changes require explicit new revision scripts. Cross-tenant ORM writes are checked server-side; direct database administration bypasses those checks. Back up the database and `backend/uploads/` together. Do not expose this development server publicly without the hardening and operational work listed in [architecture notes](docs/ARCHITECTURE.md).
