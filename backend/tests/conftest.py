import os
import tempfile
from pathlib import Path
import pytest

TEST_DIR = tempfile.TemporaryDirectory(prefix='traceback-tests-')
os.environ['DATABASE_URL'] = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///' + str(
    Path(TEST_DIR.name) / 'test.db'
)
os.environ['AI_MODE'] = 'demo'
os.environ['AUTH_RATE_LIMIT'] = '1000'
os.environ['UPLOAD_DIR'] = str(Path(TEST_DIR.name) / 'uploads')
os.environ['DEMO_DATA_DIR'] = str(Path(TEST_DIR.name) / 'demo_data')

from backend.database import Base, engine
from backend.seed import seed
from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope='session')
def client():
    Base.metadata.create_all(engine)
    seed()
    with TestClient(app, headers={'X-CSRF-Protection': '1'}) as test:
        yield test
    engine.dispose()


@pytest.fixture
def auth(client):
    result = client.post(
        '/api/auth/login', json={'email': 'admin@novafoods.demo', 'password': 'NovaFoods!2026'}
    )
    return {'Authorization': 'Bearer ' + result.json()['access_token']}
