"""Explicit user-created operational records; these routes are never agent tools."""

import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import (
    Supplier,
    MaterialLot,
    ProductionBatch,
    BatchMaterialUsage,
    Customer,
    Shipment,
    ShipmentItem,
    Inspection,
    EvidenceDocument,
    User,
)
from backend.schemas.manufacturing import (
    SupplierInput,
    LotInput,
    BatchInput,
    CustomerInput,
    ShipmentInput,
    InspectionInput,
)
from backend.security import current_user, reviewer
from backend.services.records import owned, dump, audit

router = APIRouter(prefix='/api')


def save(db, user, row, action):
    db.add(row)
    db.flush()
    audit(
        db,
        user.org_id,
        user.id,
        action,
        f'{row.__tablename__}:{row.id}; explicit authenticated user entry',
    )
    db.commit()
    return dump(row)


@router.post('/suppliers', status_code=201)
def create_supplier(
    body: SupplierInput, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return save(db, user, Supplier(org_id=user.org_id, **body.model_dump()), 'supplier_created')


@router.post('/lots', status_code=201)
def create_lot(body: LotInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned(db, Supplier, body.supplier_id, user.org_id)
    return save(
        db, user, MaterialLot(org_id=user.org_id, **body.model_dump()), 'material_lot_created'
    )


@router.post('/customers', status_code=201)
def create_customer(
    body: CustomerInput, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return save(db, user, Customer(org_id=user.org_id, **body.model_dump()), 'customer_created')


@router.post('/batches', status_code=201)
def create_batch(
    body: BatchInput, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if len({m.lot_id for m in body.materials}) != len(body.materials):
        raise HTTPException(422, 'Each material lot must appear once')
    # Lock lots in a stable order to prevent oversubscription and deadlocks.
    for material in sorted(body.materials, key=lambda m: m.lot_id):
        owned(db, MaterialLot, material.lot_id, user.org_id)
        changed = db.execute(
            update(MaterialLot)
            .where(
                MaterialLot.id == material.lot_id,
                MaterialLot.org_id == user.org_id,
                MaterialLot.status == 'available',
                MaterialLot.quantity >= material.quantity,
            )
            .values(quantity=MaterialLot.quantity - material.quantity)
        )
        if changed.rowcount != 1:
            raise HTTPException(
                409, 'Material lot is unavailable or has insufficient remaining quantity'
            )
    batch = ProductionBatch(
        org_id=user.org_id, code=body.code, product=body.product, quantity=body.quantity
    )
    db.add(batch)
    db.flush()
    for material in body.materials:
        db.add(BatchMaterialUsage(org_id=user.org_id, batch_id=batch.id, **material.model_dump()))
    return save(db, user, batch, 'production_batch_created')


@router.post('/shipments', status_code=201)
def create_shipment(
    body: ShipmentInput, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    owned(db, Customer, body.customer_id, user.org_id)
    if len({i.batch_id for i in body.items}) != len(body.items):
        raise HTTPException(422, 'Each batch must appear once')
    for item in sorted(body.items, key=lambda i: i.batch_id):
        # A write lock also serializes this check on SQLite, whose SELECT FOR UPDATE is a no-op.
        db.execute(
            update(ProductionBatch)
            .where(ProductionBatch.id == item.batch_id, ProductionBatch.org_id == user.org_id)
            .values(quantity=ProductionBatch.quantity)
        )
        batch = db.scalar(
            select(ProductionBatch)
            .where(ProductionBatch.id == item.batch_id, ProductionBatch.org_id == user.org_id)
            .with_for_update()
        )
        if not batch:
            raise HTTPException(404, 'Batch not found')
        if batch.status not in ('released', 'released_simulated'):
            raise HTTPException(409, f'{batch.code} is held and cannot be shipped')
        shipped = db.scalar(
            select(func.coalesce(func.sum(ShipmentItem.quantity), 0)).where(
                ShipmentItem.batch_id == batch.id, ShipmentItem.org_id == user.org_id
            )
        )
        if shipped + item.quantity > batch.quantity:
            raise HTTPException(409, f'{batch.code} has insufficient unshipped units')
    shipment = Shipment(
        org_id=user.org_id,
        code=body.code,
        customer_id=body.customer_id,
        status='dispatched_simulated',
    )
    db.add(shipment)
    db.flush()
    for item in body.items:
        db.add(ShipmentItem(org_id=user.org_id, shipment_id=shipment.id, **item.model_dump()))
    return save(db, user, shipment, 'shipment_created')


@router.post('/inspections', status_code=201)
def create_inspection(
    body: InspectionInput, user: User = Depends(reviewer), db: Session = Depends(get_db)
):
    batch = owned(db, ProductionBatch, body.batch_id, user.org_id)
    document = owned(db, EvidenceDocument, body.document_id, user.org_id)
    code_found = re.search(
        r'(?<![A-Za-z0-9_-])' + re.escape(batch.code) + r'(?![A-Za-z0-9_-])', document.text
    )
    if not code_found or not re.search(r'\b' + body.result + r'\b', document.text, re.IGNORECASE):
        raise HTTPException(
            422, 'Source document must identify the batch and contain the recorded pass/fail result'
        )
    return save(
        db, user, Inspection(org_id=user.org_id, **body.model_dump()), 'inspection_verified'
    )
