"""Performance monitoring for the scraper."""
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    start_time: float = field(default_factory=time.time)
    total_matches: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    tab_processing_times: Dict[str, float] = field(default_factory=dict)
    match_processing_times: Dict[str, float] = field(default_factory=dict)
    batch_times: List[float] = field(default_factory=list)
    last_batch_time: Optional[float] = None

class PerformanceMonitor:
    """Monitors and reports scraper performance metrics."""
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.logger = logging.getLogger(__name__)
        self.metrics = PerformanceMetrics()
        self._start_time = time.time()

    def start_batch(self, batch_size: int) -> None:
        """Start timing a new batch."""
        self.metrics.last_batch_time = time.time()

    def end_batch(self, successful: int, failed: int) -> None:
        """End timing a batch and update metrics."""
        if self.metrics.last_batch_time:
            batch_time = time.time() - self.metrics.last_batch_time
            self.metrics.batch_times.append(batch_time)
            self.metrics.successful_matches += successful
            self.metrics.failed_matches += failed
            self.metrics.total_matches = self.metrics.successful_matches + self.metrics.failed_matches

    def record_tab_time(self, tab_key: str, processing_time: float) -> None:
        """Record processing time for a tab."""
        self.metrics.tab_processing_times[tab_key] = (
            self.metrics.tab_processing_times.get(tab_key, 0) + processing_time
        )

    def record_match_time(self, match_id: str, processing_time: float) -> None:
        """Record processing time for a match."""
        self.metrics.match_processing_times[match_id] = processing_time

    def get_average_batch_time(self) -> float:
        """Calculate average batch processing time."""
        if not self.metrics.batch_times:
            return 0.0
        return sum(self.metrics.batch_times) / len(self.metrics.batch_times)

    def get_average_match_time(self) -> float:
        """Calculate average match processing time."""
        if not self.metrics.match_processing_times:
            return 0.0
        return sum(self.metrics.match_processing_times.values()) / len(self.metrics.match_processing_times)

    def log_progress(self, current_batch_time: Optional[float] = None) -> None:
        """Log current progress and performance metrics."""
        total_processed = self.metrics.successful_matches + self.metrics.failed_matches
        if self.metrics.total_matches > 0:
            percentage = (total_processed / self.metrics.total_matches) * 100
            elapsed_time = time.time() - self._start_time
            avg_time_per_match = elapsed_time / total_processed if total_processed > 0 else 0
            
            progress_msg = (
                f"Progress: {total_processed}/{self.metrics.total_matches} matches "
                f"({percentage:.1f}%) - {self.metrics.successful_matches} successful, "
                f"{self.metrics.failed_matches} failed"
            )
            if current_batch_time:
                progress_msg += f" (Batch time: {current_batch_time:.1f}s, Avg: {avg_time_per_match:.1f}s/match)"
            self.logger.info(progress_msg)

    def log_final_metrics(self) -> None:
        """Log final performance metrics."""
        total_time = time.time() - self._start_time
        self.logger.info("\nPerformance Metrics:")
        self.logger.info(f"Total processing time: {total_time:.1f}s")
        self.logger.info(f"Average time per match: {self.get_average_match_time():.1f}s")
        self.logger.info(f"Average batch time: {self.get_average_batch_time():.1f}s")
        self.logger.info(f"Success rate: {(self.metrics.successful_matches/self.metrics.total_matches*100):.1f}%")
        
        for tab_key, tab_time in sorted(self.metrics.tab_processing_times.items()):
            self.logger.info(f"{tab_key} total processing time: {tab_time:.1f}s") 