import os
import tempfile
import uuid

db_fd, db_path = tempfile.mkstemp(suffix='.db')
os.close(db_fd)
os.environ['DATABASE_URL'] = db_path
os.environ['SECRET_KEY'] = 'test_secret_key'
os.environ['API_KEY'] = 'mi_super_clave_secreta'
os.environ['ORIGEN_PERMITIDO'] = 'http://localhost:5000'
os.environ['OPENWEATHER_API_KEY'] = ''
os.environ['NEWS_API_KEY'] = ''

import pytest
from app import app as _app


@pytest.fixture(scope='session')
def app():
    _app.config['TESTING'] = True
    yield _app


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture
def api_key():
    return 'mi_super_clave_secreta'


@pytest.fixture
def auth_data(client):
    uid = str(uuid.uuid4())[:8]
    resp = client.post('/api/register', json={
        'username': f'testuser_{uid}',
        'email': f'test_{uid}@test.com',
        'password': 'TestPass123'
    })
    assert resp.status_code == 201, f"Register failed: {resp.get_json()}"
    data = resp.get_json()
    return {
        'access_token': data['access_token'],
        'refresh_token': data['refresh_token'],
        'user': data['user']
    }


@pytest.fixture
def auth_headers(auth_data, api_key):
    return {
        'Authorization': f"Bearer {auth_data['access_token']}",
        'X-API-Key': api_key
    }
