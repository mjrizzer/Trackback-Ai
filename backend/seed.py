from datetime import timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from sqlalchemy import select
from backend.database import SessionLocal
from backend.config import settings
from backend.models import *
from backend.security import passwords
from backend.services.documents import store


def seed():
    with SessionLocal() as db:
        if db.scalar(select(Organization).where(Organization.name == 'NovaFoods Manufacturing')):
            print('NovaFoods already seeded; no changes made.')
            return
        org = Organization(name='NovaFoods Manufacturing')
        db.add(org)
        db.flush()
        oid = org.id

        def add(model, **kwargs):
            row = model(org_id=oid, **kwargs)
            db.add(row)
            db.flush()
            return row

        for role, name in [
            ('admin', 'Alex Morgan'),
            ('analyst', 'Priya Shah'),
            ('reviewer', 'Sam Rivera'),
        ]:
            add(
                User,
                name=name,
                email=f'{role}@novafoods.demo',
                password_hash=passwords.hash('NovaFoods!2026'),
                role=role,
            )
        suppliers = [
            add(Supplier, name=name)
            for name in [
                'GreenField Ingredients',
                'Summit Grain Co.',
                'PureSource Dairy',
                'Coastal Oils',
                'Harvest Botanicals',
                'Apex Packaging',
                'Valley Sweeteners',
                'Terra Spices',
            ]
        ]
        # Exactly 25 lots, including the requested RM-042.
        lots = [
            add(
                MaterialLot,
                code=f'RM-{n:03}',
                supplier_id=suppliers[i % 8].id,
                material=['Oat flour', 'Milk powder', 'Sunflower oil', 'Cocoa', 'Cane sugar'][
                    i % 5
                ],
                quantity=2000 + i * 50,
            )
            for i, n in enumerate(list(range(18, 42)) + [42])
        ]
        batches = [
            add(
                ProductionBatch,
                code=f'PB-{i + 1:03}',
                product=['Cocoa oat bars', 'Breakfast granola', 'Protein bites'][i % 3],
                quantity=2400,
                produced_at=now() - timedelta(days=30 - i % 28),
            )
            for i in range(60)
        ]
        for i, batch in enumerate(batches):
            lot = lots[-1] if i < 4 else lots[(i - 4) % 24]
            add(BatchMaterialUsage, batch_id=batch.id, lot_id=lot.id, quantity=120)
        customers = [
            add(
                Customer,
                name=f'{["Metro", "Fresh", "Urban", "North", "Prime"][i % 5]} Market {i + 1:02}',
                region=['West', 'South', 'North', 'East'][i % 4],
            )
            for i in range(30)
        ]
        for i in range(100):
            shipment = add(
                Shipment,
                code=f'SHP-{i + 1:04}',
                customer_id=customers[i % 30].id,
                shipped_at=now() - timedelta(days=20 - i % 18),
            )
            add(ShipmentItem, shipment_id=shipment.id, batch_id=batches[i % 60].id, quantity=600)
        scenario_a = add(
            Incident,
            title='Supplier alert · possible contamination of RM-042',
            description='GreenField Ingredients reports possible contamination in RM-042. Trace all consumed batches and downstream shipments. Verify inspections before any containment decision.',
            category='contamination',
            severity='critical',
            lot_id=lots[-1].id,
            created_at=now() - timedelta(days=2),
        )
        scenario_b = add(
            Incident,
            title='Conflicting quality records · PB-012',
            description='Two source inspection certificates for PB-012 disagree on microbiology results. Compare timestamps and retain both sources for verification.',
            category='quality',
            severity='high',
            batch_id=batches[11].id,
            created_at=now() - timedelta(days=1),
        )
        add(
            Incident,
            title='Shipment documentation review',
            description='Customer requested verification of delivery documentation for SHP-0050.',
            category='shipment',
            severity='low',
            created_at=now() - timedelta(days=5),
        )
        demo_dir = settings.demo_data_dir
        demo_dir.mkdir(exist_ok=True)
        alert = b'lot_code,supplier,notice,status\nRM-042,GreenField Ingredients,Possible contamination pending laboratory confirmation,unverified\n'
        (demo_dir / 'supplier-alert.csv').write_bytes(alert)
        store(db, oid, 'supplier-alert.csv', alert, scenario_a.id)
        for i, batch in enumerate(batches):
            if i == 2:
                continue  # PB-003 intentionally has no inspection.
            content = f'batch_code,test,result,timestamp\n{batch.code},microbiology,pass,{batch.produced_at.isoformat()}\n'.encode()
            doc, _ = store(
                db, oid, f'inspection-{batch.code}.csv', content, scenario_b.id if i == 11 else None
            )
            add(
                Inspection,
                batch_id=batch.id,
                document_id=doc.id,
                test='microbiology',
                result='pass',
                observed_at=batch.produced_at,
            )
            if i == 11:
                pdf = BytesIO()
                page = canvas.Canvas(pdf)
                page.drawString(60, 780, 'NovaFoods Manufacturing - External Quality Certificate')
                page.drawString(
                    60, 750, f'{batch.code} | microbiology | FAIL | {batch.produced_at.isoformat()}'
                )
                page.drawString(60, 720, 'Conflicting certificate; source verification required.')
                page.save()
                (demo_dir / 'PB-012-conflicting-certificate.pdf').write_bytes(pdf.getvalue())
                conflicting, _ = store(
                    db, oid, 'PB-012-conflicting-certificate.pdf', pdf.getvalue(), scenario_b.id
                )
                add(
                    Inspection,
                    batch_id=batch.id,
                    document_id=conflicting.id,
                    test='microbiology',
                    result='fail',
                    observed_at=batch.produced_at + timedelta(hours=2),
                )
        audit = AuditLog(
            org_id=oid,
            action='demo_seeded',
            detail='Fictional NovaFoods dataset; PB-003 inspection missing; PB-012 conflicting certificates; RM-042 used by PB-001..004.',
        )
        db.add(audit)
        db.commit()
        print(
            'Seeded NovaFoods: 8 suppliers, 25 lots, 60 batches, 30 customers, 100 shipments. Login admin@novafoods.demo / NovaFoods!2026'
        )


if __name__ == '__main__':
    seed()
