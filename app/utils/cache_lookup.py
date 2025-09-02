"""
Cache Lookup Module

This module handles caching for the LLM proxy including:
- Request/response caching
- Cache key generation
- Cache invalidation
- Cache statistics

Currently implemented as a stub that can be enhanced with Redis, Memcached, or other caching solutions.
"""

import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta


class CacheEntry:
    """Represents a cache entry."""
    
    def __init__(self, key: str, value: Any, ttl: int = 3600, created_at: float = None):
        self.key = key
        self.value = value
        self.ttl = ttl  # Time to live in seconds
        self.created_at = created_at or time.time()
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """Access the cache entry and update statistics."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'key': self.key,
            'value': self.value,
            'ttl': self.ttl,
            'created_at': self.created_at,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed,
            'is_expired': self.is_expired()
        }


class CacheLookup:
    """Main cache lookup class with stub implementation."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.logger = logging.getLogger(__name__)
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'total_requests': 0
        }
    
    def generate_cache_key(self, api_key: str, request_data: Dict[str, Any], 
                          model: str = None, temperature: float = None) -> str:
        """
        Generate a cache key for the request.
        
        Args:
            api_key: API key (for user isolation)
            request_data: Request data dictionary
            model: LLM model name (optional)
            temperature: Temperature setting (optional)
            
        Returns:
            Cache key string
        """
        try:
            # Create a deterministic key from request data
            key_data = {
                'api_key_hash': hashlib.sha256(api_key.encode()).hexdigest()[:16],
                'text': request_data.get('text', ''),
                'model': model or 'default',
                'temperature': temperature or 0.7
            }
            
            # Remove None values and sort for consistency
            key_data = {k: v for k, v in key_data.items() if v is not None}
            key_string = json.dumps(key_data, sort_keys=True)
            
            # Generate hash
            cache_key = hashlib.sha256(key_string.encode()).hexdigest()
            
            self.logger.debug(f"Generated cache key: {cache_key[:16]}...")
            return cache_key
            
        except Exception as e:
            self.logger.error(f"Error generating cache key: {str(e)}")
            return hashlib.sha256(f"{api_key}_{time.time()}".encode()).hexdigest()
    
    def get(self, key: str) -> Tuple[bool, Optional[Any]]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Tuple of (found, value)
        """
        try:
            self._stats['total_requests'] += 1
            
            if key not in self._cache:
                self._stats['misses'] += 1
                self.logger.debug(f"Cache miss for key: {key[:16]}...")
                return False, None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                self._stats['misses'] += 1
                del self._cache[key]
                self.logger.debug(f"Cache expired for key: {key[:16]}...")
                return False, None
            
            # Access the entry
            value = entry.access()
            self._stats['hits'] += 1
            self.logger.debug(f"Cache hit for key: {key[:16]}...")
            return True, value
            
        except Exception as e:
            self.logger.error(f"Error getting from cache: {str(e)}")
            self._stats['misses'] += 1
            return False, None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if ttl is None:
                ttl = self.default_ttl
            
            # Check cache size and evict if necessary
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            # Create cache entry
            entry = CacheEntry(key, value, ttl)
            self._cache[key] = entry
            
            self._stats['sets'] += 1
            self.logger.debug(f"Cache set for key: {key[:16]}... (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting cache: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        try:
            if key in self._cache:
                del self._cache[key]
                self._stats['deletes'] += 1
                self.logger.debug(f"Cache delete for key: {key[:16]}...")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting from cache: {str(e)}")
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            self._cache.clear()
            self.logger.info("Cache cleared")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        try:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired entries: {str(e)}")
            return 0
    
    def _evict_oldest(self) -> None:
        """Evict the oldest (least recently accessed) entry."""
        try:
            if not self._cache:
                return
            
            # Find the oldest entry
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k].last_accessed)
            
            del self._cache[oldest_key]
            self._stats['evictions'] += 1
            self.logger.debug(f"Evicted oldest cache entry: {oldest_key[:16]}...")
            
        except Exception as e:
            self.logger.error(f"Error evicting oldest entry: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            total_requests = self._stats['total_requests']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': round(hit_rate, 2),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'sets': self._stats['sets'],
                'deletes': self._stats['deletes'],
                'evictions': self._stats['evictions'],
                'total_requests': total_requests,
                'memory_usage_estimate': len(self._cache) * 1024  # Rough estimate
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get detailed cache information.
        
        Returns:
            Detailed cache information
        """
        try:
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
            
            return {
                'stats': self.get_stats(),
                'entries': {
                    'total': len(self._cache),
                    'expired': expired_count,
                    'active': len(self._cache) - expired_count
                },
                'configuration': {
                    'max_size': self.max_size,
                    'default_ttl': self.default_ttl
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cache info: {str(e)}")
            return {}


class LLMCacheLookup:
    """Specialized cache lookup for LLM requests."""
    
    def __init__(self, cache_lookup: CacheLookup = None):
        self.cache_lookup = cache_lookup or CacheLookup()
        self.logger = logging.getLogger(__name__)
    
    def get_llm_response(self, api_key: str, request_data: Dict[str, Any], 
                        model: str = None, temperature: float = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Get cached LLM response.
        
        Args:
            api_key: API key
            request_data: Request data
            model: LLM model
            temperature: Temperature setting
            
        Returns:
            Tuple of (found, response_data)
        """
        try:
            cache_key = self.cache_lookup.generate_cache_key(
                api_key, request_data, model, temperature
            )
            
            found, cached_response = self.cache_lookup.get(cache_key)
            
            if found:
                self.logger.info(f"LLM cache hit for key: {cache_key[:16]}...")
                return True, cached_response
            else:
                self.logger.debug(f"LLM cache miss for key: {cache_key[:16]}...")
                return False, None
                
        except Exception as e:
            self.logger.error(f"Error getting LLM response from cache: {str(e)}")
            return False, None
    
    def cache_llm_response(self, api_key: str, request_data: Dict[str, Any], 
                          response_data: Dict[str, Any], ttl: int = 3600,
                          model: str = None, temperature: float = None) -> bool:
        """
        Cache LLM response.
        
        Args:
            api_key: API key
            request_data: Original request data
            response_data: Response data to cache
            ttl: Time to live in seconds
            model: LLM model
            temperature: Temperature setting
            
        Returns:
            True if cached successfully
        """
        try:
            cache_key = self.cache_lookup.generate_cache_key(
                api_key, request_data, model, temperature
            )
            
            # Add metadata to cached response
            cached_response = {
                'response': response_data,
                'cached_at': time.time(),
                'cache_key': cache_key,
                'request_metadata': {
                    'model': model,
                    'temperature': temperature,
                    'text_length': len(request_data.get('text', ''))
                }
            }
            
            success = self.cache_lookup.set(cache_key, cached_response, ttl)
            
            if success:
                self.logger.info(f"LLM response cached with key: {cache_key[:16]}... (TTL: {ttl}s)")
            else:
                self.logger.warning(f"Failed to cache LLM response with key: {cache_key[:16]}...")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error caching LLM response: {str(e)}")
            return False
    
    def invalidate_user_cache(self, api_key: str) -> int:
        """
        Invalidate all cache entries for a specific user.
        
        Args:
            api_key: API key to invalidate cache for
            
        Returns:
            Number of entries invalidated
        """
        try:
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            invalidated_count = 0
            
            keys_to_delete = []
            for key in self.cache_lookup._cache.keys():
                # Check if this key belongs to the user
                # This is a simple check - in a real implementation, you'd want more sophisticated key structure
                if api_key_hash in key:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                if self.cache_lookup.delete(key):
                    invalidated_count += 1
            
            self.logger.info(f"Invalidated {invalidated_count} cache entries for user")
            return invalidated_count
            
        except Exception as e:
            self.logger.error(f"Error invalidating user cache: {str(e)}")
            return 0


# Global instances
cache_lookup = CacheLookup()
llm_cache_lookup = LLMCacheLookup(cache_lookup)
