from collections import Counter
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    BackgroundTasks,
    UploadFile,
    File,
    Form,
    Response as HTTPResponse,
)
from fastapi.responses import Response, FileResponse
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import settings
from backend.models import *
from backend.schemas import (
    Login,
    Register,
    IncidentInput,
    Decision,
    ProposalInput,
    UserInput,
    RoleInput,
    RevisionInput,
    PasswordInput,
)
from backend.security import (
    passwords,
    token,
    current_user,
    reviewer,
    set_session,
    clear_session,
    DUMMY_HASH,
)
from backend.services.records import rows, owned, dump, trace, audit
from backend.services.documents import store, UPLOADS, MAX_SIZE
from backend.services.reports import report
from backend.agents.orchestrator import investigate

router = APIRouter(prefix='/api')
CATALOG = {
    'suppliers': Supplier,
    'lots': MaterialLot,
    'batches': ProductionBatch,
    'customers': Customer,
    'shipments': Shipment,
    'incidents': Incident,
    'investigations': Investigation,
    'documents': EvidenceDocument,
    'findings': EvidenceFinding,
    'agents': AgentRun,
    'tool-calls': AgentToolCall,
    'events': InvestigationEvent,
    'proposals': ActionProposal,
    'approvals': Approval,
    'audit': AuditLog,
    'users': User,
    'inspections': Inspection,
}


@router.post('/auth/login')
def login(body: Login, response: HTTPResponse, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    valid = passwords.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        if user:
            audit(
                db,
                user.org_id,
                user.id,
                'login_failed',
                'Authentication rejected; no credentials recorded',
            )
            db.commit()
        raise HTTPException(401, 'Email or password is incorrect')
    audit(db, user.org_id, user.id, 'login', 'Authenticated session')
    db.commit()
    set_session(response, user)
    return {'access_token': token(user), 'user': dump(user)}


@router.post('/auth/register', status_code=201)
def register(body: Register, response: HTTPResponse, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    if '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(422, 'Valid email required')
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Email already registered')
    org = Organization(name=body.organization)
    db.add(org)
    db.flush()
    user = User(
        org_id=org.id,
        name=body.name,
        email=email,
        password_hash=passwords.hash(body.password),
        role='admin',
    )
    db.add(user)
    db.flush()
    audit(db, org.id, user.id, 'registration', 'Created isolated organization')
    db.commit()
    set_session(response, user)
    return {'access_token': token(user), 'user': dump(user)}


@router.post('/auth/logout')
def logout(
    response: HTTPResponse, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    audit(db, user.org_id, user.id, 'logout', 'Existing sessions for this account revoked')
    db.commit()
    clear_session(response)
    return {'message': 'Signed out; existing account sessions revoked'}


@router.post('/auth/password')
def change_password(
    body: PasswordInput,
    response: HTTPResponse,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not passwords.verify(body.current_password, user.password_hash):
        raise HTTPException(403, 'Current password is incorrect')
    if body.current_password == body.new_password:
        raise HTTPException(422, 'Choose a different password')
    user.password_hash = passwords.hash(body.new_password)
    db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    audit(db, user.org_id, user.id, 'password_changed', 'Existing sessions revoked')
    db.commit()
    clear_session(response)
    return {'message': 'Password changed. Sign in again.'}


@router.get('/me')
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        'user': dump(user),
        'organization': db.get(Organization, user.org_id).name,
        'mode': settings.ai_mode,
        'live_ready': bool(settings.openai_api_key),
        'model': settings.ai_model,
        'provider': settings.ai_provider,
    }


@router.get('/dashboard')
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    org = user.org_id
    incidents, investigations = rows(db, Incident, org), rows(db, Investigation, org)
    affected = {
        s['id'] for inv in investigations for s in inv.result.get('trace', {}).get('shipments', [])
    }
    return {
        'batches': len(rows(db, ProductionBatch, org)),
        'open_incidents': sum(i.status != 'closed' for i in incidents),
        'active_investigations': sum(i.status in ('queued', 'running') for i in investigations),
        'flagged_lots': len({i.lot_id for i in incidents if i.lot_id and i.status != 'closed'}),
        'affected_shipments': len(affected),
        'pending_approvals': sum(p.status == 'pending' for p in rows(db, ActionProposal, org)),
        'trends': [
            {'date': d, 'incidents': n}
            for d, n in sorted(Counter(i.created_at.date().isoformat() for i in incidents).items())
        ],
        'activity': [dump(e) for e in rows(db, InvestigationEvent, org)[-6:]][::-1],
    }


@router.get('/records/{kind}')
def catalog(kind: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if kind not in CATALOG:
        raise HTTPException(404, 'Unknown record collection')
    if kind == 'users' and user.role != 'admin':
        raise HTTPException(403, 'Admin permission required')
    result = [dump(r) for r in rows(db, CATALOG[kind], user.org_id)]
    if kind == 'documents':
        for r in result:
            r.pop('text', None)
    return result


@router.post('/incidents', status_code=201)
def create_incident(
    body: IncidentInput, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if body.lot_id:
        owned(db, MaterialLot, body.lot_id, user.org_id)
    if body.batch_id:
        owned(db, ProductionBatch, body.batch_id, user.org_id)
    incident = Incident(org_id=user.org_id, **body.model_dump())
    db.add(incident)
    db.flush()
    audit(db, user.org_id, user.id, 'incident_created', f'Incident {incident.id}: {incident.title}')
    db.commit()
    return dump(incident)


@router.post('/incidents/{identifier}/investigate', status_code=202)
def start(
    identifier: int,
    tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    incident = owned(db, Incident, identifier, user.org_id)
    previous = db.scalar(
        select(Investigation).where(
            Investigation.incident_id == identifier, Investigation.org_id == user.org_id
        )
    )
    if previous:
        return dump(previous)
    if settings.ai_mode == 'live' and not settings.openai_api_key:
        raise HTTPException(422, 'Live mode requires a server-side API key; use AI_MODE=demo')
    inv = Investigation(
        org_id=user.org_id,
        incident_id=incident.id,
        mode=settings.ai_mode if settings.ai_mode in ('live', 'demo') else 'demo',
    )
    db.add(inv)
    try:
        db.flush()
        audit(db, user.org_id, user.id, 'investigation_started', f'Investigation {inv.id}')
        db.commit()
    except IntegrityError:
        db.rollback()
        return dump(db.scalar(select(Investigation).where(Investigation.incident_id == identifier)))
    tasks.add_task(investigate, inv.id)
    return dump(inv)


@router.get('/investigations/{identifier}')
def workspace(identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    inv = owned(db, Investigation, identifier, user.org_id)
    return {
        **dump(inv),
        'incident': dump(owned(db, Incident, inv.incident_id, user.org_id)),
        'events': [
            dump(e)
            for e in rows(db, InvestigationEvent, user.org_id)
            if e.investigation_id == inv.id
        ],
        'runs': [
            dump(r)
            for r in rows(db, AgentRun, user.org_id)
            if r.investigation_id == inv.id and r.attempt == inv.attempt
        ],
    }


@router.get('/incidents/{identifier}/trace')
def tracing(identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return trace(db, owned(db, Incident, identifier, user.org_id))


@router.get('/incidents/{identifier}')
def incident_detail(
    identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return dump(owned(db, Incident, identifier, user.org_id))


@router.post('/investigations/{identifier}/retry', status_code=202)
def retry_investigation(
    identifier: int,
    tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    inv = owned(db, Investigation, identifier, user.org_id)
    if inv.status != 'failed' or inv.result:
        raise HTTPException(
            409, 'Only failed investigations without finalized findings may be retried'
        )
    if inv.mode == 'live' and not settings.openai_api_key:
        raise HTTPException(422, 'Live mode requires a configured API key')
    changed = db.execute(
        update(Investigation)
        .where(
            Investigation.id == inv.id,
            Investigation.status == 'failed',
            Investigation.org_id == user.org_id,
        )
        .values(status='queued')
    )
    if changed.rowcount != 1:
        raise HTTPException(409, 'Investigation is already being retried')
    audit(
        db,
        user.org_id,
        user.id,
        'investigation_retried',
        f'Investigation {inv.id}; previous runs and events retained',
    )
    db.commit()
    tasks.add_task(investigate, inv.id)
    return dump(inv)


@router.post('/documents', status_code=201)
def upload(
    file: UploadFile = File(...),
    incident_id: int | None = Form(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if incident_id is not None:
        owned(db, Incident, incident_id, user.org_id)
    content = file.file.read(MAX_SIZE + 1)
    doc, issues = store(db, user.org_id, file.filename or '', content, incident_id)
    audit(
        db,
        user.org_id,
        user.id,
        'document_uploaded',
        f'Document {doc.id}; extraction warnings: {issues}',
    )
    db.commit()
    return {
        'document': dump(doc),
        'issues': issues,
        'note': 'Evidence only; uploaded rows are not automatically promoted to validated manufacturing records.',
    }


@router.get('/documents/{identifier}/download')
def document_download(
    identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    doc = owned(db, EvidenceDocument, identifier, user.org_id)
    path = UPLOADS / doc.storage_key
    if not path.is_file():
        raise HTTPException(404, 'Source file unavailable')
    return FileResponse(path, media_type=doc.media_type, filename=doc.name)


@router.get('/documents/{identifier}')
def document(identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return dump(owned(db, EvidenceDocument, identifier, user.org_id))


@router.post('/proposals/{identifier}/decision')
def decide(
    identifier: int, body: Decision, user: User = Depends(reviewer), db: Session = Depends(get_db)
):
    # Serialize decisions where supported; pending predicate protects repeat decisions.
    proposal = db.scalar(
        select(ActionProposal)
        .where(ActionProposal.id == identifier, ActionProposal.org_id == user.org_id)
        .with_for_update()
    )
    if not proposal:
        raise HTTPException(404, 'Proposal not found')
    if proposal.status != 'pending':
        raise HTTPException(409, 'Proposal already reviewed')
    if body.decision == 'approved' and proposal.kind == 'inventory_release':
        open_holds = list(
            db.scalars(
                select(ActionProposal).where(
                    ActionProposal.org_id == user.org_id,
                    ActionProposal.kind == 'inventory_hold',
                    ActionProposal.status.in_(['pending', 'revision_requested']),
                )
            )
        )
        if any(set(p.target_batch_ids) & set(proposal.target_batch_ids) for p in open_holds):
            raise HTTPException(
                409, 'Resolve overlapping pending hold proposals before authorizing a release'
            )
        if not body.verification_confirmed:
            raise HTTPException(
                422,
                'Release requires an explicit reviewer attestation that source evidence and outstanding gaps have been verified',
            )
    changed = db.execute(
        update(ActionProposal)
        .where(
            ActionProposal.id == identifier,
            ActionProposal.org_id == user.org_id,
            ActionProposal.status == 'pending',
        )
        .values(status=body.decision)
    )
    if changed.rowcount != 1:
        raise HTTPException(409, 'Proposal already reviewed')
    if body.decision == 'approved' and proposal.kind in ('inventory_hold', 'inventory_release'):
        for batch_id in proposal.target_batch_ids:
            owned(db, ProductionBatch, batch_id, user.org_id).status = (
                'held_simulated' if proposal.kind == 'inventory_hold' else 'released_simulated'
            )
    db.add(
        Approval(
            org_id=user.org_id,
            proposal_id=proposal.id,
            user_id=user.id,
            decision=body.decision,
            comment=('[Source verification attested] ' if body.verification_confirmed else '')
            + body.comment,
        )
    )
    audit(
        db,
        user.org_id,
        user.id,
        'proposal_' + body.decision,
        f'Proposal {proposal.id}: {body.comment}; verification_attested={body.verification_confirmed}; internal simulation only',
    )
    db.flush()
    inv = owned(db, Investigation, proposal.investigation_id, user.org_id)
    all_proposals = list(
        db.scalars(
            select(ActionProposal).where(
                ActionProposal.investigation_id == inv.id, ActionProposal.org_id == user.org_id
            )
        )
    )
    inv.status = (
        'awaiting_review'
        if any(p.status in ('pending', 'revision_requested') for p in all_proposals)
        else 'completed'
    )
    db.add(
        InvestigationEvent(
            org_id=user.org_id,
            investigation_id=inv.id,
            message=f'Human reviewer {user.id}: proposal {proposal.id} {body.decision}. {body.comment}',
        )
    )
    db.commit()
    return dump(proposal)


@router.post('/proposals', status_code=201)
def draft_proposal(
    body: ProposalInput, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    inv = owned(db, Investigation, body.investigation_id, user.org_id)
    if not inv.result.get('trace'):
        raise HTTPException(409, 'Complete the investigation before drafting actions')
    traced = inv.result['trace']
    proposal = ActionProposal(
        org_id=user.org_id,
        investigation_id=inv.id,
        kind=body.kind,
        justification=body.justification,
        target_batch_ids=[b['id'] for b in traced['batches']],
        evidence=sorted({e['reference'] for e in traced['edges']}),
        status='pending',
    )
    db.add(proposal)
    db.flush()
    inv.status = 'awaiting_review'
    audit(
        db,
        user.org_id,
        user.id,
        'proposal_drafted',
        f'Proposal {proposal.id}; {proposal.kind}; no operational action executed',
    )
    db.commit()
    return dump(proposal)


@router.post('/proposals/{identifier}/revise')
def revise(
    identifier: int,
    body: RevisionInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    proposal = owned(db, ActionProposal, identifier, user.org_id)
    if proposal.status != 'revision_requested':
        raise HTTPException(409, 'Only proposals with requested revisions may be resubmitted')
    previous = proposal.justification
    history = [
        *proposal.revision_history,
        {
            'previous': previous,
            'revised': body.justification,
            'user_id': user.id,
            'at': now().isoformat(),
        },
    ]
    changed = db.execute(
        update(ActionProposal)
        .where(
            ActionProposal.id == identifier,
            ActionProposal.org_id == user.org_id,
            ActionProposal.status == 'revision_requested',
        )
        .values(justification=body.justification, revision_history=history, status='pending')
    )
    if changed.rowcount != 1:
        raise HTTPException(409, 'Proposal was already resubmitted')
    audit(
        db,
        user.org_id,
        user.id,
        'proposal_revised',
        f'Proposal {identifier}; revision {len(history)} retained in proposal revision history',
    )
    db.commit()
    return dump(proposal)


@router.post('/users', status_code=201)
def create_user(body: UserInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != 'admin':
        raise HTTPException(403, 'Admin permission required')
    email = body.email.lower().strip()
    if '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(422, 'Valid email required')
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Email already registered')
    member = User(
        org_id=user.org_id,
        email=email,
        name=body.name,
        role=body.role,
        password_hash=passwords.hash(body.password),
    )
    db.add(member)
    db.flush()
    audit(db, user.org_id, user.id, 'user_created', f'User {member.id}; role {member.role}')
    db.commit()
    return dump(member)


@router.patch('/users/{identifier}/role')
def change_role(
    identifier: int,
    body: RoleInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role != 'admin':
        raise HTTPException(403, 'Admin permission required')
    member = owned(db, User, identifier, user.org_id)
    if member.id == user.id:
        raise HTTPException(409, 'Ask another administrator to change your role')
    previous = member.role
    member.role = body.role
    db.execute(
        update(User).where(User.id == member.id).values(token_version=User.token_version + 1)
    )
    audit(
        db, user.org_id, user.id, 'user_role_changed', f'User {member.id}: {previous} → {body.role}'
    )
    db.commit()
    return dump(member)


@router.get('/investigations/{identifier}/report')
def pdf(identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    inv = owned(db, Investigation, identifier, user.org_id)
    if inv.status not in ('awaiting_review', 'completed'):
        raise HTTPException(409, 'Investigation findings are not ready')
    content = report(db, inv, owned(db, Incident, inv.incident_id, user.org_id))
    audit(db, user.org_id, user.id, 'report_downloaded', f'Investigation {identifier}')
    db.commit()
    return Response(
        content,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="traceback-{identifier}.pdf"'},
    )
