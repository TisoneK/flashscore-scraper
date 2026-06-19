"""Error handling and recovery for the scraper."""
import logging
import time
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from selenium.common.exceptions import (
    WebDriverException, TimeoutException, StaleElementReferenceException,
    NoSuchElementException, ElementNotInteractableException
)

class ErrorType(Enum):
    """Types of errors that can occur during scraping."""
    URL_VERIFICATION = auto()
    CONTENT_VERIFICATION = auto()
    ELEMENT_NOT_FOUND = auto()
    NETWORK = auto()
    TIMEOUT = auto()
    UNKNOWN = auto()

@dataclass
class ErrorContext:
    """Context information for an error."""
    error_type: ErrorType
    match_id: str
    tab_index: int
    attempt: int
    error_message: str
    timestamp: float = field(default_factory=time.time)

class ErrorHandler:
    """Handles errors and manages retry logic for the scraper."""
    
    def __init__(self, max_retries: int = 3, base_retry_delay: float = 5.0):
        """Initialize the error handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_retry_delay: Base delay between retries in seconds
        """
        self.logger = logging.getLogger(__name__)
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self._error_history: Dict[str, List[ErrorContext]] = {}
        self._failed_matches: Set[str] = set()
        self._retry_queue: List[str] = []

    def handle_error(self, error: Exception, match_id: str, tab_index: int, 
                    attempt: int) -> Optional[float]:
        """Handle an error and determine if retry should be attempted.
        
        Args:
            error: The exception that occurred
            match_id: ID of the match being processed
            tab_index: Index of the tab where error occurred
            attempt: Current attempt number
            
        Returns:
            Optional[float]: Delay in seconds before next retry, or None if no retry
        """
        error_type = self._categorize_error(error)
        error_context = ErrorContext(
            error_type=error_type,
            match_id=match_id,
            tab_index=tab_index,
            attempt=attempt,
            error_message=str(error)
        )
        
        # Record error in history
        if match_id not in self._error_history:
            self._error_history[match_id] = []
        self._error_history[match_id].append(error_context)
        
        # Log error
        self.logger.warning(
            f"Error processing match {match_id} (Tab {tab_index}), "
            f"attempt {attempt}: {error_type.name} - {error}"
        )
        
        # Determine if retry should be attempted
        if attempt < self.max_retries:
            delay = self._calculate_retry_delay(attempt, error_type)
            return delay
        
        # No more retries, add to failed matches
        self._failed_matches.add(match_id)
        self.logger.error(
            f"Match {match_id} failed after {attempt} attempts: {error_type.name} - {error}"
        )
        return None

    def add_to_retry_queue(self, match_id: str) -> None:
        """Add a match to the retry queue."""
        if match_id not in self._failed_matches and match_id not in self._retry_queue:
            self._retry_queue.append(match_id)

    def get_retry_batch(self, batch_size: int) -> List[str]:
        """Get next batch of matches to retry."""
        batch = self._retry_queue[:batch_size]
        self._retry_queue = self._retry_queue[batch_size:]
        return batch

    def has_retries(self) -> bool:
        """Check if there are matches in the retry queue."""
        return len(self._retry_queue) > 0

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by type."""
        summary = {error_type: 0 for error_type in ErrorType}
        for errors in self._error_history.values():
            for error in errors:
                summary[error.error_type] += 1
        return summary

    def _categorize_error(self, error: Exception) -> ErrorType:
        """Categorize an exception into an error type."""
        if isinstance(error, TimeoutException):
            return ErrorType.TIMEOUT
        if isinstance(error, (NoSuchElementException, ElementNotInteractableException)):
            return ErrorType.ELEMENT_NOT_FOUND
        if isinstance(error, WebDriverException):
            return ErrorType.NETWORK
        return ErrorType.UNKNOWN

    def _calculate_retry_delay(self, attempt: int, error_type: ErrorType) -> float:
        """Calculate delay before next retry attempt."""
        base_delay = self.base_retry_delay
        if error_type in (ErrorType.NETWORK, ErrorType.TIMEOUT):
            base_delay *= 1.5
        return base_delay * (2 ** (attempt - 1))  # Exponential backoff 