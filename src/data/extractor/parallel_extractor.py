"""
Parallel data extractor for concurrent field extraction.

This module provides parallel processing capabilities for data extraction
to improve performance when processing multiple fields simultaneously.
"""

import threading
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from src.core.performance_monitor import PerformanceMonitor


@dataclass
class ExtractionTask:
    """Represents a field extraction task."""
    field_name: str
    extractor_func: Callable
    args: tuple
    kwargs: dict
    priority: int = 0
    timeout: float = 30.0


@dataclass
class ExtractionResult:
    """Represents the result of a field extraction."""
    field_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    worker_id: Optional[str] = None


class ParallelExtractor:
    """
    Parallel extractor for concurrent field extraction.
    
    Features:
    - Concurrent field extraction
    - Performance monitoring
    - Error handling and retry logic
    - Resource management
    - Load balancing
    """
    
    def __init__(self, max_workers: int = 4, timeout: float = 30.0):
        """
        Initialize the parallel extractor.
        
        Args:
            max_workers: Maximum number of concurrent workers
            timeout: Default timeout for extraction tasks
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
            'concurrent_extractions': 0
        }
        
        # Threading
        self.stats_lock = threading.Lock()
        self.active_extractions = 0
        self.active_extractions_lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def extract_fields_parallel(self, 
                              extraction_tasks: List[ExtractionTask],
                              timeout: Optional[float] = None) -> Dict[str, ExtractionResult]:
        """
        Extract multiple fields in parallel.
        
        Args:
            extraction_tasks: List of extraction tasks to process
            timeout: Overall timeout for all extractions
            
        Returns:
            Dictionary mapping field names to extraction results
        """
        if not extraction_tasks:
            return {}
            
        results = {}
        start_time = time.time()
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {}
            for task in extraction_tasks:
                future = executor.submit(
                    self._extract_field,
                    task.field_name,
                    task.extractor_func,
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
                    results[task.field_name] = result
                except Exception as e:
                    # Handle timeout or other exceptions
                    result = ExtractionResult(
                        field_name=task.field_name,
                        success=False,
                        error=str(e),
                        processing_time=time.time() - start_time
                    )
                    results[task.field_name] = result
                    
        # Update statistics
        with self.stats_lock:
            self.stats['tasks_processed'] += len(extraction_tasks)
            self.stats['tasks_failed'] += sum(
                1 for result in results.values() if not result.success
            )
            
        return results
        
    def extract_fields_batch(self, 
                           field_extractors: Dict[str, Callable],
                           shared_args: tuple = (),
                           shared_kwargs: Optional[dict] = None,
                           timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Extract multiple fields using a batch approach.
        
        Args:
            field_extractors: Dictionary mapping field names to extractor functions
            shared_args: Arguments to pass to all extractors
            shared_kwargs: Keyword arguments to pass to all extractors
            timeout: Overall timeout for all extractions
            
        Returns:
            Dictionary mapping field names to extracted data
        """
        if shared_kwargs is None:
            shared_kwargs = {}
            
        # Create extraction tasks
        extraction_tasks = []
        for field_name, extractor_func in field_extractors.items():
            task = ExtractionTask(
                field_name=field_name,
                extractor_func=extractor_func,
                args=shared_args,
                kwargs=shared_kwargs,
                timeout=self.default_timeout
            )
            extraction_tasks.append(task)
            
        # Process in parallel
        results = self.extract_fields_parallel(extraction_tasks, timeout)
        
        # Return only successful results
        return {
            field_name: result.data
            for field_name, result in results.items()
            if result.success
        }
        
    def _extract_field(self, 
                      field_name: str,
                      extractor_func: Callable,
                      args: tuple,
                      kwargs: dict,
                      timeout: float) -> ExtractionResult:
        """
        Extract a single field with timeout and error handling.
        
        Args:
            field_name: Name of the field being extracted
            extractor_func: Function to extract the field
            args: Arguments for the extractor function
            kwargs: Keyword arguments for the extractor function
            timeout: Timeout for this extraction
            
        Returns:
            ExtractionResult with the extraction outcome
        """
        start_time = time.time()
        worker_id = threading.current_thread().name
        
        with self.active_extractions_lock:
            self.active_extractions += 1
            
        try:
            # Execute the extraction with timeout
            data = extractor_func(*args, **kwargs)
            
            processing_time = time.time() - start_time
            
            result = ExtractionResult(
                field_name=field_name,
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
            
            result = ExtractionResult(
                field_name=field_name,
                success=False,
                error=str(e),
                processing_time=processing_time,
                worker_id=worker_id
            )
            
            self.logger.error(f"Failed to extract field {field_name}: {e}")
            return result
            
        finally:
            with self.active_extractions_lock:
                self.active_extractions -= 1
                
    def get_stats(self) -> Dict[str, Any]:
        """Get current extraction statistics."""
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
            
        stats['active_extractions'] = self.active_extractions
        
        return stats
        
    def reset_stats(self):
        """Reset extraction statistics."""
        with self.stats_lock:
            self.stats = {
                'tasks_processed': 0,
                'tasks_failed': 0,
                'total_processing_time': 0.0,
                'average_processing_time': 0.0,
                'concurrent_extractions': 0
            } 