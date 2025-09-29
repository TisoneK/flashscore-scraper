"""
Batch loader for parallel match loading.

This module provides batch processing capabilities for loading multiple matches
in parallel to improve data processing performance.

Note: This loader now works with the new URL structure using the UrlBuilder class.
"""

import threading
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from src.core.performance_monitor import PerformanceMonitor
from src.data.url_builder import UrlBuilder  # Import UrlBuilder


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
        self._executor = None
        self._shutdown_event = threading.Event()
        
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
        
    def __del__(self):
        """Ensure resources are cleaned up when the object is garbage collected."""
        self.shutdown()
        
    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """
        Clean up resources and shutdown the thread pool.
        
        Args:
            wait: If True, wait for all pending tasks to complete
            cancel_futures: If True, cancel pending tasks that haven't started
        """
        if self._executor is not None:
            self.logger.debug("Shutting down thread pool executor")
            self._shutdown_event.set()
            self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)
            self._executor = None
            self._shutdown_event.clear()
            
    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create a thread pool executor."""
        if self._executor is None or self._shutdown_event.is_set():
            if self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            self._shutdown_event.clear()
        return self._executor
        
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
        
        # Check for shutdown before starting
        if self._shutdown_event.is_set():
            self.logger.warning("BatchLoader is shutting down, no new tasks will be processed")
            return {}
            
        # Use ThreadPoolExecutor for parallel processing
        executor = self._get_executor()
        future_to_task = {}
        
        # Submit all tasks
        for task in load_tasks:
            if self._shutdown_event.is_set():
                self.logger.warning("Shutdown detected, cancelling pending tasks")
                break
                
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
        try:
            for future in as_completed(future_to_task, timeout=timeout):
                if self._shutdown_event.is_set():
                    self.logger.warning("Shutdown detected, stopping result collection")
                    break
                    
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
        except Exception as e:
            self.logger.error(f"Error in batch processing: {str(e)}", exc_info=True)
            # If we get here, there was an error in the as_completed loop
            # Make sure we don't leave any futures running
            for future in future_to_task:
                if not future.done():
                    future.cancel()
                    
        # Update statistics
        with self.stats_lock:
            self.stats['tasks_processed'] += len(load_tasks)
            self.stats['tasks_failed'] += sum(
                1 for result in results.values() if not result.success
            )
            
        return results
        
    def load_url_builders_batch(self, 
                              url_builders: List[UrlBuilder],
                              loader_func: Callable,
                              shared_args: tuple = (),
                              shared_kwargs: Optional[dict] = None,
                              timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Load multiple matches using UrlBuilder instances in batch.
        
        Args:
            url_builders: List of UrlBuilder instances
            loader_func: Function to load each match
            shared_args: Arguments to pass to all loaders
            shared_kwargs: Keyword arguments to pass to all loaders
            timeout: Overall timeout for all loading operations
            
        Returns:
            Dictionary mapping match IDs to loaded data
        """
        if shared_kwargs is None:
            shared_kwargs = {}
            
        # Create loading tasks
        load_tasks = []
        for url_builder in url_builders:
            if not isinstance(url_builder, UrlBuilder):
                self.logger.warning(f"Skipping invalid UrlBuilder: {url_builder}")
                continue
                
            task = LoadTask(
                task_id=f"match_{url_builder.mid}",
                loader_func=loader_func,
                args=(url_builder,) + shared_args,
                kwargs=shared_kwargs,
                timeout=timeout or self.default_timeout
            )
            load_tasks.append(task)
            
        # Process in parallel
        results = self.load_batch_parallel(load_tasks, timeout)
        
        # Return only successful results with match IDs as keys
        return {
            task_id: result.data
            for task_id, result in results.items()
            if result.success and result.data
        }
        
    def load_matches_batch(self, 
                          match_urls: List[str],
                          loader_func: Callable,
                          shared_args: tuple = (),
                          shared_kwargs: Optional[dict] = None,
                          timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        [Deprecated] Legacy method to load matches by URLs. 
        Prefer using load_url_builders_batch with UrlBuilder instances.
        """
        self.logger.warning("load_matches_batch is deprecated. Use load_url_builders_batch with UrlBuilder instances instead.")
        
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
                timeout=timeout or self.default_timeout
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
                timeout=timeout or self.default_timeout
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

    def load_matches_batch(self, 
                          match_urls: List[str],
                          loader_func: Callable,
                          shared_args: tuple = (),
                          shared_kwargs: Optional[dict] = None,
                          timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        [Deprecated] Legacy method to load matches by URLs. 
        Prefer using load_url_builders_batch with UrlBuilder instances.
        """
        self.logger.warning("load_matches_batch is deprecated. Use load_url_builders_batch with UrlBuilder instances instead.")
        
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
                timeout=timeout or self.default_timeout
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

    def _load_item(self, 
                   task_id: str,
                   loader_func: Callable,
                   args: tuple,
                   kwargs: dict,
                   timeout: float) -> LoadResult:
        """
        Load a single data item with timeout and error handling.
        
        Args:
            task_id: Unique identifier for the task
            loader_func: The function to execute for this task
            args: Positional arguments to pass to the loader function.
                  Can be a UrlBuilder instance or other arguments.
            kwargs: Keyword arguments to pass to the loader function.
            timeout: Maximum time in seconds to wait for the task to complete
            
        Returns:
            LoadResult: The result of the loading operation
        """
        # Log deprecation warning for legacy team_info usage
        if 'team_info' in kwargs and not any(isinstance(arg, UrlBuilder) for arg in args):
            self.logger.warning(
                "Using team_info parameter is deprecated. "
                "Pass a UrlBuilder instance as the first argument instead."
            )
            
        # Create and return the task
        task = LoadTask(
            task_id=task_id,
            loader_func=loader_func,
            args=args,
            kwargs=kwargs,
            priority=0,  # Default priority
            timeout=timeout or self.default_timeout
        )
        return task

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
            args: Arguments for the loader function.
                 If the first argument is a UrlBuilder, it will be used for logging.
            kwargs: Keyword arguments for the loader function
            timeout: Timeout for this loading operation
            
        Returns:
            LoadResult with the loading outcome
        """
        start_time = time.time()
        worker_id = f"worker_{threading.get_ident()}"
        
        # Extract match ID from UrlBuilder if present
        match_id = None
        if args and isinstance(args[0], UrlBuilder):
            match_id = args[0].mid
            
        # Update active loads counter
        with self.active_loads_lock:
            self.active_loads += 1
            
        try:
            # Start performance monitoring for this task
            op_name = f"load_{match_id or task_id}"
            self.performance_monitor.start_operation(op_name)
            
            # Log start of loading
            if match_id:
                self.logger.info(f"Starting load for match {match_id}")
            
            # Execute the loader function
            result = loader_func(*args, **kwargs)
            
            # Check if the result is a dictionary with a status field (standard format)
            if isinstance(result, dict) and 'status' in result:
                success = result.get('status') == 'success'
                error = result.get('skip_reason') if not success else None
                data = result.get('data') if success else result
            else:
                success = True
                error = None
                data = result
                
            processing_time = time.time() - start_time
            
            # Log completion with match ID if available
            log_msg = f"Task {match_id or task_id} completed in {processing_time:.2f}s. Success: {success}"
            if error:
                log_msg += f" | Error: {error}"
                
            if success:
                self.logger.info(log_msg)
            else:
                self.logger.warning(log_msg)
            
            return LoadResult(
                task_id=task_id,
                success=success,
                data=data,
                error=error,
                processing_time=processing_time,
                worker_id=worker_id
            )
            
        except Exception as e:
            # Log the error with match context if available
            error_msg = f"Error in task {match_id or task_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return LoadResult(
                task_id=task_id,
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time,
                worker_id=worker_id
            )
            
        finally:
            # Update performance monitoring
            self.performance_monitor.end_operation(op_name)
            
            # Update active loads counter
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
                
            return stats
            
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