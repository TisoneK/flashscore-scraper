"""Batch processing for the scraper."""
import logging
import time
import traceback
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from urllib3 import PoolManager, Retry
from urllib3.exceptions import MaxRetryError

from .tab_manager import TabManager

logger = logging.getLogger(__name__)

@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    base_batch_size: int = 2
    min_batch_size: int = 1
    max_batch_size: int = 3
    base_delay: float = 3.0
    max_delay: float = 10.0
    success_threshold: float = 0.7
    connection_pool_size: int = 2
    worker_timeout: int = 30  # Timeout for each worker in seconds
    max_tabs: int = 1  # Maximum number of tabs to use

@dataclass
class BatchMetrics:
    """Metrics for batch processing."""
    start_time: float = field(default_factory=time.time)
    successful_matches: int = 0
    failed_matches: int = 0
    total_processing_time: float = 0.0
    consecutive_failures: int = 0
    last_success_rate: float = 1.0

class BatchProcessor:
    """Processes matches in batches with adaptive sizing."""
    
    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        tab_manager: Optional[TabManager] = None
    ):
        """Initialize the batch processor.
        
        Args:
            config: Batch processing configuration
            tab_manager: Tab manager instance
        """
        self.config = config or BatchConfig()
        self.tab_manager = tab_manager
        self.metrics = BatchMetrics()
        
        # Set up connection pool with increased size
        self.pool = PoolManager(
            maxsize=self.config.connection_pool_size,
            retries=Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        
        logger.info(
            f"Initialized BatchProcessor with {self.config.connection_pool_size} "
            f"connections, {self.config.worker_timeout}s worker timeout, "
            f"and {self.config.max_tabs} max tabs"
        )

    def process_batch(
        self,
        matches: List[str],
        process_func: Callable[[str], Optional[Dict]],
        max_workers: Optional[int] = None
    ) -> Tuple[List[Dict], List[str]]:
        """Process a batch of matches.
        
        Args:
            matches: List of match IDs to process
            process_func: Function to process each match
            max_workers: Maximum number of parallel workers (defaults to max_tabs)
            
        Returns:
            Tuple of (successful_matches, failed_matches)
        """
        if not self.tab_manager:
            raise RuntimeError("TabManager not initialized")
            
        # Use max_tabs from config if max_workers not specified
        max_workers = max_workers or self.config.max_tabs
            
        successful_matches = []
        failed_matches = []
        batch_start = time.time()
        
        logger.info(
            f"Processing batch of {len(matches)} matches with {max_workers} workers "
            f"(timeout: {self.config.worker_timeout}s)"
        )
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_match = {}
            for match in matches:
                try:
                    # Get next available tab
                    tab_index = self.tab_manager.get_next_tab()
                    logger.debug(f"Got tab {tab_index} for match {match}")
                    
                    # Submit task with tab index
                    future = executor.submit(
                        self._process_with_tab,
                        match=match,
                        process_func=process_func,
                        tab_index=tab_index
                    )
                    future_to_match[future] = (match, tab_index)
                    logger.debug(f"Submitted match {match} to worker with tab {tab_index}")
                    
                except RuntimeError as e:
                    logger.warning(f"No tabs available for match {match}: {e}")
                    failed_matches.append(match)
                except Exception as e:
                    logger.error(
                        f"Error submitting match {match}: {e}\n"
                        f"Traceback: {traceback.format_exc()}"
                    )
                    failed_matches.append(match)
            
            # Process results as they complete
            for future in as_completed(future_to_match, timeout=self.config.worker_timeout):
                match, tab_index = future_to_match[future]
                try:
                    result = future.result(timeout=self.config.worker_timeout)
                    if result:
                        logger.info(f"Successfully processed match {match} with tab {tab_index}")
                        successful_matches.append(result)
                        self.tab_manager.mark_tab_healthy(tab_index)
                    else:
                        logger.warning(f"Failed to process match {match} with tab {tab_index}")
                        failed_matches.append(match)
                        self.tab_manager.mark_tab_unhealthy(tab_index)
                except TimeoutError:
                    logger.error(
                        f"Worker timeout processing match {match} with tab {tab_index} "
                        f"after {self.config.worker_timeout}s"
                    )
                    failed_matches.append(match)
                    self.tab_manager.mark_tab_unhealthy(tab_index)
                except Exception as e:
                    logger.error(
                        f"Error processing match {match} with tab {tab_index}: {e}\n"
                        f"Traceback: {traceback.format_exc()}"
                    )
                    failed_matches.append(match)
                    self.tab_manager.mark_tab_unhealthy(tab_index)
        
        # Update metrics
        self._update_metrics(
            successful=len(successful_matches),
            failed=len(failed_matches),
            processing_time=time.time() - batch_start
        )
        
        logger.info(
            f"Batch completed in {time.time() - batch_start:.1f}s: "
            f"{len(successful_matches)} successful, {len(failed_matches)} failed"
        )
        
        return successful_matches, failed_matches

    def _process_with_tab(
        self,
        match: str,
        process_func: Callable[[str], Optional[Dict]],
        tab_index: int
    ) -> Optional[Dict]:
        """Process a match using a specific tab.
        
        Args:
            match: Match ID to process
            process_func: Function to process the match
            tab_index: Tab index to use
            
        Returns:
            Optional[Dict]: Match details if successful, None otherwise
        """
        try:
            logger.debug(f"Starting processing of match {match} with tab {tab_index}")
            
            # Switch to tab and process
            if not self.tab_manager.switch_to_tab(tab_index):
                logger.error(f"Failed to switch to tab {tab_index} for match {match}")
                return None
                
            logger.debug(f"Successfully switched to tab {tab_index} for match {match}")
            result = process_func(match)
            
            if result:
                logger.debug(f"Successfully extracted data for match {match}")
            else:
                logger.warning(f"No data extracted for match {match}")
                
            return result
            
        except Exception as e:
            logger.error(
                f"Error processing match {match} with tab {tab_index}: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            return None

    def _update_metrics(
        self,
        successful: int,
        failed: int,
        processing_time: float
    ) -> None:
        """Update batch processing metrics.
        
        Args:
            successful: Number of successful matches
            failed: Number of failed matches
            processing_time: Total processing time
        """
        total = successful + failed
        if total > 0:
            self.metrics.last_success_rate = successful / total
            
        if successful > 0:
            self.metrics.consecutive_failures = 0
        else:
            self.metrics.consecutive_failures += 1
            
        self.metrics.successful_matches += successful
        self.metrics.failed_matches += failed
        self.metrics.total_processing_time += processing_time

    def get_adaptive_batch_size(self) -> int:
        """Calculate adaptive batch size based on metrics."""
        if self.metrics.consecutive_failures > 0:
            # Reduce batch size on failures
            return max(
                self.config.min_batch_size,
                int(self.config.base_batch_size * (0.8 ** self.metrics.consecutive_failures))
            )
        elif self.metrics.last_success_rate > self.config.success_threshold:
            # Increase batch size on success
            return min(
                self.config.max_batch_size,
                int(self.config.base_batch_size * 1.2)
            )
        return self.config.base_batch_size

    def get_adaptive_delay(self) -> float:
        """Calculate adaptive delay between batches."""
        if self.metrics.consecutive_failures > 0:
            # Increase delay on failures
            return min(
                self.config.max_delay,
                self.config.base_delay * (1.5 ** self.metrics.consecutive_failures)
            )
        elif self.metrics.last_success_rate < self.config.success_threshold:
            # Increase delay on low success rate
            return min(
                self.config.max_delay,
                self.config.base_delay * 1.5
            )
        return self.config.base_delay

    def should_continue_processing(
        self,
        total_processed: int,
        total_matches: int
    ) -> bool:
        """Determine if processing should continue.
        
        Args:
            total_processed: Number of matches processed so far
            total_matches: Total number of matches to process
            
        Returns:
            bool: True if processing should continue
        """
        if total_processed >= total_matches:
            return False
            
        if self.metrics.consecutive_failures >= 3:
            logger.warning("Too many consecutive failures, stopping processing")
            return False
            
        return True

    def get_metrics_summary(self) -> Dict:
        """Get a summary of batch processing metrics."""
        return {
            'total_matches': self.metrics.successful_matches + self.metrics.failed_matches,
            'successful_matches': self.metrics.successful_matches,
            'failed_matches': self.metrics.failed_matches,
            'success_rate': (
                self.metrics.successful_matches /
                (self.metrics.successful_matches + self.metrics.failed_matches)
                if (self.metrics.successful_matches + self.metrics.failed_matches) > 0
                else 0.0
            ),
            'total_processing_time': self.metrics.total_processing_time,
            'consecutive_failures': self.metrics.consecutive_failures,
            'last_success_rate': self.metrics.last_success_rate
        } 