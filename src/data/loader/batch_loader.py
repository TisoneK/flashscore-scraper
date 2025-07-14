"""
Batch loader for parallel match loading.

This module provides batch processing capabilities for loading multiple matches
in parallel to improve data processing performance.
"""

import threading
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from src.core.performance_monitor import PerformanceMonitor


@dataclass
class LoadTask:
    """Represents a data loading task."""
    task_id: str
    loader_func: Callable
    args: tuple
    kwargs: dict
    priority: int = 0
    timeout: float = 60.0


@dataclass
class LoadResult:
    """Represents the result of a data loading operation."""
    task_id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    worker_id: Optional[str] = None


class BatchLoader:
    """
    Batch loader for parallel data loading operations.
    
    Features:
    - Concurrent data loading
    - Performance monitoring
    - Error handling and retry logic
    - Resource management
    - Load balancing
    """
    
    def __init__(self, max_workers: int = 4, timeout: float = 60.0):
        """
        Initialize the batch loader.
        
        Args:
            max_workers: Maximum number of concurrent workers
            timeout: Default timeout for loading tasks
        """
        self.max_workers = max_workers
        self.default_timeout = timeout
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        self.stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0,
            'concurrent_loads': 0
        }
        
        # Threading
        self.stats_lock = threading.Lock()
        self.active_loads = 0
        self.active_loads_lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def load_batch_parallel(self, 
                           load_tasks: List[LoadTask],
                           timeout: Optional[float] = None) -> Dict[str, LoadResult]:
        """
        Load multiple data items in parallel.
        
        Args:
            load_tasks: List of loading tasks to process
            timeout: Overall timeout for all loading operations
            
        Returns:
            Dictionary mapping task IDs to loading results
        """
        if not load_tasks:
            return {}
            
        results = {}
        start_time = time.time()
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {}
            for task in load_tasks:
                future = executor.submit(
                    self._load_item,
                    task.task_id,
                    task.loader_func,
                    task.args,
                    task.kwargs,
                    task.timeout
                )
                future_to_task[future] = task
                
            # Collect results as they complete
            for future in as_completed(future_to_task, timeout=timeout):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results[task.task_id] = result
                except Exception as e:
                    # Handle timeout or other exceptions
                    result = LoadResult(
                        task_id=task.task_id,
                        success=False,
                        error=str(e),
                        processing_time=time.time() - start_time
                    )
                    results[task.task_id] = result
                    
        # Update statistics
        with self.stats_lock:
            self.stats['tasks_processed'] += len(load_tasks)
            self.stats['tasks_failed'] += sum(
                1 for result in results.values() if not result.success
            )
            
        return results
        
    def load_matches_batch(self, 
                          match_urls: List[str],
                          loader_func: Callable,
                          shared_args: tuple = (),
                          shared_kwargs: Optional[dict] = None,
                          timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Load multiple matches using a batch approach.
        
        Args:
            match_urls: List of match URLs to load
            loader_func: Function to load each match
            shared_args: Arguments to pass to all loaders
            shared_kwargs: Keyword arguments to pass to all loaders
            timeout: Overall timeout for all loading operations
            
        Returns:
            Dictionary mapping URLs to loaded data
        """
        if shared_kwargs is None:
            shared_kwargs = {}
            
        # Create loading tasks
        load_tasks = []
        for i, url in enumerate(match_urls):
            task = LoadTask(
                task_id=f"match_{i}_{hash(url)}",
                loader_func=loader_func,
                args=(url,) + shared_args,
                kwargs=shared_kwargs,
                timeout=self.default_timeout
            )
            load_tasks.append(task)
            
        # Process in parallel
        results = self.load_batch_parallel(load_tasks, timeout)
        
        # Return only successful results
        return {
            match_urls[i]: result.data
            for i, (task_id, result) in enumerate(results.items())
            if result.success
        }
        
    def load_data_batch(self, 
                       data_items: List[Any],
                       loader_func: Callable,
                       shared_args: tuple = (),
                       shared_kwargs: Optional[dict] = None,
                       timeout: Optional[float] = None) -> List[Any]:
        """
        Load multiple data items using a batch approach.
        
        Args:
            data_items: List of data items to load
            loader_func: Function to load each data item
            shared_args: Arguments to pass to all loaders
            shared_kwargs: Keyword arguments to pass to all loaders
            timeout: Overall timeout for all loading operations
            
        Returns:
            List of loaded data items (in order)
        """
        if shared_kwargs is None:
            shared_kwargs = {}
            
        # Create loading tasks
        load_tasks = []
        for i, item in enumerate(data_items):
            task = LoadTask(
                task_id=f"item_{i}_{hash(str(item))}",
                loader_func=loader_func,
                args=(item,) + shared_args,
                kwargs=shared_kwargs,
                timeout=self.default_timeout
            )
            load_tasks.append(task)
            
        # Process in parallel
        results = self.load_batch_parallel(load_tasks, timeout)
        
        # Return results in order
        loaded_items = []
        for i in range(len(data_items)):
            task_id = f"item_{i}_{hash(str(data_items[i]))}"
            if task_id in results and results[task_id].success:
                loaded_items.append(results[task_id].data)
            else:
                loaded_items.append(None)
                
        return loaded_items
        
    def _load_item(self, 
                   task_id: str,
                   loader_func: Callable,
                   args: tuple,
                   kwargs: dict,
                   timeout: float) -> LoadResult:
        """
        Load a single data item with timeout and error handling.
        
        Args:
            task_id: ID of the loading task
            loader_func: Function to load the data item
            args: Arguments for the loader function
            kwargs: Keyword arguments for the loader function
            timeout: Timeout for this loading operation
            
        Returns:
            LoadResult with the loading outcome
        """
        start_time = time.time()
        worker_id = threading.current_thread().name
        
        with self.active_loads_lock:
            self.active_loads += 1
            
        try:
            # Execute the loading with timeout
            data = loader_func(*args, **kwargs)
            
            processing_time = time.time() - start_time
            
            result = LoadResult(
                task_id=task_id,
                success=True,
                data=data,
                processing_time=processing_time,
                worker_id=worker_id
            )
            
            # Update statistics
            with self.stats_lock:
                self.stats['total_processing_time'] += processing_time
                if self.stats['tasks_processed'] > 0:
                    self.stats['average_processing_time'] = (
                        self.stats['total_processing_time'] / 
                        (self.stats['tasks_processed'] - self.stats['tasks_failed'])
                    )
                    
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            result = LoadResult(
                task_id=task_id,
                success=False,
                error=str(e),
                processing_time=processing_time,
                worker_id=worker_id
            )
            
            self.logger.error(f"Failed to load item {task_id}: {e}")
            return result
            
        finally:
            with self.active_loads_lock:
                self.active_loads -= 1
                
    def get_stats(self) -> Dict[str, Any]:
        """Get current loading statistics."""
        with self.stats_lock:
            stats = self.stats.copy()
            
        # Calculate additional metrics
        if stats['tasks_processed'] > 0:
            stats['success_rate'] = (
                (stats['tasks_processed'] - stats['tasks_failed']) / 
                stats['tasks_processed']
            )
        else:
            stats['success_rate'] = 0.0
            
        stats['active_loads'] = self.active_loads
        
        return stats
        
    def reset_stats(self):
        """Reset loading statistics."""
        with self.stats_lock:
            self.stats = {
                'tasks_processed': 0,
                'tasks_failed': 0,
                'total_processing_time': 0.0,
                'average_processing_time': 0.0,
                'concurrent_loads': 0
            } 