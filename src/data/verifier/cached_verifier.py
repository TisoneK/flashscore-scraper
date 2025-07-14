"""
Cached verifier for verification result caching.

This module provides caching capabilities for verification results to improve
performance by avoiding redundant verification operations.
"""

import threading
import time
import hashlib
import json
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from src.core.performance_monitor import PerformanceMonitor


@dataclass
class VerificationCache:
    """Represents a cached verification result."""
    data_hash: str
    result: bool
    timestamp: float
    ttl: float = 3600.0  # 1 hour default TTL
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp > self.ttl


class CachedVerifier:
    """
    Cached verifier for verification result caching.
    
    Features:
    - Result caching to avoid redundant verifications
    - Configurable TTL (Time To Live) for cache entries
    - Thread-safe cache operations
    - Performance monitoring
    - Automatic cache cleanup
    """
    
    def __init__(self, 
                 max_cache_size: int = 1000,
                 default_ttl: float = 3600.0,
                 cleanup_interval: float = 300.0):
        """
        Initialize the cached verifier.
        
        Args:
            max_cache_size: Maximum number of cache entries
            default_ttl: Default TTL for cache entries in seconds
            cleanup_interval: Interval for cache cleanup in seconds
        """
        self.max_cache_size = max_cache_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        # Cache storage
        self.cache: Dict[str, VerificationCache] = {}
        self.cache_lock = threading.RLock()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_evictions': 0,
            'verifications_performed': 0,
            'total_verification_time': 0.0,
            'average_verification_time': 0.0
        }
        
        # Threading
        self.stats_lock = threading.Lock()
        self.running = False
        self.cleanup_thread = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the cached verifier and cleanup thread."""
        if self.running:
            return
            
        self.running = True
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="CacheCleanup",
            daemon=True
        )
        self.cleanup_thread.start()
        
        self.logger.info("Cached verifier started")
        
    def stop(self):
        """Stop the cached verifier."""
        if not self.running:
            return
            
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
            
        self.logger.info("Cached verifier stopped")
        
    def verify_with_cache(self, 
                         data: Any,
                         verifier_func: Callable,
                         ttl: Optional[float] = None) -> bool:
        """
        Verify data with caching.
        
        Args:
            data: Data to verify
            verifier_func: Function to perform verification
            ttl: TTL for this cache entry (uses default if None)
            
        Returns:
            Verification result (True if valid, False otherwise)
        """
        if ttl is None:
            ttl = self.default_ttl
            
        # Generate cache key
        cache_key = self._generate_cache_key(data)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            with self.stats_lock:
                self.stats['cache_hits'] += 1
            return cached_result
            
        # Cache miss, perform verification
        with self.stats_lock:
            self.stats['cache_misses'] += 1
            
        start_time = time.time()
        result = verifier_func(data)
        verification_time = time.time() - start_time
        
        # Cache the result
        self._add_to_cache(cache_key, result, ttl)
        
        # Update statistics
        with self.stats_lock:
            self.stats['verifications_performed'] += 1
            self.stats['total_verification_time'] += verification_time
            self.stats['average_verification_time'] = (
                self.stats['total_verification_time'] / 
                self.stats['verifications_performed']
            )
            
        return result
        
    def verify_batch_with_cache(self, 
                               data_items: list,
                               verifier_func: Callable,
                               ttl: Optional[float] = None) -> list:
        """
        Verify multiple data items with caching.
        
        Args:
            data_items: List of data items to verify
            verifier_func: Function to perform verification
            ttl: TTL for cache entries (uses default if None)
            
        Returns:
            List of verification results
        """
        if ttl is None:
            ttl = self.default_ttl
            
        results = []
        
        for data in data_items:
            result = self.verify_with_cache(data, verifier_func, ttl)
            results.append(result)
            
        return results
        
    def _generate_cache_key(self, data: Any) -> str:
        """
        Generate a cache key for the given data.
        
        Args:
            data: Data to generate key for
            
        Returns:
            Cache key string
        """
        try:
            # Try to serialize the data
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data, sort_keys=True)
            else:
                data_str = str(data)
                
            # Generate hash
            return hashlib.md5(data_str.encode()).hexdigest()
            
        except Exception:
            # Fallback to string hash
            return hashlib.md5(str(data).encode()).hexdigest()
            
    def _get_from_cache(self, cache_key: str) -> Optional[bool]:
        """
        Get a result from cache.
        
        Args:
            cache_key: Cache key to look up
            
        Returns:
            Cached result if found and not expired, None otherwise
        """
        with self.cache_lock:
            if cache_key in self.cache:
                cache_entry = self.cache[cache_key]
                
                # Check if expired
                if cache_entry.is_expired():
                    del self.cache[cache_key]
                    return None
                    
                return cache_entry.result
                
        return None
        
    def _add_to_cache(self, cache_key: str, result: bool, ttl: float):
        """
        Add a result to cache.
        
        Args:
            cache_key: Cache key
            result: Verification result
            ttl: Time to live for this entry
        """
        with self.cache_lock:
            # Check if cache is full
            if len(self.cache) >= self.max_cache_size:
                self._evict_oldest()
                
            # Add new entry
            cache_entry = VerificationCache(
                data_hash=cache_key,
                result=result,
                timestamp=time.time(),
                ttl=ttl
            )
            
            self.cache[cache_key] = cache_entry
            
    def _evict_oldest(self):
        """Evict the oldest cache entry."""
        if not self.cache:
            return
            
        # Find oldest entry
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].timestamp
        )
        
        del self.cache[oldest_key]
        
        with self.stats_lock:
            self.stats['cache_evictions'] += 1
            
    def _cleanup_loop(self):
        """Cleanup loop for expired cache entries."""
        while self.running:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except Exception as e:
                self.logger.error(f"Cache cleanup error: {e}")
                
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        with self.cache_lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
                
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
    def clear_cache(self):
        """Clear all cache entries."""
        with self.cache_lock:
            self.cache.clear()
            
        self.logger.info("Cache cleared")
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.stats_lock:
            stats = self.stats.copy()
            
        with self.cache_lock:
            stats['cache_size'] = len(self.cache)
            stats['cache_utilization'] = len(self.cache) / self.max_cache_size
            
        # Calculate hit rate
        total_requests = stats['cache_hits'] + stats['cache_misses']
        if total_requests > 0:
            stats['hit_rate'] = stats['cache_hits'] / total_requests
        else:
            stats['hit_rate'] = 0.0
            
        return stats
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current verification statistics."""
        return self.get_cache_stats()
        
    def reset_stats(self):
        """Reset verification statistics."""
        with self.stats_lock:
            self.stats = {
                'cache_hits': 0,
                'cache_misses': 0,
                'cache_evictions': 0,
                'verifications_performed': 0,
                'total_verification_time': 0.0,
                'average_verification_time': 0.0
            }
            
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop() 