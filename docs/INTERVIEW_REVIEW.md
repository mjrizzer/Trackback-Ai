# Interviewer review: findings and fixes

The review focuses on reproducibility, evidence accuracy, security boundaries and failure handling. Passing tests establishes covered behavior; no software project can honestly guarantee that no interviewer will discover another defect.

| Finding | Impact | Implemented correction |
| --- | --- | --- |
| New organizations could not enter their manufacturing chain | Registration led to an empty workspace with no way to trace own data | Validated supplier/lot/batch/customer/shipment/inspection APIs and UI forms; integration test from a blank organization |
| Expiring browser tokens were accessible to JavaScript | XSS could read a stored session token | HttpOnly cookie sessions; Secure in production; no token stored in browser storage |
| Logout only cleared the browser | Previously copied tokens stayed valid | Server-side account token-version revocation on logout, password changes and role changes |
| No authentication throttling | Repeated password attempts were unrestricted | Bounded per-IP limiter, Retry-After response, generic auth errors and failed-login audit entries |
| Cookie-authenticated mutations needed CSRF protection | Cross-origin requests could threaten sensitive actions | Explicit CSRF header and configured Origin allowlist, plus SameSite cookies |
| Whitespace-only fields and zero IDs passed superficial checks | Empty incidents or invalid relationships could reach the database | Trim-before-validation schemas, positive IDs, finite positive quantities and forbidden extra fields |
| Missing incident URLs stayed loading | Broken links never explained the problem | Direct incident detail endpoint and a visible 404 with a return link |
| Completed records and model sources could drift | A tool could cite an existing record it never actually saw | Per-attempt trace/evidence snapshot; live citations checked against observed tool/prior validated references |
| Failed investigations could not be retried | A temporary provider failure required another incident | Atomically claimed retries, attempt counters and preserved previous events/tool calls |
| Source identifier matching used substrings | PB-001 could match unrelated PB-0010 | Exact identifier boundary matching with regression coverage |
| Uploads could be silently truncated or leave orphan files | Incomplete evidence could appear complete; failed transactions left storage residue | Explicit text limits, unique CSV headers, pre-parser request bounds, rollback cleanup and threadpool ingestion |
| Revision audit could exceed database string limits | Long justifications could fail on PostgreSQL or lose their previous state | Structured revision history stores previous/revised text; audit points to the revision; PDF includes it |
| Release approvals needed stronger intent and overlap checks | A release could conflict with a pending hold | Explicit source-verification attestation and overlapping pending-hold rejection |
| Newly entered records could oversubscribe inventory | More units could be consumed/shipped than available | Transactional material reservation, stable row-lock ordering, serialized shipment quantity checks and held-batch rejection |
| Supabase browser roles could otherwise reach public-schema tables | Database credentials/authentication assumptions were unclear | Migration enables RLS and revokes browser-role grants only on application tables |
| Project ran only as two development servers | A built frontend had no API-serving deployment path | Single-origin React/API serving, deep-link fallback, readiness check, non-root Docker image, persistent-volume Compose recipe |
| No continuous regression checks | Future edits could break working demonstrations | GitHub Actions jobs for SQLite, PostgreSQL, frontend/component/browser checks and container build |

## Questions to be ready to answer

- **Why use agents when SQL already traces batches?** SQL establishes relationships and quantities. Agents interpret incidents, retrieve evidence, compare claims, explain uncertainty and draft responses. They cannot invent relationships or bypass approvals.
- **Is Demo Mode live AI?** No. It is a labeled, prescribed workflow over real database records. The live path uses bounded model-selected tools when credentials are configured.
- **Does a cited source prove the conclusion?** No. The system checks that sources were retrieved and retains their originals; a reviewer must still assess whether a narrative follows from them.
- **Does approval send a recall?** No. Holds/releases only affect simulated internal status. Notifications and assignments remain internal approved drafts.
- **What happens on failure?** The investigation stops safely, retains its events and failed stage status, and can be retried without deleting history.
- **Why Supabase rather than Firebase?** The normalized material/batch/shipment graph, quantity checks and transactions suit PostgreSQL. FastAPI keeps AI secrets, tools and operational permissions server-side.
- **What remains before an industrial pilot?** Durable queue/resume, shared rate limiting, malware/OCR extraction isolation, MFA/account recovery, external ERP integration, formal approval policies and load/security testing. Release verification is an explicit human attestation, not laboratory proof generated by the application.

Cloud account configuration and real model accuracy cannot be verified without the relevant credentials. The QA record distinguishes locally run checks from CI definitions and unexercised cloud integrations.
