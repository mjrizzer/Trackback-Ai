from sqlalchemy import select
import csv
from io import StringIO
from fastapi import HTTPException
from backend.models import *


def rows(db, model, org):
    return list(db.scalars(select(model).where(model.org_id == org).order_by(model.id)))


def owned(db, model, identifier, org):
    value = db.scalar(select(model).where(model.id == identifier, model.org_id == org))
    if value is None:
        raise HTTPException(404, 'Record not found')
    return value


def dump(row):
    result = {}
    for column in row.__table__.columns:
        if column.name in ('password_hash', 'storage_key', 'token_version'):
            continue
        value = getattr(row, column.name)
        # SQLite drops timezone metadata; all stored timestamps are UTC.
        if isinstance(value, datetime):
            value = (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()
        result[column.name] = value
    return result


def audit(db, org, user, action, detail):
    db.add(AuditLog(org_id=org, user_id=user, action=action, detail=detail))


def trace(db, incident):
    org = incident.org_id
    lots = [owned(db, MaterialLot, incident.lot_id, org)] if incident.lot_id else []
    batches = []
    if lots:
        batches = list(
            db.scalars(
                select(ProductionBatch)
                .join(BatchMaterialUsage, BatchMaterialUsage.batch_id == ProductionBatch.id)
                .where(
                    ProductionBatch.org_id == org,
                    BatchMaterialUsage.org_id == org,
                    BatchMaterialUsage.lot_id == lots[0].id,
                )
                .distinct()
            )
        )
    if incident.batch_id:
        batch = owned(db, ProductionBatch, incident.batch_id, org)
        if batch.id not in [b.id for b in batches]:
            batches.append(batch)
        lots = list(
            db.scalars(
                select(MaterialLot)
                .join(BatchMaterialUsage, BatchMaterialUsage.lot_id == MaterialLot.id)
                .where(
                    MaterialLot.org_id == org,
                    BatchMaterialUsage.org_id == org,
                    BatchMaterialUsage.batch_id.in_([b.id for b in batches]),
                )
                .distinct()
            )
        )
    ids = [b.id for b in batches]
    items = list(
        db.scalars(
            select(ShipmentItem).where(ShipmentItem.org_id == org, ShipmentItem.batch_id.in_(ids))
        )
    )
    shipments = list(
        db.scalars(
            select(Shipment).where(
                Shipment.org_id == org, Shipment.id.in_([x.shipment_id for x in items])
            )
        )
    )
    customers = list(
        db.scalars(
            select(Customer).where(
                Customer.org_id == org, Customer.id.in_([s.customer_id for s in shipments])
            )
        )
    )
    suppliers = list(
        db.scalars(
            select(Supplier).where(
                Supplier.org_id == org, Supplier.id.in_([l.supplier_id for l in lots])
            )
        )
    )
    usage = list(
        db.scalars(
            select(BatchMaterialUsage).where(
                BatchMaterialUsage.org_id == org,
                BatchMaterialUsage.lot_id.in_([l.id for l in lots]),
                BatchMaterialUsage.batch_id.in_(ids),
            )
        )
    )
    nodes = [
        {
            'id': f'{kind}:{r.id}',
            'kind': kind,
            'label': getattr(r, 'code', getattr(r, 'name', '')),
            'record': dump(r),
        }
        for kind, records in [
            ('supplier', suppliers),
            ('lot', lots),
            ('batch', batches),
            ('shipment', shipments),
            ('customer', customers),
        ]
        for r in records
    ]
    edges = (
        [
            {
                'source': f'supplier:{l.supplier_id}',
                'target': f'lot:{l.id}',
                'reference': f'material_lots:{l.id}',
            }
            for l in lots
        ]
        + [
            {
                'source': f'lot:{u.lot_id}',
                'target': f'batch:{u.batch_id}',
                'reference': f'batch_material_usage:{u.id}',
            }
            for u in usage
        ]
        + [
            {
                'source': f'batch:{i.batch_id}',
                'target': f'shipment:{i.shipment_id}',
                'reference': f'shipment_items:{i.id}',
            }
            for i in items
        ]
        + [
            {
                'source': f'shipment:{s.id}',
                'target': f'customer:{s.customer_id}',
                'reference': f'shipments:{s.id}',
            }
            for s in shipments
        ]
    )
    return {
        'lots': [dump(x) for x in lots],
        'batches': [dump(x) for x in batches],
        'shipments': [dump(x) for x in shipments],
        'customers': [dump(x) for x in customers],
        'potential_units': sum(i.quantity for i in items),
        'nodes': nodes,
        'edges': edges,
    }


def evidence(db, incident, traced):
    ids = [b['id'] for b in traced['batches']]
    inspections = list(
        db.scalars(
            select(Inspection).where(
                Inspection.org_id == incident.org_id, Inspection.batch_id.in_(ids)
            )
        )
    )
    docs = rows(db, EvidenceDocument, incident.org_id)
    codes = [b['code'] for b in traced['batches']] + [l['code'] for l in traced['lots']]
    import re

    docs = [
        d
        for d in docs
        if d.incident_id == incident.id
        or any(
            re.search(r'(?<![A-Za-z0-9_-])' + re.escape(c) + r'(?![A-Za-z0-9_-])', d.text)
            for c in codes
        )
        or d.id in [i.document_id for i in inspections]
    ]
    missing = [
        {
            'kind': 'missing',
            'detail': f'No inspection record for {b["code"]}',
            'references': [f'production_batches:{b["id"]}'],
        }
        for b in traced['batches']
        if b['id'] not in [i.batch_id for i in inspections]
    ]
    conflicts = []
    for b in ids:
        for test in sorted({i.test for i in inspections if i.batch_id == b}):
            group = [i for i in inspections if i.batch_id == b and i.test == test]
            if len({i.result for i in group}) > 1:
                conflicts.append(
                    {
                        'kind': 'conflict',
                        'detail': f'Batch {b}: contradictory {test} results; timestamps alone cannot establish which result is correct.',
                        'references': [f'inspections:{i.id}' for i in group]
                        + [f'evidence_documents:{i.document_id}' for i in group],
                    }
                )
    document_findings = []
    known_batches = {b.code for b in rows(db, ProductionBatch, incident.org_id)}
    known_lots = {l.code for l in rows(db, MaterialLot, incident.org_id)}
    claims = {}
    for doc in docs:
        if doc.media_type != 'text/csv':
            continue
        for number, row in enumerate(csv.DictReader(StringIO(doc.text)), 2):
            ref = f'evidence_documents:{doc.id}'
            if None in row or any(value in ('', None) for value in row.values()):
                document_findings.append(
                    {
                        'kind': 'missing',
                        'detail': f'{doc.name}, row {number}: missing values or inconsistent columns.',
                        'references': [ref],
                    }
                )
            for field, known in [('batch_code', known_batches), ('lot_code', known_lots)]:
                if row.get(field) and row[field] not in known:
                    document_findings.append(
                        {
                            'kind': 'identifier',
                            'detail': f'{doc.name}, row {number}: unknown {field} {row[field]}; no relationship inferred.',
                            'references': [ref],
                        }
                    )
            key = (row.get('batch_code'), row.get('test'))
            if all(key) and row.get('result'):
                claims.setdefault(key, []).append((row['result'].lower(), ref))
    already_conflicting = {
        (i.batch_id, i.test)
        for i in inspections
        if len({j.result for j in inspections if j.batch_id == i.batch_id and j.test == i.test}) > 1
    }
    for (code, test), group in claims.items():
        batch = next((b for b in traced['batches'] if b['code'] == code), None)
        canonical = [
            i for i in inspections if batch and i.batch_id == batch['id'] and i.test == test
        ]
        values = {value for value, _ in group} | {i.result.lower() for i in canonical}
        if len(values) > 1 and (not batch or (batch['id'], test) not in already_conflicting):
            document_findings.append(
                {
                    'kind': 'conflict',
                    'detail': f'{code}: uploaded {test} claims disagree with another source or validated inspection. Original laboratory verification required.',
                    'references': sorted(
                        {ref for _, ref in group} | {f'inspections:{i.id}' for i in canonical}
                    ),
                }
            )
    return {
        'inspections': [dump(i) for i in inspections],
        'documents': [dump(d) for d in docs],
        'findings': missing + conflicts + document_findings,
    }
