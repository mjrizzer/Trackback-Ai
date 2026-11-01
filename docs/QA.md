# Validation record

Environment: Windows, Python 3.14.3, Node.js 24.20.0, SQLite fallback. Backend tests use an isolated temporary database; browser tests run against fictional local demo data.

**GitHub verification:** [workflow run 41288704336](https://github.com/mjrizzer/Trackback-Ai/actions/runs/41288704336) completed successfully for application commit `d398d19f57a9693d14aaa07251766c80fe4f53d7`. All four jobs passed: SQLite backend, PostgreSQL backend, production web/browser checks, and Docker image build. Linux CI uses Python 3.12 and Node.js 22; local browser checks use Microsoft Edge, while CI uses Chromium.

## Automated checks

- Backend: **30 passing Pytest tests** covering the original investigation workflows plus blank-input rejection, exact identifier matching, secure cookie/CSRF behavior, logout/password revocation, throttling, security headers, request bounds, orphan-upload cleanup, failed-run retries, unobserved AI citation rejection, release attestation, and a new organization's complete manufacturing entry/trace workflow. Material reservation, held-batch shipment rejection, overship protection and transaction rollback are exercised.
- Frontend: 2 component tests for meaningful empty states and graph source inspection.
- TypeScript and Vite production build pass. Framework/chart chunks are separated to avoid a large single bundle.
- Dependency checks: `pip check` passes; npm audit reports zero known vulnerabilities after upgrading test tooling.
- Alembic migrations applied; current revision `0003`. Fresh upgrade/downgrade and metadata drift checks pass.
- Ruff static checks and Python formatting are included in local validation and CI. Frontend pages are split into separate modules and TypeScript imports are organized.

Browser: **4 passing Playwright tests**, exercised both through the Vite development server and against the built single-origin application on port 8000, in installed Microsoft Edge headless. Coverage includes both incident scenarios, graph inspection, report download, document preview, mobile navigation/creation/theme, all navigation modules, missing-record errors, token absence from browser storage, and manufacturing entry. Screenshots are available as `dashboard-desktop.png` and `dashboard-mobile.png`. The mobile test asserts no page-level horizontal overflow at 390 × 844.

## Limits

No real API key was configured. Live Responses integration uses a mocked provider in tests. PostgreSQL and the Docker image were successfully verified in GitHub Actions; Docker is not installed in the local Windows environment, so local container execution is not claimed. Supabase cloud requires a connected project and private database configuration. Load testing, external recall systems and real industrial data are not exercised. A Starlette deprecation warning concerning its HTTPX test transport is non-failing. Demo Mode remains explicitly labeled.
