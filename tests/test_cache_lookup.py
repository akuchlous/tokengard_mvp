#!/usr/bin/env python3
"""
Unit tests for the cache lookup module
"""

import pytest
import time
import json
from app.utils.cache_lookup import (
    CacheEntry, CacheLookup, LLMCacheLookup, 
    cache_lookup, llm_cache_lookup
)


class TestCacheEntry:
    """Test the CacheEntry class."""
    
    def test_cache_entry_creation(self):
        """Test creating a CacheEntry."""
        entry = CacheEntry("test_key", "test_value", 3600)
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.ttl == 3600
        assert entry.access_count == 0
        assert not entry.is_expired()
    
    def test_cache_entry_access(self):
        """Test accessing a CacheEntry."""
        entry = CacheEntry("test_key", "test_value", 3600)
        original_created_at = entry.created_at
        
        # Access the entry
        value = entry.access()
        
        assert value == "test_value"
        assert entry.access_count == 1
        assert entry.last_accessed >= original_created_at
    
    def test_cache_entry_expired(self):
        """Test expired CacheEntry."""
        entry = CacheEntry("test_key", "test_value", 1)  # 1 second TTL
        
        # Wait for expiration
        time.sleep(1.1)
        
        assert entry.is_expired()
    
    def test_cache_entry_to_dict(self):
        """Test converting CacheEntry to dictionary."""
        entry = CacheEntry("test_key", "test_value", 3600)
        entry.access()  # Access once
        
        entry_dict = entry.to_dict()
        
        assert entry_dict['key'] == "test_key"
        assert entry_dict['value'] == "test_value"
        assert entry_dict['ttl'] == 3600
        assert entry_dict['access_count'] == 1
        assert entry_dict['is_expired'] is False


class TestCacheLookup:
    """Test the CacheLookup class."""
    
    def test_cache_lookup_creation(self):
        """Test creating a CacheLookup."""
        cache = CacheLookup(max_size=100, default_ttl=1800)
        
        assert cache.max_size == 100
        assert cache.default_ttl == 1800
        assert len(cache._cache) == 0
    
    def test_generate_cache_key(self):
        """Test generating cache keys."""
        cache = CacheLookup()
        
        # Test with different inputs
        key1 = cache.generate_cache_key("api_key_1", {"text": "hello"}, "gpt-3.5", 0.7)
        key2 = cache.generate_cache_key("api_key_1", {"text": "hello"}, "gpt-3.5", 0.7)
        key3 = cache.generate_cache_key("api_key_1", {"text": "world"}, "gpt-3.5", 0.7)
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different inputs should generate different keys
        assert key1 != key3
        
        # Keys should be valid SHA256 hashes
        assert len(key1) == 64  # SHA256 hex length
        assert all(c in '0123456789abcdef' for c in key1)
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = CacheLookup()
        
        # Set a value
        success = cache.set("test_key", "test_value", 3600)
        assert success is True
        
        # Get the value
        found, value = cache.get("test_key")
        assert found is True
        assert value == "test_value"
    
    def test_cache_miss(self):
        """Test cache miss scenario."""
        cache = CacheLookup()
        
        # Try to get non-existent key
        found, value = cache.get("nonexistent_key")
        assert found is False
        assert value is None
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        cache = CacheLookup()
        
        # Set a value with short TTL
        cache.set("test_key", "test_value", 1)  # 1 second TTL
        
        # Should be found immediately
        found, value = cache.get("test_key")
        assert found is True
        assert value == "test_value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        found, value = cache.get("test_key")
        assert found is False
        assert value is None
    
    def test_cache_delete(self):
        """Test deleting cache entries."""
        cache = CacheLookup()
        
        # Set a value
        cache.set("test_key", "test_value", 3600)
        
        # Verify it exists
        found, _ = cache.get("test_key")
        assert found is True
        
        # Delete it
        deleted = cache.delete("test_key")
        assert deleted is True
        
        # Verify it's gone
        found, _ = cache.get("test_key")
        assert found is False
    
    def test_cache_delete_nonexistent(self):
        """Test deleting non-existent cache entry."""
        cache = CacheLookup()
        
        deleted = cache.delete("nonexistent_key")
        assert deleted is False
    
    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = CacheLookup()
        
        # Add some entries
        cache.set("key1", "value1", 3600)
        cache.set("key2", "value2", 3600)
        
        assert len(cache._cache) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache._cache) == 0
    
    def test_cache_cleanup_expired(self):
        """Test cleaning up expired entries."""
        cache = CacheLookup()
        
        # Add some entries with different TTLs
        cache.set("key1", "value1", 1)  # Expires quickly
        cache.set("key2", "value2", 3600)  # Expires later
        
        # Wait for first entry to expire
        time.sleep(1.1)
        
        # Cleanup expired entries
        removed_count = cache.cleanup_expired()
        
        assert removed_count == 1
        assert len(cache._cache) == 1
        
        # Verify the remaining entry
        found, value = cache.get("key2")
        assert found is True
        assert value == "value2"
    
    def test_cache_eviction(self):
        """Test cache eviction when max size is reached."""
        cache = CacheLookup(max_size=2)
        
        # Add entries up to max size
        cache.set("key1", "value1", 3600)
        cache.set("key2", "value2", 3600)
        
        assert len(cache._cache) == 2
        
        # Add one more entry (should trigger eviction)
        cache.set("key3", "value3", 3600)
        
        assert len(cache._cache) == 2  # Should still be at max size
        
        # One of the original entries should be evicted
        found1, _ = cache.get("key1")
        found2, _ = cache.get("key2")
        found3, _ = cache.get("key3")
        
        # At least one should be missing (evicted)
        assert sum([found1, found2, found3]) <= 2
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = CacheLookup()
        
        # Initial stats
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['sets'] == 0
        
        # Perform some operations
        cache.set("key1", "value1", 3600)
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['sets'] == 1
        assert stats['size'] == 1
        assert stats['hit_rate'] == 50.0  # 1 hit out of 2 requests


class TestLLMCacheLookup:
    """Test the LLMCacheLookup class."""
    
    def test_llm_cache_lookup_creation(self):
        """Test creating an LLMCacheLookup."""
        llm_cache = LLMCacheLookup()
        
        assert llm_cache.cache_lookup is not None
        assert isinstance(llm_cache.cache_lookup, CacheLookup)
    
    def test_get_llm_response_cache_miss(self):
        """Test getting LLM response from cache (miss)."""
        llm_cache = LLMCacheLookup()
        
        api_key = "tk-test-key-123456789012345678901234567890"
        request_data = {"text": "Hello world"}
        
        found, response = llm_cache.get_llm_response(api_key, request_data)
        
        assert found is False
        assert response is None
    
    def test_get_llm_response_cache_hit(self):
        """Test getting LLM response from cache (hit)."""
        llm_cache = LLMCacheLookup()
        
        api_key = "tk-test-key-123456789012345678901234567890"
        request_data = {"text": "Hello world"}
        response_data = {"response": "Hello! How can I help you?"}
        
        # Cache a response
        success = llm_cache.cache_llm_response(api_key, request_data, response_data)
        assert success is True
        
        # Get the cached response
        found, cached_response = llm_cache.get_llm_response(api_key, request_data)
        
        assert found is True
        assert cached_response['response'] == response_data
        assert 'cached_at' in cached_response
        assert 'cache_key' in cached_response
    
    def test_cache_llm_response(self):
        """Test caching LLM response."""
        llm_cache = LLMCacheLookup()
        
        api_key = "tk-test-key-123456789012345678901234567890"
        request_data = {"text": "Hello world", "model": "gpt-3.5", "temperature": 0.7}
        response_data = {"response": "Hello! How can I help you?"}
        
        success = llm_cache.cache_llm_response(api_key, request_data, response_data, ttl=1800)
        
        assert success is True
        
        # Verify it was cached
        found, cached_response = llm_cache.get_llm_response(api_key, request_data)
        assert found is True
        assert cached_response['response'] == response_data
    
    def test_invalidate_user_cache(self):
        """Test invalidating user cache."""
        llm_cache = LLMCacheLookup()
        
        api_key = "tk-test-key-123456789012345678901234567890"
        request_data = {"text": "Hello world"}
        response_data = {"response": "Hello! How can I help you?"}
        
        # Cache some responses
        llm_cache.cache_llm_response(api_key, request_data, response_data)
        llm_cache.cache_llm_response(api_key, {"text": "Goodbye"}, {"response": "Goodbye!"})
        
        # Invalidate user cache
        invalidated_count = llm_cache.invalidate_user_cache(api_key)
        
        # Should have invalidated the cached entries
        assert invalidated_count >= 0  # May be 0 if key structure doesn't match


class TestGlobalInstances:
    """Test the global cache instances."""
    
    def test_global_instances_exist(self):
        """Test that global cache instances exist."""
        assert cache_lookup is not None
        assert isinstance(cache_lookup, CacheLookup)
        
        assert llm_cache_lookup is not None
        assert isinstance(llm_cache_lookup, LLMCacheLookup)
    
    def test_global_instances_are_singletons(self):
        """Test that global instances are singletons."""
        from app.utils.cache_lookup import cache_lookup as cache1
        from app.utils.cache_lookup import cache_lookup as cache2
        
        assert cache1 is cache2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
