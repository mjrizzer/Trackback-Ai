# Run as a complete web application

The production frontend and API can be served from **one URL**. No Vite development server or browser-side database credentials are needed in that configuration.

## Single-origin local demonstration

Run migrations and seeding from the README first, then build the frontend:

```powershell
cd C:\Users\HP\traceback-ai\frontend
npm.cmd ci
npm.cmd run build
cd ..
$env:SERVE_FRONTEND = 'true'
$env:CORS_ORIGINS = 'http://127.0.0.1:8000,http://localhost:8000'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Deep links such as `/incidents/1` work through the React route fallback. Unknown `/api/...` endpoints return JSON 404 rather than the frontend HTML. `/health` checks the process; `/health/ready` checks database schema availability.

## Docker Compose

Install Docker Desktop. Copy `.env.example` to `.env`. Generate a persistent JWT secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into `JWT_SECRET` in your local `.env`, then run:

```powershell
docker compose --profile app up --build
```

Open **http://localhost:8000**. The profile runs PostgreSQL and a non-root application container; schema migrations and optional fictional seeding run before startup. Database and uploads use named volumes. The Compose recipe uses development cookie settings because localhost is HTTP. The Docker image defaults to production, where Secure cookies require HTTPS.

`docker compose up -d postgres` remains available without the application profile. Do not use the local-development PostgreSQL password on an Internet-facing database.

## Supabase PostgreSQL

Supabase is supported through its PostgreSQL connection, preserving relational joins and transaction safety. Firebase is not used because supply-chain relationships and quantity constraints fit PostgreSQL directly.

1. Create/select your Supabase project and obtain a **database connection URI** from its Connect panel. This is different from the public API URL/key. Prefer a direct or session-pooler connection for this long-running backend and migrations. The session pooler supports IPv4 where direct connectivity is unavailable.
2. Set `DATABASE_URL` for a direct Python deployment, or `DEPLOY_DATABASE_URL` for Docker Compose:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres.PROJECT:URL_ENCODED_PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

3. Run `python -m alembic upgrade head` using the virtual environment. Optionally seed fictional data with `python -m backend.seed`.
4. Keep all database credentials on the backend. Do not place a service-role key, database password, or connection URI in a `VITE_` variable.

Migrations enable row-level security on this application's tables and revoke Supabase `anon`/`authenticated` access where those roles exist. There are no permissive browser policies: all requests go through FastAPI authorization. Existing unrelated project tables are not altered. The backend connection must be an owner/migration role capable of these operations; it remains private. Application queries and foreign-key write guards enforce organization scope. RLS here denies direct browser access; it does **not** claim to provide per-organization policies for the private backend role.

See [Supabase connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres) and [RLS documentation](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Hosting the Docker image

Build with `docker build -t traceback-ai .`. Deploy to a container host with HTTPS and a persistent disk mounted at `/data`; configure:

```dotenv
ENVIRONMENT=production
JWT_SECRET=a-random-persistent-secret-of-at-least-32-characters
DATABASE_URL=postgresql+psycopg://...supabase...?sslmode=require
CORS_ORIGINS=https://your-application.example
SERVE_FRONTEND=true
AI_MODE=demo
SEED_DEMO=false
```

Set `SEED_DEMO=true` only when intentionally creating the public fictional demo accounts. In normal hosting, register a new organization and enter its data. For live AI additionally configure `OPENAI_API_KEY` and `AI_MODEL` on the host. Keep one application worker; a durable job queue is required before adding replicas.

**Persistence matters:** Supabase stores database records, while source evidence files are on `/data/uploads`. Back up both. An ephemeral hosting filesystem will lose originals on restart; use a persistent volume before sharing a hosted instance. Cloud deployment has not been performed without an authorized Supabase project and hosting account; no invented live URL is provided.

## GitHub automation

`.github/workflows/ci.yml` runs the backend against SQLite and PostgreSQL, checks production frontend builds and component tests, executes Chromium browser regressions against the actual built web application, and builds the Docker image. Browser failures upload traces. These cloud checks complement locally executed tests; check their actual GitHub status before claiming a deployment or container build passed.
