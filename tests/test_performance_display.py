"""
Test for the performance display system.

This module tests the dynamic console display system that can update
performance metrics and progress bars without affecting other console items.
"""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock
from src.cli.performance_display import PerformanceDisplay, ProgressBar, MetricsDisplay


class TestPerformanceDisplay:
    """Test cases for PerformanceDisplay."""
    
    def test_performance_display_initialization(self):
        """Test performance display initialization."""
        # Mock the screen clearing to avoid affecting test output
        with patch('os.system'):
            display = PerformanceDisplay()
            
            assert display.display_lines is not None
            assert len(display.permanent_lines) > 0
            assert len(display.dynamic_lines) > 0
            assert display.metrics_area_start >= 0
            assert display.progress_area_start >= 0
            
    def test_add_permanent_line(self):
        """Test adding permanent lines."""
        with patch('os.system'):
            display = PerformanceDisplay()
            
            # Add a permanent line
            display.add_permanent_line("test_line", "Test Content")
            
            assert "test_line" in display.display_lines
            assert display.display_lines["test_line"].is_permanent
            assert "test_line" in display.permanent_lines
            
    def test_add_dynamic_line(self):
        """Test adding dynamic lines."""
        with patch('os.system'):
            display = PerformanceDisplay()
            
            # Add a dynamic line
            display.add_dynamic_line("test_dynamic", "Dynamic Content")
            
            assert "test_dynamic" in display.display_lines
            assert not display.display_lines["test_dynamic"].is_permanent
            assert "test_dynamic" in display.dynamic_lines
            
    def test_update_metric(self):
        """Test updating performance metrics."""
        with patch('os.system'), patch('sys.stdout.write'), patch('sys.stdout.flush'):
            display = PerformanceDisplay()
            
            # Update a metric
            display.update_metric("memory_usage", 512.5, " MB")
            
            line = display.display_lines["memory_usage"]
            assert "512.5" in line.content
            assert "MB" in line.content
            
    def test_update_progress_bar(self):
        """Test updating progress bars."""
        with patch('os.system'), patch('sys.stdout.write'), patch('sys.stdout.flush'):
            display = PerformanceDisplay()
            
            # Update progress bar
            display.update_progress_bar("overall_progress", 50, 100, "Overall")
            
            line = display.display_lines["overall_progress"]
            assert "50%" in line.content
            assert "50/100" in line.content
            
    def test_update_current_task(self):
        """Test updating current task description."""
        with patch('os.system'), patch('sys.stdout.write'), patch('sys.stdout.flush'):
            display = PerformanceDisplay()
            
            # Update current task
            display.update_current_task("Processing match data...")
            
            line = display.display_lines["current_task"]
            assert "Processing match data" in line.content
            
    def test_update_performance_metrics(self):
        """Test updating all performance metrics at once."""
        with patch('os.system'), patch('sys.stdout.write'), patch('sys.stdout.flush'):
            display = PerformanceDisplay()
            
            # Update multiple metrics
            metrics = {
                'memory_usage': 512.5,
                'cpu_usage': 75.2,
                'active_workers': 4,
                'tasks_processed': 150,
                'success_rate': 95.5,
                'average_processing_time': 2.34
            }
            
            display.update_performance_metrics(metrics)
            
            # Check that metrics were updated
            memory_line = display.display_lines["memory_usage"]
            cpu_line = display.display_lines["cpu_usage"]
            
            assert "512.5" in memory_line.content
            assert "75.2" in cpu_line.content
            
    def test_show_alert(self):
        """Test showing alert messages."""
        with patch('os.system'), patch('sys.stdout.write'), patch('sys.stdout.flush'):
            display = PerformanceDisplay()
            
            # Show an alert
            display.show_alert("Test alert message", "info")
            
            # The alert should be displayed temporarily
            # (In a real scenario, this would show on screen)
            
    def test_get_display_stats(self):
        """Test getting display statistics."""
        with patch('os.system'):
            display = PerformanceDisplay()
            
            stats = display.get_display_stats()
            
            assert 'total_lines' in stats
            assert 'permanent_lines' in stats
            assert 'dynamic_lines' in stats
            assert 'metrics_area_size' in stats
            assert 'progress_area_size' in stats
            
            assert stats['total_lines'] > 0
            assert stats['permanent_lines'] > 0
            assert stats['dynamic_lines'] > 0


class TestProgressBar:
    """Test cases for ProgressBar."""
    
    def test_progress_bar_initialization(self):
        """Test progress bar initialization."""
        bar = ProgressBar("Test Progress", 100)
        
        assert bar.description == "Test Progress"
        assert bar.total == 100
        assert bar.current == 0
        assert bar.start_time > 0
        
    def test_progress_bar_update(self):
        """Test progress bar update."""
        bar = ProgressBar("Test Progress", 100)
        
        # Update progress
        bar.update(50)
        
        assert bar.current == 50
        assert bar.total == 100
        
    def test_progress_bar_update_with_new_total(self):
        """Test progress bar update with new total."""
        bar = ProgressBar("Test Progress", 100)
        
        # Update with new total
        bar.update(25, 50)
        
        assert bar.current == 25
        assert bar.total == 50
        
    def test_get_bar_string(self):
        """Test getting progress bar string."""
        bar = ProgressBar("Test Progress", 100)
        
        # Test empty progress
        bar_string = bar.get_bar_string()
        assert "0%" in bar_string
        assert "0/100" in bar_string
        assert "░" * 20 in bar_string  # Empty bar
        
        # Test half progress
        bar.update(50)
        bar_string = bar.get_bar_string()
        assert "50%" in bar_string
        assert "50/100" in bar_string
        assert "█" * 10 in bar_string  # Half filled
        assert "░" * 10 in bar_string  # Half empty
        
        # Test full progress
        bar.update(100)
        bar_string = bar.get_bar_string()
        assert "100%" in bar_string
        assert "100/100" in bar_string
        assert "█" * 20 in bar_string  # Full bar
        
    def test_get_bar_string_with_zero_total(self):
        """Test progress bar string with zero total."""
        bar = ProgressBar("Test Progress", 0)
        
        bar_string = bar.get_bar_string()
        assert "0%" in bar_string
        assert "░" * 20 in bar_string  # Empty bar


class TestMetricsDisplay:
    """Test cases for MetricsDisplay."""
    
    def test_metrics_display_initialization(self):
        """Test metrics display initialization."""
        metrics_display = MetricsDisplay()
        
        assert metrics_display.metrics == {}
        assert metrics_display.last_update == 0.0
        
    def test_update_metrics(self):
        """Test updating metrics."""
        metrics_display = MetricsDisplay()
        
        # Update metrics
        new_metrics = {
            'memory_usage': 512.5,
            'cpu_usage': 75.2,
            'active_workers': 4
        }
        
        metrics_display.update_metrics(new_metrics)
        
        assert metrics_display.metrics == new_metrics
        assert metrics_display.last_update > 0
        
    def test_get_formatted_metrics(self):
        """Test getting formatted metrics."""
        metrics_display = MetricsDisplay()
        
        # Set up metrics
        metrics_display.metrics = {
            'memory_usage': 512.5,
            'cpu_usage': 75.2,
            'active_workers': 4,
            'tasks_processed': 150,
            'success_rate': 95.5,
            'average_processing_time': 2.34
        }
        
        formatted = metrics_display.get_formatted_metrics()
        
        assert 'memory_usage' in formatted
        assert 'cpu_usage' in formatted
        assert 'active_workers' in formatted
        assert 'tasks_processed' in formatted
        assert 'success_rate' in formatted
        assert 'average_processing_time' in formatted
        
        # Check formatting
        assert "512.5 MB" in formatted['memory_usage']
        assert "75.2%" in formatted['cpu_usage']
        assert "4" in formatted['active_workers']
        assert "150" in formatted['tasks_processed']
        assert "95.5%" in formatted['success_rate']
        assert "2.34s" in formatted['average_processing_time']


class TestPerformanceDisplayIntegration:
    """Integration tests for performance display system."""
    
    def test_display_with_real_metrics(self):
        """Test display with realistic performance metrics."""
        with patch('os.system'), patch('sys.stdout.write'), patch('sys.stdout.flush'):
            display = PerformanceDisplay()
            
            # Simulate real performance metrics
            metrics = {
                'memory_usage': 1024.5,
                'cpu_usage': 85.3,
                'active_workers': 3,
                'tasks_processed': 250,
                'success_rate': 92.8,
                'average_processing_time': 1.45
            }
            
            # Update display with metrics
            display.update_performance_metrics(metrics)
            
            # Update progress
            display.update_progress_bar("overall_progress", 75, 100, "Overall")
            display.update_progress_bar("batch_progress", 15, 20, "Batch")
            display.update_current_task("Extracting match data from page 15/20")
            
            # Verify updates
            memory_line = display.display_lines["memory_usage"]
            cpu_line = display.display_lines["cpu_usage"]
            overall_line = display.display_lines["overall_progress"]
            batch_line = display.display_lines["batch_progress"]
            task_line = display.display_lines["current_task"]
            
            assert "1024.5" in memory_line.content
            assert "85.3" in cpu_line.content
            assert "75%" in overall_line.content
            assert "75%" in batch_line.content
            assert "Extracting match data" in task_line.content
            
    def test_thread_safety(self):
        """Test thread safety of the display system."""
        with patch('os.system'), patch('sys.stdout.write'), patch('sys.stdout.flush'):
            display = PerformanceDisplay()
            
            # Create multiple threads updating the display
            def update_metrics():
                for i in range(10):
                    metrics = {
                        'memory_usage': 500 + i,
                        'cpu_usage': 50 + i,
                        'active_workers': i % 4 + 1
                    }
                    display.update_performance_metrics(metrics)
                    time.sleep(0.01)
                    
            def update_progress():
                for i in range(10):
                    display.update_progress_bar("overall_progress", i, 10, "Overall")
                    time.sleep(0.01)
                    
            # Start threads
            thread1 = threading.Thread(target=update_metrics)
            thread2 = threading.Thread(target=update_progress)
            
            thread1.start()
            thread2.start()
            
            thread1.join()
            thread2.join()
            
            # Display should remain stable despite concurrent updates
            assert len(display.display_lines) > 0
            assert display.metrics_area_start >= 0
            assert display.progress_area_start >= 0


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v"]) 