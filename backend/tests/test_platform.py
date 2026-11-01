from io import BytesIO
from sqlalchemy import select
import pytest
from pypdf import PdfReader
from backend.database import SessionLocal
from backend.models import *
from backend.services.records import trace, evidence
from backend.schemas import ToolArguments
from backend.tools.investigation import InvestigationTools


def records(client, auth, kind):
    response = client.get('/api/records/' + kind, headers=auth)
    assert response.status_code == 200
    return response.json()


def test_authentication(client, auth):
    client.cookies.clear()
    assert client.get('/api/me').status_code in (401, 403)
    assert (
        client.post(
            '/api/auth/login', json={'email': 'admin@novafoods.demo', 'password': 'wrong'}
        ).status_code
        == 401
    )
    assert client.get('/api/me', headers=auth).json()['user']['role'] == 'admin'


def test_timestamps_include_utc_offset(client, auth):
    incident = client.get('/api/records/incidents', headers=auth).json()[0]
    assert incident['created_at'].endswith('+00:00')


def test_relationship_counts(client, auth):
    for kind, count in [
        ('suppliers', 8),
        ('lots', 25),
        ('batches', 60),
        ('shipments', 100),
        ('customers', 30),
    ]:
        assert len(records(client, auth, kind)) == count


def test_deterministic_trace_excludes_unrelated_shipments(client, auth):
    result = client.get('/api/incidents/1/trace', headers=auth).json()
    assert {b['code'] for b in result['batches']} == {'PB-001', 'PB-002', 'PB-003', 'PB-004'}
    assert {s['code'] for s in result['shipments']} == {
        'SHP-0001',
        'SHP-0002',
        'SHP-0003',
        'SHP-0004',
        'SHP-0061',
        'SHP-0062',
        'SHP-0063',
        'SHP-0064',
    }
    assert result['potential_units'] == 4800
    assert len(result['customers']) == 4


def test_missing_and_conflicting_records(client, auth):
    with SessionLocal() as db:
        a = db.get(Incident, 1)
        findings = evidence(db, a, trace(db, a))['findings']
        assert any('PB-003' in f['detail'] and f['kind'] == 'missing' for f in findings)
        b = db.get(Incident, 2)
        ev = evidence(db, b, trace(db, b))
        assert len([f for f in ev['findings'] if f['kind'] == 'conflict']) == 1
        assert len(ev['documents']) == 2
        assert {i['result'] for i in ev['inspections']} == {'pass', 'fail'}


def test_incident_creation_and_validation(client, auth):
    assert client.post('/api/incidents', headers=auth, json={'title': 'x'}).status_code == 422
    result = client.post(
        '/api/incidents',
        headers=auth,
        json={
            'title': 'Shipment follow up',
            'description': 'Review original delivery records.',
            'category': 'shipment',
            'severity': 'medium',
        },
    )
    assert result.status_code == 201
    assert result.json()['status'] == 'open'


def test_full_investigation_approval_and_pdf(client, auth):
    response = client.post('/api/incidents/1/investigate', headers=auth)
    assert response.status_code == 202
    identifier = response.json()['id']
    inv = client.get(f'/api/investigations/{identifier}', headers=auth).json()
    assert inv['status'] == 'awaiting_review'
    assert len(inv['runs']) == 5
    assert len(inv['events']) >= 12
    assert inv['result']['risk']['estimated_exposure_units'] == 4800
    proposals = records(client, auth, 'proposals')
    proposal = next(p for p in proposals if p['investigation_id'] == identifier)
    assert proposal['status'] == 'pending'
    # Agents drafted a hold but could not execute it.
    assert all(b['status'] == 'released' for b in records(client, auth, 'batches')[:4])
    analyst = client.post(
        '/api/auth/login', json={'email': 'analyst@novafoods.demo', 'password': 'NovaFoods!2026'}
    ).json()
    assert (
        client.post(
            f'/api/proposals/{proposal["id"]}/decision',
            headers={'Authorization': 'Bearer ' + analyst['access_token']},
            json={'decision': 'approved', 'comment': 'Attempt bypass'},
        ).status_code
        == 403
    )
    approved = client.post(
        f'/api/proposals/{proposal["id"]}/decision',
        headers=auth,
        json={
            'decision': 'approved',
            'comment': 'Precautionary hold pending supplier confirmation',
        },
    )
    assert approved.status_code == 200
    assert all(b['status'] == 'held_simulated' for b in records(client, auth, 'batches')[:4])
    assert (
        client.post(
            f'/api/proposals/{proposal["id"]}/decision',
            headers=auth,
            json={'decision': 'rejected', 'comment': 'Second decision'},
        ).status_code
        == 409
    )
    pdf = client.get(f'/api/investigations/{identifier}/report', headers=auth)
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    text = ''.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
    assert 'RM-042' in text and 'PB-003' in text and 'approved' in text
    assert any(a['action'] == 'proposal_approved' for a in records(client, auth, 'audit'))


def test_conflict_integration_and_rejection(client, auth):
    inv = client.post('/api/incidents/2/investigate', headers=auth).json()
    result = client.get(f'/api/investigations/{inv["id"]}', headers=auth).json()
    assert result['status'] == 'awaiting_review'
    assert result['result']['evidence']['findings'][0]['kind'] == 'conflict'
    proposal = next(
        p for p in records(client, auth, 'proposals') if p['investigation_id'] == inv['id']
    )
    response = client.post(
        f'/api/proposals/{proposal["id"]}/decision',
        headers=auth,
        json={'decision': 'rejected', 'comment': 'Reconcile original lab certificates first'},
    )
    assert response.json()['status'] == 'rejected'


def test_agent_tool_permission_validation(client, auth):
    client.post('/api/incidents/1/investigate', headers=auth)
    with pytest.raises(Exception):
        ToolArguments.model_validate({'org_id': 999, 'sql': 'delete from users'})
    with SessionLocal() as db:
        inv = db.scalar(select(Investigation))
        run = db.scalar(select(AgentRun).where(AgentRun.investigation_id == inv.id))
        tools = InvestigationTools(db, inv, run)
        with pytest.raises(ValueError, match='not authorized'):
            tools.call('approve_action', {})
        assert tools.call('get_incident_details', {})['incident']['org_id'] == inv.org_id


def test_upload_restrictions_and_csv_issues(client, auth):
    assert (
        client.post(
            '/api/documents', headers=auth, files={'file': ('evil.exe', b'MZ executable')}
        ).status_code
        == 422
    )
    assert (
        client.post(
            '/api/documents', headers=auth, files={'file': ('invalid.pdf', b'not a pdf')}
        ).status_code
        == 422
    )
    content = (
        b'batch_code,test,result\nPB-012,microbiology,pass\nPB-012,microbiology,fail\nPB-013,,\n'
    )
    response = client.post(
        '/api/documents',
        headers=auth,
        files={'file': ('inspection.csv', content)},
        data={'incident_id': '2'},
    )
    assert response.status_code == 201
    assert len(response.json()['issues']) == 2
    identifier = response.json()['document']['id']
    assert client.get(f'/api/documents/{identifier}/download', headers=auth).content == content


def test_organization_isolation(client, auth):
    result = client.post(
        '/api/auth/register',
        json={
            'email': 'isolated@example.com',
            'password': 'LongPassword!23',
            'name': 'Another Admin',
            'organization': 'Isolated Co',
        },
    )
    assert result.status_code == 201
    headers = {'Authorization': 'Bearer ' + result.json()['access_token']}
    assert records(client, headers, 'shipments') == []
    assert client.get('/api/incidents/1/trace', headers=headers).status_code == 404
    assert client.get('/api/documents/1', headers=headers).status_code == 404
    assert client.get('/api/investigations/1/report', headers=headers).status_code == 404
    assert (
        client.post(
            '/api/incidents',
            headers=headers,
            json={
                'title': 'Foreign lot',
                'description': 'Attempt foreign material lot.',
                'category': 'other',
                'severity': 'low',
                'lot_id': 1,
            },
        ).status_code
        == 404
    )


def test_revision_release_and_notification_drafts(client, auth):
    inv = client.post('/api/incidents/1/investigate', headers=auth).json()
    proposal = client.post(
        '/api/proposals',
        headers=auth,
        json={
            'investigation_id': inv['id'],
            'kind': 'inventory_release',
            'justification': 'Release only after laboratory verification is approved.',
        },
    )
    assert proposal.status_code == 201
    pid = proposal.json()['id']
    assert (
        client.post(
            f'/api/proposals/{pid}/decision',
            headers=auth,
            json={
                'decision': 'revision_requested',
                'comment': 'Please attach supplier confirmation.',
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f'/api/proposals/{pid}/revise',
            headers=auth,
            json={
                'justification': 'Revised simulated release draft after evidence reconciliation.'
            },
        ).json()['status']
        == 'pending'
    )
    assert (
        client.post(
            f'/api/proposals/{pid}/decision',
            headers=auth,
            json={
                'decision': 'approved',
                'comment': 'Release authorized after source verification.',
                'verification_confirmed': True,
            },
        ).status_code
        == 200
    )
    assert all(b['status'] == 'released_simulated' for b in records(client, auth, 'batches')[:4])
    for kind in ['supplier_escalation', 'customer_notification', 'corrective_assignment']:
        draft = client.post(
            '/api/proposals',
            headers=auth,
            json={
                'investigation_id': inv['id'],
                'kind': kind,
                'justification': 'Internal review draft; verification required before sending.',
            },
        )
        assert draft.status_code == 201 and draft.json()['status'] == 'pending'


def test_user_management_and_tenant_write_guard(client, auth):
    response = client.post(
        '/api/users',
        headers=auth,
        json={
            'name': 'New Reviewer',
            'email': 'new@novafoods.demo',
            'password': 'ReviewerPass!23',
            'role': 'analyst',
        },
    )
    assert response.status_code == 201
    assert 'password_hash' not in response.json()
    assert (
        client.patch(
            f'/api/users/{response.json()["id"]}/role', headers=auth, json={'role': 'reviewer'}
        ).json()['role']
        == 'reviewer'
    )
    with SessionLocal() as db:
        org = Organization(name='Write isolation test')
        db.add(org)
        db.flush()
        bad = MaterialLot(
            org_id=org.id,
            code='BAD',
            supplier_id=1,
            material='Invalid cross tenant reference',
            quantity=1,
        )
        db.add(bad)
        with pytest.raises(ValueError, match='Cross-organization'):
            db.flush()
        db.rollback()


def test_uploaded_claims_and_identifiers_are_evidence(client, auth):
    content = b'batch_code,test,result\nPB-001,microbiology,fail\nPB-999,microbiology,pass\n'
    result = client.post(
        '/api/documents',
        headers=auth,
        files={'file': ('claims.csv', content)},
        data={'incident_id': '1'},
    )
    assert result.status_code == 201
    with SessionLocal() as db:
        incident = db.get(Incident, 1)
        findings = evidence(db, incident, trace(db, incident))['findings']
        assert any(f['kind'] == 'identifier' and 'PB-999' in f['detail'] for f in findings)
        assert any(f['kind'] == 'conflict' and 'PB-001' in f['detail'] for f in findings)
        # Imported claims do not mutate validated inspection results.
        assert db.scalar(select(Inspection).where(Inspection.batch_id == 1)).result == 'pass'
