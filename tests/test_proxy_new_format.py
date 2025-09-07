import json
import time

from app import create_app
from app.models import db, User, APIKey, ProxyLog
from app.utils.auth_utils import hash_password


def _setup_app():
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET_KEY': 'test-jwt-secret-key',
    }
    app = create_app(test_config)
    client = app.test_client()
    with app.app_context():
        db.create_all()
        user = User(email='format@example.com', password_hash=hash_password('TestPass123!'))
        user.status = 'active'
        db.session.add(user)
        db.session.commit()
        # Create one enabled key
        api_key = APIKey(user_id=user.id, key_name='key_ok', key_value='tk-abcdefghijklmnopqrstuvwxyz123456', state='enabled')
        db.session.add(api_key)
        db.session.commit()
        # Return only primitive key value to avoid DetachedInstanceError outside context
        return app, client, user, api_key.key_value


def test_proxy_success_openai_shape_with_token_id():
    app, client, user, api_key_value = _setup_app()
    payload = {
        'api_key': api_key_value,
        'text': 'Hello, OpenAI-like response!',
        'model': 'gpt-4o',
    }
    resp = client.post('/api/proxy', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    # OpenAI-like shape
    assert isinstance(data.get('id'), str)
    assert data.get('object') == 'chat.completion'
    assert isinstance(data.get('created'), int)
    assert data.get('model') == payload['model']
    assert isinstance(data.get('choices'), list) and data['choices']
    assert 'usage' in data
    # Extra field
    assert 'proxy_id' in data and isinstance(data['proxy_id'], str)


def test_proxy_policy_error_openai_error_with_token_id():
    app, client, user, api_key_value = _setup_app()
    # Use invalid key
    payload = {
        'api_key': 'tk-invalid-key',
        'text': 'Hello'
    }
    resp = client.post('/api/proxy', json=payload)
    assert resp.status_code == 401
    data = resp.get_json()
    # Error reason in choices[0].message.content for standardized OpenAI-like envelope
    assert 'choices' in data
    assert 'api key' in data['choices'][0]['message']['content'].lower()
    assert 'proxy_id' in data


def test_get_proxy_log_by_id_requires_api_key_and_authorized():
    app, client, user, api_key_value = _setup_app()
    # Create a proxy call to generate a log
    resp = client.post('/api/proxy', json={'api_key': api_key_value, 'text': 'log me'})
    assert resp.status_code in (200, 400)
    with app.app_context():
        log = ProxyLog.query.order_by(ProxyLog.id.desc()).first()
        assert log is not None
    # No API key -> 401
    r1 = client.get(f'/api/logs/{log.id}')
    assert r1.status_code == 401
    # Wrong key -> 401
    r2 = client.get(f'/api/logs/{log.id}?api_key=tk-not-a-real-key')
    assert r2.status_code == 401
    # Correct key but ensure ownership enforced
    r3 = client.get(f'/api/logs/{log.id}?api_key={api_key_value}')
    assert r3.status_code == 200
    data = r3.get_json()
    assert data.get('id') == log.id
    assert data.get('api_key_value') == log.api_key_value


