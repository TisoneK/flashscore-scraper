"""
Test for the performance display system.

This module tests the dynamic console display system that can update
performance metrics and progress bars without affecting other console items.
"""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock
from src.cli.performance_display import PerformanceDisplay, DisplayLine, Colors


class TestColors:
    """Test cases for Colors class."""

    def test_colors_has_reset(self):
        """Test that Colors has RESET constant."""
        assert hasattr(Colors, 'RESET')
        assert isinstance(Colors.RESET, str)

    def test_colors_has_standard_colors(self):
        """Test that Colors has standard ANSI color codes."""
        for color_name in ['RED', 'GREEN', 'YELLOW', 'BLUE', 'MAGENTA', 'CYAN', 'WHITE']:
            assert hasattr(Colors, color_name)
            assert isinstance(getattr(Colors, color_name), str)

    def test_colors_has_styles(self):
        """Test that Colors has style codes."""
        assert hasattr(Colors, 'BOLD')
        assert hasattr(Colors, 'DIM')


class TestDisplayLine:
    """Test cases for DisplayLine dataclass."""

    def test_display_line_creation(self):
        """Test creating a DisplayLine."""
        line = DisplayLine(id="test", content="Hello", line_number=1)
        assert line.id == "test"
        assert line.content == "Hello"
        assert line.line_number == 1
        assert line.is_permanent is False
        assert line.last_update == 0.0

    def test_display_line_with_permanent(self):
        """Test creating a permanent DisplayLine."""
        line = DisplayLine(id="header", content="Header", line_number=0, is_permanent=True)
        assert line.is_permanent is True

    def test_display_line_with_timestamp(self):
        """Test creating a DisplayLine with a timestamp."""
        line = DisplayLine(id="test", content="Updated", line_number=2, last_update=12345.0)
        assert line.last_update == 12345.0


class TestPerformanceDisplay:
    """Test cases for PerformanceDisplay."""

    def test_performance_display_initialization(self):
        """Test performance display initialization."""
        display = PerformanceDisplay()
        assert hasattr(display, 'metrics')
        assert isinstance(display.metrics, dict)
        assert hasattr(display, 'lock')
        assert hasattr(display, '_paused')
        assert display._paused is False
        assert hasattr(display, '_is_running')
        assert display._is_running is True  # Created in running state; stop() sets to False

    def test_update_metrics(self):
        """Test updating performance metrics."""
        display = PerformanceDisplay()
        metrics = {
            'memory_usage': 512.5,
            'cpu_usage': 75.2,
            'active_workers': 4,
            'tasks_processed': 150,
            'success_rate': 95.5,
            'average_processing_time': 2.34
        }
        display.update_metrics(metrics)
        assert display.metrics['memory_usage'] == 512.5
        assert display.metrics['cpu_usage'] == 75.2
        assert display.metrics['active_workers'] == 4

    def test_update_progress(self):
        """Test updating overall progress."""
        display = PerformanceDisplay()
        display.update_progress(50, 100, description="Overall")
        assert display.progress_current == 50
        assert display.progress_total == 100
        assert display.progress_desc == "Overall"

    def test_update_batch_progress(self):
        """Test updating batch progress."""
        display = PerformanceDisplay()
        display.update_batch_progress(15, 20, description="Batch")
        assert display.batch_current == 15
        assert display.batch_total == 20
        assert display.batch_desc == "Batch"

    def test_update_current_task(self):
        """Test updating current task description."""
        display = PerformanceDisplay()
        display.update_current_task("Processing match data...")
        assert display.current_task == "Processing match data..."

    def test_update_current_match(self):
        """Test updating current match description."""
        display = PerformanceDisplay()
        display.update_current_match("Lakers vs Celtics")
        assert display.current_match == "Lakers vs Celtics"

    def test_show_alert(self):
        """Test showing alert messages."""
        display = PerformanceDisplay()
        display.show_alert("Test alert message", alert_type="info")
        assert display.alert_message == "Test alert message"
        assert display.alert_type == "info"

    def test_show_status(self):
        """Test showing status messages (persistent alert)."""
        display = PerformanceDisplay()
        display.show_status("Running...")
        assert display.alert_message == "Running..."
        assert display.alert_type == "info"

    def test_update_status_indicators(self):
        """Test updating status indicators."""
        display = PerformanceDisplay()
        indicators = {'network': 'green', 'driver': 'yellow', 'memory': 'red'}
        display.update_status_indicators(indicators)
        assert display.status_indicators == indicators

    def test_update_schedule_info(self):
        """Test updating schedule information."""
        display = PerformanceDisplay()
        display.update_schedule_info("Daily Run", "2026-06-07 09:00")
        assert display.schedule_label == "Daily Run"
        assert display.schedule_next_text == "2026-06-07 09:00"

    def test_set_stop_callback(self):
        """Test setting stop callback."""
        display = PerformanceDisplay()
        callback = MagicMock()
        display.set_stop_callback(callback)
        assert display._stop_callback == callback

    def test_add_subtask(self):
        """Test adding subtasks."""
        display = PerformanceDisplay()
        display.add_subtask("Loading odds...")
        display.add_subtask("Extracting H2H...")
        assert len(display.subtasks) == 2
        assert "Loading odds..." in display.subtasks
        assert "Extracting H2H..." in display.subtasks

    def test_clear_subtasks(self):
        """Test clearing subtasks."""
        display = PerformanceDisplay()
        display.add_subtask("Task 1")
        display.add_subtask("Task 2")
        display.clear_subtasks()
        assert len(display.subtasks) == 0

    def test_subtask_maxlen(self):
        """Test subtask deque maxlen."""
        display = PerformanceDisplay()
        for i in range(10):
            display.add_subtask(f"Task {i}")
        assert len(display.subtasks) == 6
        assert "Task 9" in display.subtasks

    def test_reset_batch_progress(self):
        """Test resetting batch progress."""
        display = PerformanceDisplay()
        display.update_batch_progress(10, 20, description="Old Batch")
        display.reset_batch_progress(50, description="New Batch")
        assert display.batch_total == 50
        assert display.batch_desc == "New Batch"

    def test_stop_sets_flag(self):
        """Test that stop() sets the running flag to False."""
        display = PerformanceDisplay()
        display._is_running = True
        display.stop()
        assert display._is_running is False


class TestPerformanceDisplayThreadSafety:
    """Test thread safety of the display system."""

    def test_concurrent_metric_updates(self):
        """Test that concurrent metric updates don't corrupt data."""
        display = PerformanceDisplay()

        def update_metrics(worker_id):
            for i in range(50):
                display.update_metrics({
                    f'metric_{worker_id}': i,
                    'shared_counter': i
                })

        threads = [
            threading.Thread(target=update_metrics, args=(f"w{i}",))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for i in range(4):
            assert f'metric_w{i}' in display.metrics

    def test_concurrent_progress_updates(self):
        """Test that concurrent progress updates are handled safely."""
        display = PerformanceDisplay()

        def update_progress():
            for i in range(50):
                display.update_progress(i, 100)

        threads = [
            threading.Thread(target=update_progress)
            for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert 0 <= display.progress_current <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
