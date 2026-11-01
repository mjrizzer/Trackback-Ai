import csv
import hashlib
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4
from sqlalchemy import event
from sqlalchemy.orm import Session
from pypdf import PdfReader
from fastapi import HTTPException
from backend.config import settings
from backend.models import EvidenceDocument

UPLOADS = settings.upload_dir
MAX_SIZE = 10 * 1024 * 1024


def extract(filename, content):
    suffix = Path(filename).suffix.lower()
    if not content or len(content) > MAX_SIZE:
        raise HTTPException(422, 'File must be nonempty and at most 10 MB')
    try:
        if suffix == '.pdf':
            if not content.startswith(b'%PDF-'):
                raise ValueError('Invalid PDF signature')
            reader = PdfReader(BytesIO(content))
            if len(reader.pages) > 200:
                raise ValueError('Maximum 200 pages')
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            if not text.strip():
                raise ValueError('PDF has no extractable text; provide a text-based PDF or CSV')
            if len(text) > 200000:
                raise ValueError('Extracted text exceeds 200,000 characters; split the document')
            return text, 'application/pdf', []
        if suffix == '.csv':
            text = content.decode('utf-8-sig')
            reader = csv.DictReader(StringIO(text))
            if (
                not reader.fieldnames
                or len(set(reader.fieldnames)) != len(reader.fieldnames)
                or any(not name.strip() for name in reader.fieldnames)
            ):
                raise ValueError('CSV headers must be nonempty and unique')
            data = list(reader)
            if not data or not data[0]:
                raise ValueError('CSV requires a header and data rows')
            issues = [
                f'Row {index + 2}: missing values or inconsistent columns'
                for index, row in enumerate(data)
                if any(v is None or v == '' for v in row.values()) or None in row
            ]
            groups = {}
            for row in data:
                key = (row.get('batch_code'), row.get('test'))
                if all(key) and row.get('result'):
                    groups.setdefault(key, set()).add(row['result'].lower())
            issues += [
                f'Contradictory results for {key[0]} / {key[1]}'
                for key, results in groups.items()
                if len(results) > 1
            ]
            if len(text) > 200000:
                raise ValueError('Extracted text exceeds 200,000 characters; split the document')
            return text, 'text/csv', issues[:100]
    except Exception as error:
        raise HTTPException(422, f'Unable to extract document: {error}')
    raise HTTPException(422, 'Only PDF and UTF-8 CSV files are accepted')


def store(db, org, filename, content, incident_id=None):
    text, media, issues = extract(filename, content)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    key = f'{uuid4().hex}{Path(filename).suffix.lower()}'
    (UPLOADS / key).write_bytes(content)
    db.info.setdefault('pending_uploads', []).append(UPLOADS / key)
    doc = EvidenceDocument(
        org_id=org,
        name=Path(filename).name[:200],
        storage_key=key,
        media_type=media,
        text=text,
        sha256=hashlib.sha256(content).hexdigest(),
        incident_id=incident_id,
    )
    db.add(doc)
    db.flush()
    return doc, issues


@event.listens_for(Session, 'after_rollback')
def remove_uncommitted_uploads(session):
    for path in session.info.pop('pending_uploads', []):
        path.unlink(missing_ok=True)


@event.listens_for(Session, 'after_commit')
def preserve_committed_uploads(session):
    session.info.pop('pending_uploads', None)
