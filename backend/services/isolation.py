"""Validate organization ownership of every ORM-written foreign-key relationship."""

from sqlalchemy import event
from sqlalchemy.orm import Session
from backend.database import Base


@event.listens_for(Session, 'before_flush')
def validate_tenant_relationships(session, _context, _instances):
    tables = {mapper.local_table.name: mapper.class_ for mapper in Base.registry.mappers}
    for row in list(session.new) + list(session.dirty):
        if not hasattr(row, 'org_id'):
            continue
        state = __import__('sqlalchemy').inspect(row)
        if state.persistent and state.attrs.org_id.history.has_changes():
            raise ValueError('Organization ownership cannot be changed')
        for column in row.__table__.columns:
            for foreign in column.foreign_keys:
                table = foreign.column.table.name
                value = getattr(row, column.name)
                model = tables.get(table)
                if value is None or model is None or not hasattr(model, 'org_id'):
                    continue
                parent = session.get(model, value)
                if parent is None or parent.org_id != row.org_id:
                    raise ValueError(f'Cross-organization or missing relationship: {table}')
