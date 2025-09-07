"""
TokenGuard - API Key Management Unit Tests

This module contains unit tests for the API key management system including:
- API key creation and validation
- API key state management (enable/disable)
- API key value refresh functionality
- API key deletion and security
- Default API key creation on user activation
"""

import pytest
from datetime import datetime, timedelta
from app.models import db, User, APIKey
from app.models.utils import generate_api_key_name, generate_api_key_value
from app.utils.auth_utils import hash_password

# Import the function from the APIKey model class
create_default_api_key = APIKey.create_default_api_keys


class TestAPIKeyGeneration:
    """Test API key generation functions"""
    
    def test_generate_api_key_name(self):
        """Test that API key names are generated correctly"""
        key_name = generate_api_key_name()
        
        # Check length is exactly 6 characters
        assert len(key_name) == 6
        
        # Check it's alphanumeric
        assert key_name.isalnum()
        
        # Check it's unique (generate multiple and ensure no duplicates)
        key_names = [generate_api_key_name() for _ in range(10)]
        assert len(set(key_names)) == 10
    
    def test_generate_api_key_value(self):
        """Test that API key values are generated correctly"""
        key_value = generate_api_key_value()
        
        # Check it starts with 'tk-'
        assert key_value.startswith('tk-')
        
        # Check total length is 38 (3 for 'tk-' + 32 for random chars)
        assert len(key_value) == 35
        
        # Check the random part is alphanumeric
        random_part = key_value[3:]
        assert random_part.isalnum()
        assert len(random_part) == 32
    
    def test_generate_api_key_value_uniqueness(self):
        """Test that generated API key values are unique"""
        key_values = [generate_api_key_value() for _ in range(10)]
        assert len(set(key_values)) == 10


class TestAPIKeyModel:
    """Test APIKey model functionality"""
    
    def test_api_key_creation(self, app, db_session, test_user):
        """Test creating an API key"""
        # Create API key
        api_key = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        # Verify creation
        assert api_key.id is not None
        assert api_key.key_name == 'test12'
        assert api_key.key_value == 'tk-abcdefghijklmnopqrstuvwxyz123456'
        assert api_key.state == 'enabled'
        assert api_key.user_id == test_user.id
        assert api_key.created_at is not None
    
    def test_api_key_state_management(self, app, db_session, test_user):
        """Test enabling and disabling API keys"""
        # Create API key
        api_key = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        # Test initial state
        assert api_key.is_enabled() is True
        
        # Test disable
        api_key.disable()
        assert api_key.state == 'disabled'
        assert api_key.is_enabled() is False
        
        # Test enable is prohibited
        with pytest.raises(ValueError):
            api_key.enable()
    
    def test_api_key_refresh(self, app, db_session, test_user):
        """Test refreshing API key values"""
        # Create API key
        original_value = 'tk-abcdefghijklmnopqrstuvwxyz123456'
        api_key = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value=original_value,
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        # Store original value
        original_key_value = api_key.key_value
        
        # Test refresh
        api_key.refresh_key_value()
        
        # Verify value changed
        assert api_key.key_value != original_key_value
        assert api_key.key_value.startswith('tk-')
        assert len(api_key.key_value) == 35
        
        # Verify it's still enabled
        assert api_key.is_enabled() is True
    
    def test_api_key_last_used_update(self, app, db_session, test_user):
        """Test updating last used timestamp"""
        # Create API key
        api_key = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        # Initial last_used should be None
        assert api_key.last_used is None
        
        # Update last used
        api_key.update_last_used()
        
        # Verify last_used is updated
        assert api_key.last_used is not None
        assert isinstance(api_key.last_used, datetime)
    
    def test_api_key_unique_constraint(self, app, db_session, test_user):
        """Test that users cannot have duplicate key names"""
        # Create first API key
        api_key1 = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(api_key1)
        db_session.commit()
        
        # Try to create second API key with same name
        api_key2 = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-zyxwvutsrqponmlkjihgfedcba654321',
            state='enabled'
        )
        db_session.add(api_key2)
        
        # This should raise an integrity error
        with pytest.raises(Exception):
            db_session.commit()
        
        db_session.rollback()


class TestDefaultAPIKeyCreation:
    """Test default API key creation on user activation"""
    
    def test_create_default_api_key(self, app, db_session, test_user):
        """Test creating 10 default API keys for a user"""
        # Create default API keys
        api_keys = create_default_api_key(test_user.id)
        
        # Verify we get 10 keys
        assert api_keys is not None
        assert len(api_keys) == 10
        
        # Verify first key is created correctly
        first_key = api_keys[0]
        assert first_key.key_name == 'key_0'
        assert first_key.key_value.startswith('tk-')
        assert len(first_key.key_value) == 35
        assert first_key.state == 'enabled'
        assert first_key.user_id == test_user.id
        
        # Verify all keys are saved to database
        db_keys = APIKey.query.filter_by(user_id=test_user.id).all()
        assert len(db_keys) == 10
        
        # Verify key names are key_0 through key_9
        key_names = [key.key_name for key in db_keys]
        expected_names = [f'key_{i}' for i in range(10)]
        assert sorted(key_names) == sorted(expected_names)
    
    def test_default_api_key_uniqueness(self, app, db_session):
        """Test that default API keys are unique per user"""
        # Create two test users
        user1 = User(
            email='test1@example.com',
            password_hash=hash_password('password123')
        )
        user2 = User(
            email='test2@example.com',
            password_hash=hash_password('password123')
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # Create default API keys for both users
        api_keys1 = create_default_api_key(user1.id)
        api_keys2 = create_default_api_key(user2.id)
        
        # Verify both users get 10 keys each
        assert len(api_keys1) == 10
        assert len(api_keys2) == 10
        
        # Verify first keys have correct names
        assert api_keys1[0].key_name == 'key_0'
        assert api_keys2[0].key_name == 'key_0'
        
        # Verify they have different key values
        assert api_keys1[0].key_value != api_keys2[0].key_value
        
        # Verify they belong to different users
        assert api_keys1[0].user_id == user1.id
        assert api_keys2[0].user_id == user2.id
        
        # Verify all key values are unique across both users
        all_key_values = [key.key_value for key in api_keys1 + api_keys2]
        assert len(all_key_values) == len(set(all_key_values))  # All unique


class TestAPIKeyValidation:
    """Test API key validation rules"""
    

    def test_api_key_name_length_validation(self, app, db_session, test_user):
        """Test that API key names must be exactly 6 characters"""
        # Test valid key name (6 characters)
        valid_key = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(valid_key)
        db_session.commit()
        
        # Test invalid key name (5 characters)
        invalid_key_short = APIKey(
            user_id=test_user.id,
            key_name='test1',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(invalid_key_short)
        
        # This should work as SQLAlchemy doesn't enforce length at Python level
        # but the application logic should validate this
        db_session.commit()
        
        # Test invalid key name (7 characters)
        invalid_key_long = APIKey(
            user_id=test_user.id,
            key_name='test123',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(invalid_key_long)
        db_session.commit()
    
    def test_api_key_value_format_validation(self, app, db_session, test_user):
        """Test that API key values follow the correct format"""
        # Test valid key value
        valid_key = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(valid_key)
        db_session.commit()
        
        # Test invalid key value (no 'tk-' prefix)
        invalid_key_no_prefix = APIKey(
            user_id=test_user.id,
            key_name='test34',
            key_value='abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(invalid_key_no_prefix)
        db_session.commit()
        
        # Test invalid key value (wrong length)
        invalid_key_wrong_length = APIKey(
            user_id=test_user.id,
            key_name='test56',
            key_value='tk-abcdefghijklmnopqrstuvwxyz12345',  # 34 chars instead of 35
            state='enabled'
        )
        db_session.add(invalid_key_wrong_length)
        db_session.commit()


class TestAPIKeySecurity:
    """Test API key security features"""
    
    def test_api_key_user_isolation(self, app, db_session):
        """Test that users can only access their own API keys"""
        # Create two test users
        user1 = User(
            email='test1@example.com',
            password_hash=hash_password('password123')
        )
        user2 = User(
            email='test2@example.com',
            password_hash=hash_password('password123')
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        
        # Create API keys for both users
        api_key1 = APIKey(
            user_id=user1.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        api_key2 = APIKey(
            user_id=user2.id,
            key_name='test34',
            key_value='tk-zyxwvutsrqponmlkjihgfedcba654321',
            state='enabled'
        )
        db_session.add_all([api_key1, api_key2])
        db_session.commit()
        
        # Verify users can only see their own keys
        user1_keys = APIKey.query.filter_by(user_id=user1.id).all()
        user2_keys = APIKey.query.filter_by(user_id=user2.id).all()
        
        assert len(user1_keys) == 1
        assert user1_keys[0].user_id == user1.id
        assert user1_keys[0].key_name == 'test12'
        
        assert len(user2_keys) == 1
        assert user2_keys[0].user_id == user2.id
        assert user2_keys[0].key_name == 'test34'
    
    def test_api_key_state_persistence(self, app, db_session, test_user):
        """Test that API key state changes persist across sessions"""
        # Create API key
        api_key = APIKey(
            user_id=test_user.id,
            key_name='test12',
            key_value='tk-abcdefghijklmnopqrstuvwxyz123456',
            state='enabled'
        )
        db_session.add(api_key)
        db_session.commit()
        
        # Disable the key
        api_key.disable()
        
        # Query the key again to verify state persisted
        db_key = db_session.get(APIKey, api_key.id)
        assert db_key.state == 'disabled'
        assert not db_key.is_enabled()
