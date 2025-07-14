"""
Comprehensive tests for optimization components.

This module tests all the new optimization components including:
- Worker Pool
- Parallel Extractor
- Batch Loader
- Cached Verifier
"""

import time
import threading
import pytest
from unittest.mock import Mock, patch
from src.core.worker_pool import WorkerPool, WorkerTask, WorkerResult
from src.data.extractor.parallel_extractor import ParallelExtractor, ExtractionTask, ExtractionResult
from src.data.loader.batch_loader import BatchLoader, LoadTask, LoadResult
from src.data.verifier.cached_verifier import CachedVerifier, VerificationCache


class TestWorkerPool:
    """Test cases for WorkerPool."""
    
    def test_worker_pool_initialization(self):
        """Test worker pool initialization."""
        pool = WorkerPool(max_workers=4, task_timeout=300)
        
        assert pool.max_workers == 4
        assert pool.task_timeout == 300
        assert not pool.running
        assert pool.active_workers == 0
        
    def test_worker_pool_start_stop(self):
        """Test worker pool start and stop."""
        pool = WorkerPool(max_workers=2)
        
        # Start pool
        pool.start()
        assert pool.running
        assert len(pool.workers) == 2
        
        # Stop pool
        pool.stop()
        assert not pool.running
        
    def test_task_submission(self):
        """Test task submission to worker pool."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Create test task
        task = WorkerTask(
            task_id="test_task",
            match_url="https://example.com/match",
            priority=1
        )
        
        # Submit task
        success = pool.submit_task(task)
        assert success
        
        # Get result
        result = pool.get_result(timeout=5.0)
        assert result is not None
        assert result.task_id == "test_task"
        assert result.success
        
        pool.stop()
        
    def test_worker_pool_stats(self):
        """Test worker pool statistics."""
        pool = WorkerPool(max_workers=2)
        pool.start()
        
        # Submit a few tasks
        for i in range(3):
            task = WorkerTask(
                task_id=f"task_{i}",
                match_url=f"https://example.com/match_{i}"
            )
            pool.submit_task(task)
            
        # Wait for processing
        time.sleep(1)
        
        # Check stats
        stats = pool.get_stats()
        assert stats['tasks_processed'] >= 3
        assert stats['active_workers'] == 2
        
        pool.stop()
        
    def test_worker_pool_context_manager(self):
        """Test worker pool as context manager."""
        with WorkerPool(max_workers=2) as pool:
            assert pool.running
            
            # Submit task
            task = WorkerTask(
                task_id="context_task",
                match_url="https://example.com/context"
            )
            pool.submit_task(task)
            
            # Get result
            result = pool.get_result(timeout=5.0)
            assert result is not None
            
        # Pool should be stopped
        assert not pool.running


class TestParallelExtractor:
    """Test cases for ParallelExtractor."""
    
    def test_parallel_extractor_initialization(self):
        """Test parallel extractor initialization."""
        extractor = ParallelExtractor(max_workers=4, timeout=30.0)
        
        assert extractor.max_workers == 4
        assert extractor.default_timeout == 30.0
        assert extractor.active_extractions == 0
        
    def test_extract_fields_batch(self):
        """Test batch field extraction."""
        extractor = ParallelExtractor(max_workers=2)
        
        # Mock extractor functions
        def extract_name(data):
            return f"Name_{data}"
            
        def extract_score(data):
            return f"Score_{data}"
            
        field_extractors = {
            'name': extract_name,
            'score': extract_score
        }
        
        # Extract fields
        results = extractor.extract_fields_batch(
            field_extractors=field_extractors,
            shared_args=("test_data",),
            timeout=10.0
        )
        
        assert 'name' in results
        assert 'score' in results
        assert results['name'] == "Name_test_data"
        assert results['score'] == "Score_test_data"
        
    def test_extract_fields_parallel(self):
        """Test parallel field extraction."""
        extractor = ParallelExtractor(max_workers=2)
        
        # Create extraction tasks
        def mock_extractor(data):
            return f"Extracted_{data}"
            
        tasks = [
            ExtractionTask(
                field_name="field1",
                extractor_func=mock_extractor,
                args=("data1",),
                kwargs={}
            ),
            ExtractionTask(
                field_name="field2",
                extractor_func=mock_extractor,
                args=("data2",),
                kwargs={}
            )
        ]
        
        # Extract in parallel
        results = extractor.extract_fields_parallel(tasks, timeout=10.0)
        
        assert len(results) == 2
        assert results['field1'].success
        assert results['field2'].success
        assert results['field1'].data == "Extracted_data1"
        assert results['field2'].data == "Extracted_data2"
        
    def test_extractor_stats(self):
        """Test extractor statistics."""
        extractor = ParallelExtractor(max_workers=2)
        
        # Perform some extractions
        def mock_extractor(data):
            time.sleep(0.1)  # Simulate processing
            return f"Extracted_{data}"
            
        field_extractors = {
            'field1': mock_extractor,
            'field2': mock_extractor
        }
        
        extractor.extract_fields_batch(
            field_extractors=field_extractors,
            shared_args=("test",)
        )
        
        # Check stats
        stats = extractor.get_stats()
        assert stats['tasks_processed'] >= 2
        assert stats['success_rate'] > 0
        
    def test_extractor_error_handling(self):
        """Test extractor error handling."""
        extractor = ParallelExtractor(max_workers=2)
        
        # Mock extractor that raises exception
        def failing_extractor(data):
            raise ValueError("Extraction failed")
            
        field_extractors = {
            'failing_field': failing_extractor
        }
        
        # Extract should handle errors gracefully
        results = extractor.extract_fields_batch(
            field_extractors=field_extractors,
            shared_args=("test",)
        )
        
        # Should return empty dict due to failure
        assert len(results) == 0
        
        # Check stats
        stats = extractor.get_stats()
        assert stats['tasks_failed'] > 0


class TestBatchLoader:
    """Test cases for BatchLoader."""
    
    def test_batch_loader_initialization(self):
        """Test batch loader initialization."""
        loader = BatchLoader(max_workers=4, timeout=60.0)
        
        assert loader.max_workers == 4
        assert loader.default_timeout == 60.0
        assert loader.active_loads == 0
        
    def test_load_matches_batch(self):
        """Test batch match loading."""
        loader = BatchLoader(max_workers=2)
        
        # Mock loader function
        def mock_loader(url):
            return f"Loaded_{url}"
            
        match_urls = [
            "https://example.com/match1",
            "https://example.com/match2"
        ]
        
        # Load matches
        results = loader.load_matches_batch(
            match_urls=match_urls,
            loader_func=mock_loader,
            timeout=10.0
        )
        
        assert len(results) == 2
        assert "https://example.com/match1" in results
        assert "https://example.com/match2" in results
        assert results["https://example.com/match1"] == "Loaded_https://example.com/match1"
        
    def test_load_data_batch(self):
        """Test batch data loading."""
        loader = BatchLoader(max_workers=2)
        
        # Mock loader function
        def mock_loader(item):
            return f"Processed_{item}"
            
        data_items = ["item1", "item2", "item3"]
        
        # Load data
        results = loader.load_data_batch(
            data_items=data_items,
            loader_func=mock_loader,
            timeout=10.0
        )
        
        assert len(results) == 3
        assert results[0] == "Processed_item1"
        assert results[1] == "Processed_item2"
        assert results[2] == "Processed_item3"
        
    def test_loader_stats(self):
        """Test loader statistics."""
        loader = BatchLoader(max_workers=2)
        
        # Perform some loads
        def mock_loader(item):
            time.sleep(0.1)  # Simulate processing
            return f"Loaded_{item}"
            
        data_items = ["item1", "item2"]
        
        loader.load_data_batch(
            data_items=data_items,
            loader_func=mock_loader
        )
        
        # Check stats
        stats = loader.get_stats()
        assert stats['tasks_processed'] >= 2
        assert stats['success_rate'] > 0
        
    def test_loader_error_handling(self):
        """Test loader error handling."""
        loader = BatchLoader(max_workers=2)
        
        # Mock loader that raises exception
        def failing_loader(item):
            raise RuntimeError("Loading failed")
            
        data_items = ["item1", "item2"]
        
        # Load should handle errors gracefully
        results = loader.load_data_batch(
            data_items=data_items,
            loader_func=failing_loader
        )
        
        # Should return None for failed items
        assert results[0] is None
        assert results[1] is None


class TestCachedVerifier:
    """Test cases for CachedVerifier."""
    
    def test_cached_verifier_initialization(self):
        """Test cached verifier initialization."""
        verifier = CachedVerifier(
            max_cache_size=1000,
            default_ttl=3600.0,
            cleanup_interval=300.0
        )
        
        assert verifier.max_cache_size == 1000
        assert verifier.default_ttl == 3600.0
        assert verifier.cleanup_interval == 300.0
        assert len(verifier.cache) == 0
        
    def test_verification_cache(self):
        """Test verification cache functionality."""
        cache = VerificationCache(
            data_hash="test_hash",
            result=True,
            timestamp=time.time(),
            ttl=1.0
        )
        
        assert not cache.is_expired()
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.is_expired()
        
    def test_verify_with_cache(self):
        """Test verification with caching."""
        verifier = CachedVerifier(max_cache_size=100)
        verifier.start()
        
        # Mock verifier function
        def mock_verifier(data):
            return data == "valid_data"
            
        # First verification (cache miss)
        result1 = verifier.verify_with_cache("valid_data", mock_verifier)
        assert result1 is True
        
        # Second verification (cache hit)
        result2 = verifier.verify_with_cache("valid_data", mock_verifier)
        assert result2 is True
        
        # Check stats
        stats = verifier.get_stats()
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['verifications_performed'] == 1
        
        verifier.stop()
        
    def test_verify_batch_with_cache(self):
        """Test batch verification with caching."""
        verifier = CachedVerifier(max_cache_size=100)
        verifier.start()
        
        # Mock verifier function
        def mock_verifier(data):
            return data in ["valid1", "valid2"]
            
        data_items = ["valid1", "invalid1", "valid2"]
        
        # Verify batch
        results = verifier.verify_batch_with_cache(data_items, mock_verifier)
        
        assert len(results) == 3
        assert results[0] is True
        assert results[1] is False
        assert results[2] is True
        
        verifier.stop()
        
    def test_cache_eviction(self):
        """Test cache eviction when full."""
        verifier = CachedVerifier(max_cache_size=2)
        verifier.start()
        
        # Mock verifier function
        def mock_verifier(data):
            return True
            
        # Fill cache
        verifier.verify_with_cache("data1", mock_verifier)
        verifier.verify_with_cache("data2", mock_verifier)
        
        # Add one more (should evict oldest)
        verifier.verify_with_cache("data3", mock_verifier)
        
        # Check stats
        stats = verifier.get_stats()
        assert stats['cache_evictions'] > 0
        
        verifier.stop()
        
    def test_cache_cleanup(self):
        """Test cache cleanup of expired entries."""
        verifier = CachedVerifier(
            max_cache_size=100,
            default_ttl=0.1,  # Very short TTL for testing
            cleanup_interval=0.1
        )
        verifier.start()
        
        # Mock verifier function
        def mock_verifier(data):
            return True
            
        # Add cache entry
        verifier.verify_with_cache("test_data", mock_verifier)
        
        # Wait for expiration and cleanup
        time.sleep(0.3)
        
        # Check that cache is empty
        stats = verifier.get_stats()
        assert stats['cache_size'] == 0
        
        verifier.stop()
        
    def test_clear_cache(self):
        """Test cache clearing."""
        verifier = CachedVerifier(max_cache_size=100)
        verifier.start()
        
        # Mock verifier function
        def mock_verifier(data):
            return True
            
        # Add some cache entries
        verifier.verify_with_cache("data1", mock_verifier)
        verifier.verify_with_cache("data2", mock_verifier)
        
        # Clear cache
        verifier.clear_cache()
        
        # Check that cache is empty
        stats = verifier.get_stats()
        assert stats['cache_size'] == 0
        
        verifier.stop()
        
    def test_cached_verifier_context_manager(self):
        """Test cached verifier as context manager."""
        with CachedVerifier(max_cache_size=100) as verifier:
            assert verifier.running
            
            # Mock verifier function
            def mock_verifier(data):
                return data == "valid"
                
            # Test verification
            result = verifier.verify_with_cache("valid", mock_verifier)
            assert result is True
            
        # Verifier should be stopped
        assert not verifier.running


class TestOptimizationIntegration:
    """Integration tests for optimization components."""
    
    def test_worker_pool_with_parallel_extractor(self):
        """Test worker pool integration with parallel extractor."""
        pool = WorkerPool(max_workers=2)
        extractor = ParallelExtractor(max_workers=2)
        
        pool.start()
        
        # Create extraction task
        def mock_extractor(data):
            return f"Extracted_{data}"
            
        # Submit extraction task to worker pool
        task = WorkerTask(
            task_id="extraction_task",
            match_url="https://example.com/match",
            priority=1
        )
        
        pool.submit_task(task)
        
        # Get result
        result = pool.get_result(timeout=5.0)
        assert result is not None
        assert result.success
        
        pool.stop()
        
    def test_batch_loader_with_cached_verifier(self):
        """Test batch loader integration with cached verifier."""
        loader = BatchLoader(max_workers=2)
        verifier = CachedVerifier(max_cache_size=100)
        
        verifier.start()
        
        # Mock loader and verifier functions
        def mock_loader(url):
            return {"url": url, "data": "loaded"}
            
        def mock_verifier(data):
            return data is not None
            
        # Load data
        urls = ["https://example.com/match1", "https://example.com/match2"]
        loaded_data = loader.load_matches_batch(urls, mock_loader)
        
        # Verify loaded data
        for data in loaded_data.values():
            result = verifier.verify_with_cache(data, mock_verifier)
            assert result is True
            
        verifier.stop()
        
    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration across components."""
        from src.core.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        monitor.start_resource_monitoring()
        
        # Test with worker pool
        with WorkerPool(max_workers=2) as pool:
            # Submit some tasks
            for i in range(3):
                task = WorkerTask(
                    task_id=f"perf_test_{i}",
                    match_url=f"https://example.com/match_{i}"
                )
                pool.submit_task(task)
                
            # Get performance stats
            pool_stats = pool.get_stats()
            monitor_stats = monitor.get_stats()
            
            assert pool_stats['tasks_processed'] >= 3
            assert monitor_stats['memory_usage'] > 0
            
        monitor.stop_resource_monitoring()


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"]) 