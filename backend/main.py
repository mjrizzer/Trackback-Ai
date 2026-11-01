from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from backend.config import settings
from backend.database import SessionLocal
from backend.models import Investigation, AgentRun, InvestigationEvent, now
from backend.api.routes import router
from backend.api.manufacturing import router as manufacturing_router
from backend.services.safety import SafetyMiddleware


@asynccontextmanager
async def lifespan(app):
    # A restarted local worker cannot silently leave an investigation running forever.
    with SessionLocal() as db:
        for inv in db.scalars(
            select(Investigation).where(Investigation.status.in_(['queued', 'running']))
        ):
            inv.status = 'failed'
            db.add(
                InvestigationEvent(
                    org_id=inv.org_id,
                    investigation_id=inv.id,
                    message='Worker restarted; investigation interrupted safely. Use Retry investigation to resume with a fresh attempt.',
                )
            )
        for run in db.scalars(select(AgentRun).where(AgentRun.status == 'running')):
            run.status, run.finished_at = 'failed', now()
        db.commit()
    yield


app = FastAPI(title='TraceBack AI', version='1.1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(','),
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH'],
    allow_headers=['Authorization', 'Content-Type', 'X-CSRF-Protection'],
)
app.add_middleware(SafetyMiddleware)
app.include_router(router)
app.include_router(manufacturing_router)


@app.exception_handler(IntegrityError)
async def integrity_error(_request, _error):
    return JSONResponse(
        {
            'detail': 'This change conflicts with an existing record or relationship. Refresh and try again.'
        },
        status_code=409,
    )


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/health/ready')
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text('SELECT id FROM organizations LIMIT 1'))
        return {'status': 'ready'}
    except Exception:
        return JSONResponse({'status': 'unavailable'}, status_code=503)


if settings.serve_frontend and (settings.frontend_dist / 'index.html').is_file():
    app.mount('/assets', StaticFiles(directory=settings.frontend_dist / 'assets'), name='assets')

    @app.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        if path == 'api' or path.startswith(('api/', 'health/')):
            return JSONResponse({'detail': 'Not found'}, status_code=404)
        return FileResponse(
            settings.frontend_dist / 'index.html', headers={'Cache-Control': 'no-cache'}
        )
