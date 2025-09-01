"""
Unit tests for banned keywords functionality.

This module tests the BannedKeyword model and related functionality.
"""

import pytest
import json
from datetime import datetime
from app.models import BannedKeyword


class TestBannedKeywordModel:
    """Test BannedKeyword model functionality."""
    
    def test_create_banned_keyword(self, db_session, test_user):
        """Test creating a banned keyword."""
        keyword = BannedKeyword(
            user_id=test_user.id,
            keyword='spam'
        )
        db_session.add(keyword)
        db_session.commit()
        
        assert keyword.id is not None
        assert keyword.user_id == test_user.id
        assert keyword.keyword == 'spam'
        assert keyword.created_at is not None
    
    def test_get_user_keywords(self, db_session, test_user):
        """Test getting keywords for a user."""
        # Add some keywords
        keywords = ['spam', 'scam', 'fraud']
        for keyword_text in keywords:
            keyword = BannedKeyword(
                user_id=test_user.id,
                keyword=keyword_text
            )
            db_session.add(keyword)
        db_session.commit()
        
        # Get keywords
        user_keywords = BannedKeyword.get_user_keywords(test_user.id)
        assert len(user_keywords) == 3
        assert all(kw.keyword in keywords for kw in user_keywords)
    
    def test_add_keyword_method(self, db_session, test_user):
        """Test the add_keyword class method."""
        # Add a keyword
        keyword, error = BannedKeyword.add_keyword(test_user.id, 'spam')
        assert keyword is not None
        assert error is None
        assert keyword.keyword == 'spam'
        
        # Try to add duplicate
        keyword2, error2 = BannedKeyword.add_keyword(test_user.id, 'spam')
        assert keyword2 is None
        assert error2 == "Keyword already exists"
    
    def test_remove_keyword_method(self, db_session, test_user):
        """Test the remove_keyword class method."""
        # Add a keyword
        keyword = BannedKeyword(
            user_id=test_user.id,
            keyword='spam'
        )
        db_session.add(keyword)
        db_session.commit()
        keyword_id = keyword.id
        
        # Remove the keyword
        success, error = BannedKeyword.remove_keyword(test_user.id, keyword_id)
        assert success is True
        assert error is None
        
        # Try to remove non-existent keyword
        success2, error2 = BannedKeyword.remove_keyword(test_user.id, 999)
        assert success2 is False
        assert error2 == "Keyword not found"
    
    def test_check_banned_method(self, db_session, test_user):
        """Test the check_banned class method."""
        # Add banned keywords
        BannedKeyword.add_keyword(test_user.id, 'spam')
        BannedKeyword.add_keyword(test_user.id, 'scam')
        
        # Test banned content
        is_banned, banned_keyword = BannedKeyword.check_banned(test_user.id, 'This is spam content')
        assert is_banned is True
        assert banned_keyword == 'spam'
        
        # Test clean content
        is_banned2, banned_keyword2 = BannedKeyword.check_banned(test_user.id, 'This is clean content')
        assert is_banned2 is False
        assert banned_keyword2 is None
        
        # Test case insensitive
        is_banned3, banned_keyword3 = BannedKeyword.check_banned(test_user.id, 'This is SPAM content')
        assert is_banned3 is True
        assert banned_keyword3 == 'spam'
    
    def test_populate_default_keywords(self, db_session, test_user):
        """Test populating default keywords."""
        added_count = BannedKeyword.populate_default_keywords(test_user.id)
        assert added_count == 21
        
        # Check that keywords were added
        user_keywords = BannedKeyword.get_user_keywords(test_user.id)
        assert len(user_keywords) == 21
        
        # Check some expected keywords
        keyword_texts = [kw.keyword for kw in user_keywords]
        assert 'spam' in keyword_texts
        assert 'scam' in keyword_texts
        assert 'fraud' in keyword_texts
    
    def test_to_dict_method(self, db_session, test_user):
        """Test the to_dict method."""
        keyword = BannedKeyword(
            user_id=test_user.id,
            keyword='spam'
        )
        db_session.add(keyword)
        db_session.commit()
        
        keyword_dict = keyword.to_dict()
        assert keyword_dict['id'] == keyword.id
        assert keyword_dict['user_id'] == test_user.id
        assert keyword_dict['keyword'] == 'spam'
        assert 'created_at' in keyword_dict
        assert 'updated_at' in keyword_dict


class TestBannedKeywordsAPI:
    """Test banned keywords API endpoints."""
    
    def test_get_banned_keywords_unauthorized(self, client):
        """Test getting banned keywords without authentication."""
        response = client.get('/api/banned-keywords')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_get_banned_keywords_authorized(self, client, db_session, test_user):
        """Test getting banned keywords with authentication."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Add some keywords
        BannedKeyword.add_keyword(test_user.id, 'spam')
        BannedKeyword.add_keyword(test_user.id, 'scam')
        
        response = client.get('/api/banned-keywords')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'keywords' in data
        assert len(data['keywords']) == 2
    
    def test_add_banned_keyword_unauthorized(self, client):
        """Test adding banned keyword without authentication."""
        response = client.post('/api/banned-keywords', 
                             json={'keyword': 'spam'})
        assert response.status_code == 401
    
    def test_add_banned_keyword_authorized(self, client, test_user):
        """Test adding banned keyword with authentication."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        response = client.post('/api/banned-keywords', 
                             json={'keyword': 'spam'})
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert 'keyword' in data
        assert data['keyword']['keyword'] == 'spam'
    
    def test_add_banned_keyword_duplicate(self, client, db_session, test_user):
        """Test adding duplicate banned keyword."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Add keyword first time
        response1 = client.post('/api/banned-keywords', 
                              json={'keyword': 'spam'})
        assert response1.status_code == 201
        
        # Try to add same keyword again
        response2 = client.post('/api/banned-keywords', 
                              json={'keyword': 'spam'})
        assert response2.status_code == 400
        data = json.loads(response2.data)
        assert 'error' in data
    
    def test_add_banned_keyword_empty(self, client, test_user):
        """Test adding empty banned keyword."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        response = client.post('/api/banned-keywords', 
                             json={'keyword': ''})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_delete_banned_keyword_unauthorized(self, client):
        """Test deleting banned keyword without authentication."""
        response = client.delete('/api/banned-keywords/1')
        assert response.status_code == 401
    
    def test_delete_banned_keyword_authorized(self, client, db_session, test_user):
        """Test deleting banned keyword with authentication."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Add a keyword
        keyword, _ = BannedKeyword.add_keyword(test_user.id, 'spam')
        
        response = client.delete(f'/api/banned-keywords/{keyword.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_delete_banned_keyword_not_found(self, client, db_session, test_user):
        """Test deleting non-existent banned keyword."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        response = client.delete('/api/banned-keywords/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_populate_default_keywords_unauthorized(self, client):
        """Test populating default keywords without authentication."""
        response = client.post('/api/banned-keywords/populate-defaults')
        assert response.status_code == 401
    
    def test_populate_default_keywords_authorized(self, client, db_session, test_user):
        """Test populating default keywords with authentication."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        response = client.post('/api/banned-keywords/populate-defaults')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'added_count' in data
        assert data['added_count'] == 21


class TestProxyEndpointWithBannedKeywords:
    """Test proxy endpoint with banned keywords functionality."""
    
    def test_proxy_with_banned_keyword(self, client, db_session, test_user, test_api_key):
        """Test proxy endpoint blocking content with banned keywords."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Add a banned keyword
        BannedKeyword.add_keyword(test_user.id, 'spam')
        
        # Test with banned content
        response = client.post('/api/proxy', 
                             json={
                                 'api_key': test_api_key.key_value,
                                 'text': 'This message contains spam content'
                             })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'content_error'
        assert 'banned keyword' in data['message']
        assert data['banned_keyword'] == 'spam'
    
    def test_proxy_with_clean_content(self, client, db_session, test_user, test_api_key):
        """Test proxy endpoint allowing clean content."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Add a banned keyword
        BannedKeyword.add_keyword(test_user.id, 'spam')
        
        # Test with clean content
        response = client.post('/api/proxy', 
                             json={
                                 'api_key': test_api_key.key_value,
                                 'text': 'This is clean content without banned words'
                             })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'key_pass'
        assert 'external_check' in data
    
    def test_proxy_with_external_api_blocking(self, client, db_session, test_user, test_api_key):
        """Test proxy endpoint with external API blocking."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Test with very long content (should be blocked by external API)
        long_text = 'word ' * 300  # 1200+ characters
        response = client.post('/api/proxy', 
                             json={
                                 'api_key': test_api_key.key_value,
                                 'text': long_text
                             })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'content_error'
        assert 'external service' in data['message']
    
    def test_proxy_with_repetitive_content(self, client, db_session, test_user, test_api_key):
        """Test proxy endpoint with repetitive content."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Test with repetitive content (should be blocked by external API)
        repetitive_text = 'spam spam spam spam spam spam spam spam spam spam spam spam'
        response = client.post('/api/proxy', 
                             json={
                                 'api_key': test_api_key.key_value,
                                 'text': repetitive_text
                             })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'content_error'
        assert 'external service' in data['message']
    
    def test_proxy_without_text(self, client, db_session, test_user, test_api_key):
        """Test proxy endpoint without text content."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        # Add a banned keyword
        BannedKeyword.add_keyword(test_user.id, 'spam')
        
        # Test without text
        response = client.post('/api/proxy', 
                             json={
                                 'api_key': test_api_key.key_value
                             })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'key_pass'
        assert data['text_length'] == 0


class TestBannedKeywordsRoutes:
    """Test banned keywords page routes."""
    
    def test_banned_keywords_page_unauthorized(self, client):
        """Test accessing banned keywords page without authentication."""
        response = client.get('/banned_keywords/test-user-123')
        assert response.status_code == 401
    
    def test_banned_keywords_page_authorized(self, client, db_session, test_user):
        """Test accessing banned keywords page with authentication."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        response = client.get(f'/banned_keywords/{test_user.user_id}')
        assert response.status_code == 200
        assert b'Banned Keywords Management' in response.data
    
    def test_banned_keywords_page_wrong_user(self, client, db_session, test_user):
        """Test accessing banned keywords page for different user."""
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
        
        response = client.get('/banned_keywords/different-user-123')
        assert response.status_code == 403
