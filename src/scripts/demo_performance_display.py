#!/usr/bin/env python3
"""
Demo for the rich-based PerformanceDisplay system.
Shows live updates to metrics, progress, batch progress, current task, and alerts.
"""
import time
import threading
import random
from src.cli.performance_display import PerformanceDisplay

def demo_performance_display():
    display = PerformanceDisplay()

    def metrics_updater():
        for i in range(30):
            metrics = {
                'memory_usage': 500 + random.randint(0, 200),
                'cpu_usage': 60 + random.randint(0, 30),
                'active_workers': random.randint(2, 4),
                'tasks_processed': 50 + i * 10,
                'success_rate': 90 + random.randint(-5, 10),
                'average_processing_time': 1.5 + random.uniform(-0.5, 0.5)
            }
            display.update_metrics(metrics)
            time.sleep(0.7)

    def progress_updater():
        for i in range(31):
            display.update_progress(i, 30, "Overall")
            display.update_batch_progress(i % 5, 5, "Batch")
            display.update_current_task(f"Task {i+1}/30: {random.choice(['Loading', 'Extracting', 'Processing', 'Verifying', 'Saving'])}...")
            time.sleep(1)

    def alert_updater():
        alerts = [
            ("Memory usage high", "warning"),
            ("Task completed successfully", "success"),
            ("Network timeout detected", "error"),
            ("Performance optimization active", "info")
        ]
        for i, (msg, typ) in enumerate(alerts):
            time.sleep(5 + i * 4)
            display.show_alert(msg, typ)

    # Start background threads
    t1 = threading.Thread(target=metrics_updater, daemon=True)
    t2 = threading.Thread(target=progress_updater, daemon=True)
    t3 = threading.Thread(target=alert_updater, daemon=True)
    t1.start()
    t2.start()
    t3.start()

    # Start the live display (blocks until interrupted)
    try:
        display.start(refresh_per_second=8)
    except KeyboardInterrupt:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("\nDemo interrupted.")

if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logger.info("\n[DEMO] Rich PerformanceDisplay Live Demo")
    logger.info("Press Ctrl+C to exit early.")
    demo_performance_display() 