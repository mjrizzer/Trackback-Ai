from backend.database import SessionLocal
from backend.models import ProductionBatch


def test_new_organization_can_build_and_trace_its_supply_chain(client):
    registration = client.post(
        '/api/auth/register',
        json={
            'email': 'factory@example.com',
            'password': 'FactoryPassword!23',
            'name': 'Factory Admin',
            'organization': 'New Test Factory',
        },
    )
    assert registration.status_code == 201
    auth = {'Authorization': 'Bearer ' + registration.json()['access_token']}
    supplier = client.post('/api/suppliers', headers=auth, json={'name': 'Test Supplier'}).json()
    lot = client.post(
        '/api/lots',
        headers=auth,
        json={
            'code': 'TEST-RM',
            'supplier_id': supplier['id'],
            'material': 'Oat flour',
            'quantity': 100,
        },
    ).json()
    batch_input = {
        'code': 'TEST-PB',
        'product': 'Test bars',
        'quantity': 1000,
        'materials': [{'lot_id': lot['id'], 'quantity': 20}],
    }
    response = client.post('/api/batches', headers=auth, json=batch_input)
    assert response.status_code == 201
    batch = response.json()
    assert client.get('/api/records/lots', headers=auth).json()[0]['quantity'] == 80
    assert (
        client.post(
            '/api/batches',
            headers=auth,
            json={
                **batch_input,
                'code': 'TOO-MUCH',
                'materials': [{'lot_id': lot['id'], 'quantity': 1000}],
            },
        ).status_code
        == 409
    )
    # A failed duplicate-code transaction must not consume another 20 kg.
    assert client.post('/api/batches', headers=auth, json=batch_input).status_code == 409
    assert client.get('/api/records/lots', headers=auth).json()[0]['quantity'] == 80
    customer = client.post(
        '/api/customers', headers=auth, json={'name': 'Test Retail', 'region': 'South'}
    ).json()
    shipment_input = {
        'code': 'TEST-SHP',
        'customer_id': customer['id'],
        'items': [{'batch_id': batch['id'], 'quantity': 600}],
    }
    assert client.post('/api/shipments', headers=auth, json=shipment_input).status_code == 201
    assert (
        client.post(
            '/api/shipments', headers=auth, json={**shipment_input, 'code': 'OVER-SHP'}
        ).status_code
        == 409
    )
    with SessionLocal() as db:
        db.get(ProductionBatch, batch['id']).status = 'held_simulated'
        db.commit()
    assert (
        client.post(
            '/api/shipments',
            headers=auth,
            json={
                **shipment_input,
                'code': 'HELD-SHP',
                'items': [{'batch_id': batch['id'], 'quantity': 10}],
            },
        ).status_code
        == 409
    )
    csv = b'batch_code,test,result\nTEST-PB,microbiology,pass\n'
    doc = client.post('/api/documents', headers=auth, files={'file': ('test.csv', csv)}).json()[
        'document'
    ]
    assert (
        client.post(
            '/api/inspections',
            headers=auth,
            json={
                'batch_id': batch['id'],
                'document_id': doc['id'],
                'test': 'microbiology',
                'result': 'pass',
            },
        ).status_code
        == 201
    )
    incident = client.post(
        '/api/incidents',
        headers=auth,
        json={
            'title': 'New factory incident',
            'description': 'Verify tracing for our own factory records.',
            'category': 'quality',
            'severity': 'high',
            'lot_id': lot['id'],
        },
    ).json()
    result = client.get(f'/api/incidents/{incident["id"]}/trace', headers=auth).json()
    assert [b['id'] for b in result['batches']] == [batch['id']]
    assert result['potential_units'] == 600
    assert result['customers'][0]['id'] == customer['id']
