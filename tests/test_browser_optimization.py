"""Test browser optimization improvements."""
import time
import psutil
import logging
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.performance_monitor import PerformanceMonitor
from core.resource_manager import ResourceManager
from driver_manager.chrome_driver import ChromeDriverManager
from config import CONFIG

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_performance_monitor():
    """Test the enhanced performance monitor."""
    logger.info("🧪 Testing Performance Monitor...")
    
    monitor = PerformanceMonitor()
    
    # Test memory monitoring
    memory_summary = monitor.get_memory_summary()
    logger.info(f"Memory Summary: {memory_summary}")
    
    # Test CPU monitoring
    cpu_summary = monitor.get_cpu_summary()
    logger.info(f"CPU Summary: {cpu_summary}")
    
    # Test browser monitoring
    browser_summary = monitor.get_browser_summary()
    logger.info(f"Browser Summary: {browser_summary}")
    
    # Test health checks
    memory_healthy = monitor.is_memory_healthy()
    cpu_healthy = monitor.is_cpu_healthy()
    logger.info(f"Memory Healthy: {memory_healthy}")
    logger.info(f"CPU Healthy: {cpu_healthy}")
    
    # Test cleanup triggers
    should_cleanup = monitor.should_trigger_cleanup()
    logger.info(f"Should Trigger Cleanup: {should_cleanup}")
    
    # Cleanup
    monitor.stop_resource_monitoring()
    logger.info("✅ Performance Monitor test completed")

def test_resource_manager():
    """Test the resource manager."""
    logger.info("🧪 Testing Resource Manager...")
    
    # Create performance monitor for resource manager
    performance_monitor = PerformanceMonitor()
    resource_manager = ResourceManager(performance_monitor)
    
    # Test resource summary
    resource_summary = resource_manager.get_resource_summary()
    logger.info(f"Resource Summary: {resource_summary}")
    
    # Test health checks
    is_healthy = resource_manager.is_healthy()
    should_restart = resource_manager.should_restart_browser()
    logger.info(f"Resource Healthy: {is_healthy}")
    logger.info(f"Should Restart Browser: {should_restart}")
    
    # Test cleanup callbacks
    cleanup_called = False
    def test_cleanup_callback():
        nonlocal cleanup_called
        cleanup_called = True
        logger.info("🧹 Cleanup callback executed")
    
    resource_manager.add_cleanup_callback(test_cleanup_callback)
    
    # Force cleanup
    resource_manager.force_cleanup()
    logger.info(f"Cleanup callback called: {cleanup_called}")
    
    # Cleanup
    resource_manager.stop_monitoring()
    performance_monitor.stop_resource_monitoring()
    logger.info("✅ Resource Manager test completed")

def test_chrome_driver_optimization():
    """Test the optimized Chrome driver."""
    logger.info("🧪 Testing Chrome Driver Optimization...")
    
    try:
        # Create Chrome driver manager
        chrome_manager = ChromeDriverManager(CONFIG)
        
        # Test Chrome options
        options = chrome_manager.get_chrome_options()
        logger.info(f"Chrome Options Count: {len(options.arguments)}")
        
        # Check for critical performance flags
        critical_flags = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--memory-pressure-off',
            '--max_old_space_size=4096',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding'
        ]
        
        missing_flags = []
        for flag in critical_flags:
            if flag not in options.arguments:
                missing_flags.append(flag)
        
        if missing_flags:
            logger.warning(f"⚠️ Missing critical flags: {missing_flags}")
        else:
            logger.info("✅ All critical performance flags present")
        
        # Test driver installation check
        installation_status = chrome_manager.check_driver_installation()
        logger.info(f"Driver Installation Status: {installation_status}")
        
        logger.info("✅ Chrome Driver Optimization test completed")
        
    except Exception as e:
        logger.error(f"❌ Chrome Driver test failed: {e}")

def test_memory_usage():
    """Test memory usage monitoring."""
    logger.info("🧪 Testing Memory Usage Monitoring...")
    
    # Get initial memory
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    logger.info(f"Initial Memory Usage: {initial_memory:.1f}MB")
    
    # Create performance monitor
    monitor = PerformanceMonitor()
    
    # Simulate some work
    time.sleep(2)
    
    # Get memory after work
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    logger.info(f"Final Memory Usage: {final_memory:.1f}MB")
    logger.info(f"Memory Increase: {memory_increase:.1f}MB")
    
    # Test memory thresholds
    memory_summary = monitor.get_memory_summary()
    logger.info(f"Peak Memory: {memory_summary['peak_memory_mb']:.1f}MB")
    logger.info(f"Memory Warnings: {memory_summary['memory_warnings']}")
    logger.info(f"Memory Critical: {memory_summary['memory_critical']}")
    
    # Cleanup
    monitor.stop_resource_monitoring()
    logger.info("✅ Memory Usage test completed")

def test_integration():
    """Test integration of all components."""
    logger.info("🧪 Testing Integration...")
    
    try:
        # Create all components
        performance_monitor = PerformanceMonitor()
        resource_manager = ResourceManager(performance_monitor)
        chrome_manager = ChromeDriverManager(CONFIG)
        
        # Test component interaction
        logger.info("Testing component interaction...")
        
        # Simulate resource monitoring
        time.sleep(3)
        
        # Get summaries from all components
        memory_summary = performance_monitor.get_memory_summary()
        cpu_summary = performance_monitor.get_cpu_summary()
        resource_summary = resource_manager.get_resource_summary()
        
        logger.info(f"Integration Memory: {memory_summary['current_memory_mb']:.1f}MB")
        logger.info(f"Integration CPU: {cpu_summary['current_cpu_percent']:.1f}%")
        logger.info(f"Integration Active Tabs: {resource_summary['active_tabs']}")
        
        # Test health status
        memory_healthy = performance_monitor.is_memory_healthy()
        cpu_healthy = performance_monitor.is_cpu_healthy()
        resource_healthy = resource_manager.is_healthy()
        
        logger.info(f"Memory Healthy: {memory_healthy}")
        logger.info(f"CPU Healthy: {cpu_healthy}")
        logger.info(f"Resource Healthy: {resource_healthy}")
        
        # Cleanup
        resource_manager.stop_monitoring()
        performance_monitor.stop_resource_monitoring()
        
        logger.info("✅ Integration test completed")
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")

def main():
    """Run all browser optimization tests."""
    logger.info("🚀 Starting Browser Optimization Tests...")
    
    try:
        # Test individual components
        test_performance_monitor()
        time.sleep(1)
        
        test_resource_manager()
        time.sleep(1)
        
        test_chrome_driver_optimization()
        time.sleep(1)
        
        test_memory_usage()
        time.sleep(1)
        
        test_integration()
        
        logger.info("🎉 All browser optimization tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")

if __name__ == "__main__":
    main() 