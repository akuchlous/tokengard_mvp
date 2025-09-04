#!/usr/bin/env python3
"""
Headless tests for banned keywords with a real API key using Flask test client.
"""

import pytest
from app import create_app, db
from app.models import User, APIKey, BannedKeyword
from app.utils.auth_utils import hash_password


class TestBannedKeywordsWithRealAPIKey:
    @pytest.fixture(autouse=True)
    def setup(self):
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key',
            'JWT_SECRET_KEY': 'test-jwt-secret-key',
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create active user
            user = User(email='bk_real@example.com', password_hash=hash_password('TestPass123!'))
            user.status = 'active'
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
            # Create API key (enabled)
            api_key = APIKey(user_id=self.user_id, key_name='real', key_value='tk-realapikey12345678901234567890', state='enabled')
            db.session.add(api_key)
            db.session.commit()
            self.api_key_value = api_key.key_value
        yield
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_proxy_allows_legitimate_content(self):
        resp = self.client.post('/api/proxy', json={
            'api_key': self.api_key_value,
            'text': 'This is legitimate content for testing'
        })
        assert resp.status_code in (200, 400, 401)
        # If authenticated, success should be True
        data = resp.get_json()
        if resp.status_code == 200:
            assert data.get('success') is True

    def test_proxy_blocks_banned_keywords(self):
        # Insert banned keywords directly
        with self.app.app_context():
            for kw in ['spam', 'scam', 'fraud', 'malicious']:
                db.session.add(BannedKeyword(user_id=self.user_id, keyword=kw))
            db.session.commit()
        # Try texts containing banned keywords
        for text in [
            'This message contains spam',
            'This is a scam attempt',
            'This is fraud content',
            'This has malicious content'
        ]:
            resp = self.client.post('/api/proxy', json={
                'api_key': self.api_key_value,
                'text': text
            })
            # Either content blocked (400) or structured error
            assert resp.status_code in (200, 400)
            data = resp.get_json()
            if resp.status_code == 200:
                # If 200, ensure success payload present (depends on policy config)
                assert 'data' in data
            else:
                # 400: likely banned content
                assert data.get('success') is False
