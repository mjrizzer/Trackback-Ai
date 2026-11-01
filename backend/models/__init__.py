from datetime import datetime, timezone
from sqlalchemy import (
    String,
    ForeignKey,
    Integer,
    Float,
    JSON,
    DateTime,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


def now():
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = 'organizations'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


class Tenant:
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'), index=True)


class User(Tenant, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default='analyst')
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default='0')


class Supplier(Tenant, Base):
    __tablename__ = 'suppliers'
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default='approved')


class MaterialLot(Tenant, Base):
    __tablename__ = 'material_lots'
    __table_args__ = (UniqueConstraint('org_id', 'code'), CheckConstraint('quantity >= 0'))
    code: Mapped[str] = mapped_column(String(60))
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'), index=True)
    material: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default='available')


class ProductionBatch(Tenant, Base):
    __tablename__ = 'production_batches'
    __table_args__ = (UniqueConstraint('org_id', 'code'),)
    code: Mapped[str] = mapped_column(String(60))
    product: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default='released')
    produced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BatchMaterialUsage(Tenant, Base):
    __tablename__ = 'batch_material_usage'
    __table_args__ = (UniqueConstraint('batch_id', 'lot_id'), CheckConstraint('quantity > 0'))
    batch_id: Mapped[int] = mapped_column(ForeignKey('production_batches.id'), index=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey('material_lots.id'), index=True)
    quantity: Mapped[float] = mapped_column(Float)


class Customer(Tenant, Base):
    __tablename__ = 'customers'
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(100))


class Shipment(Tenant, Base):
    __tablename__ = 'shipments'
    __table_args__ = (Index('uq_shipments_org_code', 'org_id', 'code', unique=True),)
    code: Mapped[str] = mapped_column(String(60))
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), index=True)
    status: Mapped[str] = mapped_column(String(30), default='delivered')
    shipped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ShipmentItem(Tenant, Base):
    __tablename__ = 'shipment_items'
    __table_args__ = (UniqueConstraint('shipment_id', 'batch_id'), CheckConstraint('quantity > 0'))
    shipment_id: Mapped[int] = mapped_column(ForeignKey('shipments.id'), index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('production_batches.id'), index=True)
    quantity: Mapped[int] = mapped_column(Integer)


class Incident(Tenant, Base):
    __tablename__ = 'incidents'
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(8000))
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(30))
    lot_id: Mapped[int | None] = mapped_column(ForeignKey('material_lots.id'))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey('production_batches.id'))
    status: Mapped[str] = mapped_column(String(30), default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Investigation(Tenant, Base):
    __tablename__ = 'investigations'
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.id'), unique=True)
    status: Mapped[str] = mapped_column(String(30), default='queued')
    mode: Mapped[str] = mapped_column(String(30), default='demo')
    attempt: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvidenceDocument(Tenant, Base):
    __tablename__ = 'evidence_documents'
    name: Mapped[str] = mapped_column(String(200))
    storage_key: Mapped[str] = mapped_column(String(200))
    media_type: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(String(200000))
    sha256: Mapped[str] = mapped_column(String(64))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Inspection(Tenant, Base):
    __tablename__ = 'inspections'
    batch_id: Mapped[int] = mapped_column(ForeignKey('production_batches.id'), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('evidence_documents.id'))
    test: Mapped[str] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(30))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvidenceFinding(Tenant, Base):
    __tablename__ = 'evidence_findings'
    investigation_id: Mapped[int] = mapped_column(ForeignKey('investigations.id'), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(String(4000))
    references: Mapped[list] = mapped_column(JSON, default=list)


class AgentRun(Tenant, Base):
    __tablename__ = 'agent_runs'
    investigation_id: Mapped[int] = mapped_column(ForeignKey('investigations.id'), index=True)
    agent: Mapped[str] = mapped_column(String(100))
    attempt: Mapped[int] = mapped_column(Integer, default=1, server_default='1')
    status: Mapped[str] = mapped_column(String(30), default='running')
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentToolCall(Tenant, Base):
    __tablename__ = 'agent_tool_calls'
    run_id: Mapped[int] = mapped_column(ForeignKey('agent_runs.id'), index=True)
    tool: Mapped[str] = mapped_column(String(100))
    arguments: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)


class InvestigationEvent(Tenant, Base):
    __tablename__ = 'investigation_events'
    investigation_id: Mapped[int] = mapped_column(ForeignKey('investigations.id'), index=True)
    message: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ActionProposal(Tenant, Base):
    __tablename__ = 'action_proposals'
    investigation_id: Mapped[int] = mapped_column(ForeignKey('investigations.id'), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    justification: Mapped[str] = mapped_column(String(4000))
    target_batch_ids: Mapped[list] = mapped_column(JSON)
    evidence: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default='pending')
    revision_history: Mapped[list] = mapped_column(JSON, default=list, server_default='[]')


class Approval(Tenant, Base):
    __tablename__ = 'approvals'
    proposal_id: Mapped[int] = mapped_column(ForeignKey('action_proposals.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Tenant, Base):
    __tablename__ = 'audit_logs'
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# Install ORM write validation after all models have registered.
from backend.services import isolation  # noqa: E402,F401
