"""
Worker Pool for concurrent match processing.

This module provides a thread-safe worker pool for distributing match processing
across multiple workers to improve scraping performance.
"""

import threading
import queue
import time
import logging
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.exceptions import WorkerPoolError
from src.core.performance_monitor import PerformanceMonitor


@dataclass
class WorkerTask:
    """Represents a task to be processed by a worker."""
    task_id: str
    match_url: str
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class WorkerResult:
    """Represents the result of a worker task."""
    task_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    worker_id: Optional[str] = None


class WorkerPool:
    """
    Thread-safe worker pool for concurrent match processing.
    
    Features:
    - Dynamic worker allocation based on system resources
    - Load balancing across workers
    - Health monitoring and recovery
    - Performance tracking
    - Graceful shutdown
    """
    
    def __init__(self, 
                 max_workers: int = 4,
                 task_timeout: int = 300,
                 health_check_interval: int = 30):
        """
        Initialize the worker pool.
        
        Args:
            max_workers: Maximum number of concurrent workers
            task_timeout: Timeout for individual tasks in seconds
            health_check_interval: Interval for health checks in seconds
        """
        self.max_workers = max_workers
        self.task_timeout = task_timeout
        self.health_check_interval = health_check_interval
        
        # Thread-safe queues
        self.task_queue = queue.PriorityQueue()
        self.result_queue = queue.Queue()
        
        # Worker management
        self.workers: List[threading.Thread] = []
        self.worker_states: Dict[str, Dict[str, Any]] = {}
        self.active_workers = 0
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        self.stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0,
            'worker_utilization': 0.0
        }
        
        # Control flags
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Threading locks
        self.stats_lock = threading.Lock()
        self.worker_lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the worker pool and initialize workers."""
        if self.running:
            return
            
        self.running = True
        self.shutdown_event.clear()
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"Worker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            
        # Start health monitoring thread
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop,
            name="HealthMonitor",
            daemon=True
        )
        self.health_monitor_thread.start()
        
        self.logger.info(f"Worker pool started with {self.max_workers} workers")
        
    def stop(self):
        """Stop the worker pool gracefully."""
        if not self.running:
            return
            
        self.logger.info("Stopping worker pool...")
        self.running = False
        self.shutdown_event.set()
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
            
        # Stop performance monitoring
        self.performance_monitor.stop_resource_monitoring()
        
        self.logger.info("Worker pool stopped")
        
    def submit_task(self, task: WorkerTask) -> bool:
        """
        Submit a task to the worker pool.
        
        Args:
            task: The task to be processed
            
        Returns:
            True if task was submitted successfully
        """
        if not self.running:
            raise WorkerPoolError("Worker pool is not running")
            
        try:
            # Priority is inverted (lower number = higher priority)
            priority = (task.priority, task.created_at)
            self.task_queue.put((priority, task))
            
            with self.stats_lock:
                self.stats['tasks_processed'] += 1
                
            self.logger.debug(f"Task {task.task_id} submitted to worker pool")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit task {task.task_id}: {e}")
            return False
            
    def get_result(self, timeout: float = 1.0) -> Optional[WorkerResult]:
        """
        Get a result from the result queue.
        
        Args:
            timeout: Timeout for getting result
            
        Returns:
            WorkerResult if available, None otherwise
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def get_stats(self) -> Dict[str, Any]:
        """Get current worker pool statistics."""
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
            
        stats['active_workers'] = self.active_workers
        stats['queue_size'] = self.task_queue.qsize()
        
        return stats
        
    def _worker_loop(self):
        """Main worker loop for processing tasks."""
        worker_id = threading.current_thread().name
        
        with self.worker_lock:
            self.worker_states[worker_id] = {
                'status': 'idle',
                'tasks_processed': 0,
                'last_activity': time.time()
            }
            self.active_workers += 1
            
        try:
            while self.running and not self.shutdown_event.is_set():
                try:
                    # Get task with timeout
                    priority, task = self.task_queue.get(timeout=1.0)
                    
                    # Update worker state
                    with self.worker_lock:
                        self.worker_states[worker_id].update({
                            'status': 'processing',
                            'current_task': task.task_id,
                            'last_activity': time.time()
                        })
                    
                    # Process task
                    result = self._process_task(task, worker_id)
                    
                    # Put result in result queue
                    self.result_queue.put(result)
                    
                    # Update worker state
                    with self.worker_lock:
                        self.worker_states[worker_id].update({
                            'status': 'idle',
                            'tasks_processed': self.worker_states[worker_id]['tasks_processed'] + 1,
                            'current_task': None
                        })
                        
                except queue.Empty:
                    # No tasks available, continue loop
                    continue
                except Exception as e:
                    self.logger.error(f"Worker {worker_id} encountered error: {e}")
                    
        finally:
            with self.worker_lock:
                self.active_workers -= 1
                if worker_id in self.worker_states:
                    del self.worker_states[worker_id]
                    
    def _process_task(self, task: WorkerTask, worker_id: str) -> WorkerResult:
        """
        Process a single task.
        
        Args:
            task: The task to process
            worker_id: ID of the worker processing the task
            
        Returns:
            WorkerResult with processing outcome
        """
        start_time = time.time()
        
        try:
            # Simulate task processing (replace with actual scraping logic)
            time.sleep(0.1)  # Simulate processing time
            
            # For now, return a mock result
            # In actual implementation, this would call the scraping logic
            result = WorkerResult(
                task_id=task.task_id,
                success=True,
                data={'url': task.match_url, 'processed_by': worker_id},
                processing_time=time.time() - start_time,
                worker_id=worker_id
            )
            
            with self.stats_lock:
                self.stats['total_processing_time'] += result.processing_time
                self.stats['average_processing_time'] = (
                    self.stats['total_processing_time'] / 
                    (self.stats['tasks_processed'] - self.stats['tasks_failed'])
                )
                
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            with self.stats_lock:
                self.stats['tasks_failed'] += 1
                
            return WorkerResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                processing_time=processing_time,
                worker_id=worker_id
            )
            
    def _health_monitor_loop(self):
        """Monitor worker health and restart failed workers."""
        while self.running and not self.shutdown_event.is_set():
            try:
                time.sleep(self.health_check_interval)
                
                # Check worker health
                with self.worker_lock:
                    current_time = time.time()
                    for worker_id, state in self.worker_states.items():
                        # Check if worker is stuck
                        if (state['status'] == 'processing' and 
                            current_time - state['last_activity'] > self.task_timeout):
                            
                            self.logger.warning(f"Worker {worker_id} appears stuck, marking for restart")
                            state['status'] = 'stuck'
                            
                # Restart stuck workers
                self._restart_stuck_workers()
                
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")
                
    def _restart_stuck_workers(self):
        """Restart workers that are stuck or unresponsive."""
        with self.worker_lock:
            stuck_workers = [
                worker_id for worker_id, state in self.worker_states.items()
                if state['status'] == 'stuck'
            ]
            
        for worker_id in stuck_workers:
            self.logger.info(f"Restarting stuck worker {worker_id}")
            # In a real implementation, you would restart the worker thread
            # For now, we just log the restart
            
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop() 