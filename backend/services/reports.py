from io import BytesIO
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from backend.models import *
from backend.services.records import rows


def report(db, inv, incident):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles['Title'].textColor = colors.HexColor('#163b66')
    story = []

    def add(text, style='BodyText'):
        story.append(Paragraph(escape(str(text)).replace('\n', '<br/>'), styles[style]))
        story.append(Spacer(1, 8))

    add('TRACEBACK AI', 'Title')
    add(f'Investigation {inv.id} | {inv.mode.upper()} MODE | {inv.status}', 'Heading2')
    add(f'Incident {incident.id}: {incident.title}', 'Heading1')
    add(incident.description)
    add('Executive summary', 'Heading2')
    for agent in inv.result.get('agents', []):
        add(f'{agent["agent"]}: {agent["summary"]}')
        add('Evidence: ' + ', '.join(agent['evidence_references']))
    traced = inv.result.get('trace', {})
    for title, key in [
        ('Affected material lots', 'lots'),
        ('Affected production batches', 'batches'),
        ('Potentially affected shipments', 'shipments'),
        ('Potentially affected customers', 'customers'),
    ]:
        add(title, 'Heading2')
        add(
            ', '.join(r.get('code', r.get('name', '')) for r in traced.get(key, []))
            or 'None identified'
        )
    add('Verified evidence and gaps', 'Heading2')
    for finding in inv.result.get('evidence', {}).get('findings', []):
        add(f'{finding["kind"]}: {finding["detail"]} | Sources: {", ".join(finding["references"])}')
    for doc in inv.result.get('evidence', {}).get('documents', []):
        add(f'evidence_documents:{doc["id"]} — {doc["name"]} | SHA-256 {doc["sha256"]}')
    add('Risk and uncertainty', 'Heading2')
    add(inv.result.get('risk', {}))
    add('Timeline', 'Heading2')
    for ev in rows(db, InvestigationEvent, inv.org_id):
        if ev.investigation_id == inv.id:
            add(f'{ev.created_at.isoformat()} — {ev.message}')
    add('Recommended actions and approval history', 'Heading2')
    for p in rows(db, ActionProposal, inv.org_id):
        if p.investigation_id == inv.id:
            add(f'{p.kind}: {p.justification} | Status: {p.status} | Sources: {p.evidence}')
            for revision in p.revision_history:
                add(
                    f'Revision {revision["at"]} by user {revision["user_id"]}: {revision["previous"]} -> {revision["revised"]}'
                )
            for a in rows(db, Approval, inv.org_id):
                if a.proposal_id == p.id:
                    add(
                        f'{a.created_at.isoformat()} | Reviewer {a.user_id}: {a.decision} — {a.comment}'
                    )
    add(
        'Internal investigation support only. Approved actions affect simulated internal records. No external notification or recall is initiated.'
    )
    SimpleDocTemplate(
        buffer, title=f'TraceBack investigation {inv.id}', author='TraceBack AI'
    ).build(story)
    return buffer.getvalue()
