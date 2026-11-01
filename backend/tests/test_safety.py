import pytest
from backend.config import Settings, settings
from backend.database import SessionLocal
from backend.models import Incident, Investigation, ActionProposal
from backend.services.documents import store, extract
from backend.services.records import evidence, trace
from backend.services.safety import login_limiter


def test_blank_input_and_invalid_identifiers_are_rejected(client, auth):
    base = {
        'title': '     ',
        'description': '                    ',
        'category': 'quality',
        'severity': 'high',
    }
    assert client.post('/api/incidents', headers=auth, json=base).status_code == 422
    assert (
        client.post(
            '/api/incidents',
            headers=auth,
            json={
                **base,
                'title': 'Valid title',
                'description': 'Valid detailed description',
                'lot_id': 0,
            },
        ).status_code
        == 422
    )
    assert client.get('/api/incidents/999999', headers=auth).status_code == 404


def test_cookie_security_csrf_and_logout_revocation(client):
    result = client.post(
        '/api/auth/login', json={'email': 'admin@novafoods.demo', 'password': 'NovaFoods!2026'}
    )
    assert (
        'HttpOnly' in result.headers['set-cookie']
        and 'SameSite=lax' in result.headers['set-cookie']
    )
    bearer = {'Authorization': 'Bearer ' + result.json()['access_token']}
    assert client.get('/api/me').status_code == 200
    assert client.post('/api/auth/logout', headers={'X-CSRF-Protection': ''}).status_code == 403
    assert (
        client.post('/api/auth/logout', headers={'Origin': 'https://attacker.invalid'}).status_code
        == 403
    )
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/me', headers=bearer).status_code == 401


def test_login_rate_limit_and_response_headers(client, monkeypatch):
    monkeypatch.setattr(settings, 'auth_rate_limit', 2)
    login_limiter.entries.clear()
    try:
        for _ in range(2):
            assert (
                client.post(
                    '/api/auth/login', json={'email': 'nobody@example.com', 'password': 'wrong'}
                ).status_code
                == 401
            )
        rejected = client.post(
            '/api/auth/login', json={'email': 'nobody@example.com', 'password': 'wrong'}
        )
        assert rejected.status_code == 429 and rejected.headers['retry-after'] == '60'
        response = client.get('/health')
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.headers['x-frame-options'] == 'DENY'
    finally:
        login_limiter.entries.clear()


def test_production_rejects_missing_or_weak_secrets():
    with pytest.raises(ValueError, match='JWT_SECRET'):
        Settings(_env_file=None, environment='production', jwt_secret='')
    with pytest.raises(ValueError, match='JWT_SECRET'):
        Settings(_env_file=None, environment='production', jwt_secret='short')


def test_request_size_limit_and_duplicate_csv_headers(client, auth):
    assert (
        client.post(
            '/api/incidents',
            headers={**auth, 'Content-Type': 'application/json'},
            content=b'x' * (256 * 1024 + 1),
        ).status_code
        == 413
    )
    with pytest.raises(Exception, match='headers'):
        extract('duplicate.csv', b'batch_code,result,result\nPB-001,pass,fail\n')


def test_rollback_removes_uncommitted_source_files(client):
    from backend.services.documents import UPLOADS

    with SessionLocal() as db:
        doc, _ = store(db, 1, 'rollback.csv', b'field,value\na,b\n')
        path = UPLOADS / doc.storage_key
        assert path.is_file()
        db.rollback()
        assert not path.exists()


def test_document_code_matching_uses_exact_identifiers(client):
    with SessionLocal() as db:
        doc, _ = store(
            db, 1, 'unrelated-prefix.csv', b'batch_code,test,result\nPB-0010,microbiology,fail\n'
        )
        db.commit()
        incident = db.get(Incident, 1)
        ev = evidence(db, incident, trace(db, incident))
        assert doc.id not in {d['id'] for d in ev['documents']}


def test_failed_investigation_retry_keeps_history(client, auth):
    body = {
        'title': 'Retry investigation test',
        'description': 'Retry an interrupted investigation safely.',
        'category': 'records',
        'severity': 'medium',
    }
    incident = client.post('/api/incidents', headers=auth, json=body).json()
    with SessionLocal() as db:
        inv = Investigation(org_id=1, incident_id=incident['id'], status='failed', mode='demo')
        db.add(inv)
        db.commit()
        identifier = inv.id
    assert client.post(f'/api/investigations/{identifier}/retry', headers=auth).status_code == 202
    result = client.get(f'/api/investigations/{identifier}', headers=auth).json()
    assert result['status'] == 'awaiting_review' and len(result['runs']) == 5
    assert result['attempt'] == 1
    assert client.post(f'/api/investigations/{identifier}/retry', headers=auth).status_code == 409


def test_release_needs_source_verification_attestation(client, auth):
    inv = client.post('/api/incidents/1/investigate', headers=auth).json()
    proposal = client.post(
        '/api/proposals',
        headers=auth,
        json={
            'investigation_id': inv['id'],
            'kind': 'inventory_release',
            'justification': 'Review all source evidence before releasing inventory.',
        },
    ).json()
    result = client.post(
        f'/api/proposals/{proposal["id"]}/decision',
        headers=auth,
        json={'decision': 'approved', 'comment': 'Verified release review.'},
    )
    assert result.status_code in (409, 422)
    with SessionLocal() as db:
        assert db.get(ActionProposal, proposal['id']).status == 'pending'


def test_password_change_revokes_existing_sessions(client, auth):
    member = client.post(
        '/api/users',
        headers=auth,
        json={
            'name': 'Password Test',
            'email': 'password-test@example.com',
            'password': 'OriginalPassword!23',
            'role': 'analyst',
        },
    ).json()
    session = client.post(
        '/api/auth/login', json={'email': member['email'], 'password': 'OriginalPassword!23'}
    ).json()
    headers = {'Authorization': 'Bearer ' + session['access_token']}
    changed = client.post(
        '/api/auth/password',
        headers=headers,
        json={'current_password': 'OriginalPassword!23', 'new_password': 'UpdatedPassword!234'},
    )
    assert changed.status_code == 200
    assert client.get('/api/me', headers=headers).status_code == 401
    assert (
        client.post(
            '/api/auth/login', json={'email': member['email'], 'password': 'UpdatedPassword!234'}
        ).status_code
        == 200
    )
