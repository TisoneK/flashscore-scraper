import sys
import os
import contextlib
import time
import random
import logging
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
from selenium.common.exceptions import WebDriverException

@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

class RetryManager:
    """
    Handles retry logic with exponential backoff and jitter.
    """
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter_factor: float = 0.1):
        """
        Initialize the retry manager.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff (2 = 1s, 2s, 4s, 8s...)
            jitter_factor: Random jitter factor (0.1 = ±10% of delay)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter_factor = jitter_factor
        self.logger = logging.getLogger(__name__)
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (exponential_base ^ attempt)
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = delay * self.jitter_factor * random.uniform(-1, 1)
        delay += jitter
        
        return max(0, delay)
    
    def retry_operation(self, 
                       operation: Callable,
                       *args,
                       retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
                       **kwargs) -> Any:
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: Function to retry
            *args: Arguments for the operation
            retryable_exceptions: Tuple of exceptions that should trigger retry
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                result = operation(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"Operation succeeded on attempt {attempt + 1}")
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    self.logger.warning(
                        f"Operation failed on attempt {attempt + 1}/{self.max_attempts}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"Operation failed after {self.max_attempts} attempts. "
                        f"Last error: {e}"
                    )
        
        raise last_exception
    
    def retry_decorator(self, 
                       max_attempts: Optional[int] = None,
                       retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
        """
        Decorator for retrying functions.
        
        Args:
            max_attempts: Override default max_attempts
            retryable_exceptions: Exceptions that should trigger retry
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                attempts = max_attempts if max_attempts is not None else self.max_attempts
                return self.retry_operation(
                    func, *args, 
                    retryable_exceptions=retryable_exceptions,
                    **kwargs
                )
            return wrapper
        return decorator

# Network-specific retry manager
class NetworkRetryManager(RetryManager):
    """
    Specialized retry manager for network operations.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.network_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,
        )

    def _is_network_error(self, exc: Exception) -> bool:
        msg = str(exc)
        network_error_signatures = [
            'net::ERR_INTERNET_DISCONNECTED',
            'net::ERR_PROXY_CONNECTION_FAILED',
            'net::ERR_CONNECTION_TIMED_OUT',
            'net::ERR_CONNECTION_RESET',
            'net::ERR_NAME_NOT_RESOLVED',
            'net::ERR_NETWORK_CHANGED',
            'net::ERR_CONNECTION_REFUSED',
            'net::ERR_FAILED',
            'chrome not reachable',
            'disconnected',
            'timeout',
        ]
        return any(sig in msg for sig in network_error_signatures)

    def retry_network_operation(self, operation: Callable, *args, **kwargs) -> Any:
        from src.core.network_monitor import NetworkMonitor
        import threading
        
        # Helper to check shutdown state dynamically on each iteration
        def _is_shutting_down():
            try:
                return getattr(threading.current_thread(), '_is_shutting_down', False)
            except Exception:
                return False
        # Optional cooperative stop callback passed by callers
        stop_checker = kwargs.pop('stop_checker', None)
        
        monitor = NetworkMonitor()
        last_exception = None
        for attempt in range(self.max_attempts):
            # Cooperative cancellation check
            try:
                if _is_shutting_down() or (callable(stop_checker) and stop_checker()):
                    raise RuntimeError("Operation cancelled by shutdown")
            except Exception:
                # If stop_checker raised, treat as shutdown
                raise RuntimeError("Operation cancelled by shutdown")
            if not monitor.is_connected():
                if not _is_shutting_down():
                    self.logger.warning("Network down, waiting for reconnection before retrying...")
                monitor.wait_for_connection(timeout=60)
                if not _is_shutting_down():
                    self.logger.info("Network reconnected. Resuming operation...")
            try:
                with suppress_stderr():
                    result = operation(*args, **kwargs)
                if attempt > 0 and not _is_shutting_down():
                    self.logger.info(f"Operation succeeded on attempt {attempt + 1}")
                return result
            except WebDriverException as e:
                last_exception = e
                msg = getattr(e, 'msg', None)
                msg = msg.splitlines()[0] if msg else str(e)
                if self._is_network_error(e):
                    if not _is_shutting_down():
                        self.logger.warning(f"Selenium network error: {msg}. Will wait for reconnection and retry.")
                    if attempt < self.max_attempts - 1:
                        delay = self.calculate_delay(attempt)
                        # Cooperative cancellation before sleeping
                        if _is_shutting_down() or (callable(stop_checker) and stop_checker()):
                            raise RuntimeError("Operation cancelled by shutdown")
                        if not _is_shutting_down():
                            self.logger.warning(
                                f"Operation failed on attempt {attempt + 1}/{self.max_attempts}: {msg}. "
                                f"Retrying in {delay:.2f}s..."
                            )
                        time.sleep(delay)
                        continue
                if attempt >= self.max_attempts - 1:
                    if not _is_shutting_down():
                        self.logger.error(
                            f"Operation failed after {self.max_attempts} attempts. "
                            f"Last error: {e}", exc_info=True
                        )
                    raise
                else:
                    delay = self.calculate_delay(attempt)
                    if _is_shutting_down() or (callable(stop_checker) and stop_checker()):
                        raise RuntimeError("Operation cancelled by shutdown")
                    if not _is_shutting_down():
                        self.logger.warning(
                            f"Operation failed on attempt {attempt + 1}/{self.max_attempts}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                    time.sleep(delay)
            except Exception as e:
                last_exception = e
                if self._is_network_error(e):
                    if not _is_shutting_down():
                        self.logger.warning(f"Network error detected: {str(e)}. Will wait for reconnection and retry.")
                    if attempt < self.max_attempts - 1:
                        delay = self.calculate_delay(attempt)
                        if _is_shutting_down() or (callable(stop_checker) and stop_checker()):
                            raise RuntimeError("Operation cancelled by shutdown")
                        if not _is_shutting_down():
                            self.logger.warning(
                                f"Operation failed on attempt {attempt + 1}/{self.max_attempts}: {str(e)}. "
                                f"Retrying in {delay:.2f}s..."
                            )
                        time.sleep(delay)
                        continue
                if attempt >= self.max_attempts - 1:
                    if not _is_shutting_down():
                        self.logger.error(
                            f"Operation failed after {self.max_attempts} attempts. "
                            f"Last error: {e}", exc_info=True
                        )
                    raise
                else:
                    delay = self.calculate_delay(attempt)
                    if _is_shutting_down() or (callable(stop_checker) and stop_checker()):
                        raise RuntimeError("Operation cancelled by shutdown")
                    if not _is_shutting_down():
                        self.logger.warning(
                            f"Operation failed on attempt {attempt + 1}/{self.max_attempts}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                    time.sleep(delay)
        if last_exception is not None:
            raise last_exception
        else:
            raise Exception("Network operation failed after retries, but no exception was captured.") 