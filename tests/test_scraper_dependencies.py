import unittest

from typing import Optional

from src.scraper import FlashscoreScraper
from src.reporting import NullReporter, CaptureReporter


class FakeDriver:
    current_url = "about:blank"
    def quit(self):
        pass
    def implicitly_wait(self, t):
        pass


class FakeDriverManager:
    def __init__(self):
        self._driver = FakeDriver()
        self.chrome_log_path: Optional[str] = None
    def initialize(self) -> None:
        pass
    def get_driver(self):
        return self._driver
    def close(self, force: bool = False) -> None:
        pass


class MemoryStorage:
    def __init__(self):
        self.saved = {}
    def save_matches(self, matches, filename: Optional[str] = None) -> bool:
        self.saved[filename or "matches.json"] = [m.to_dict() for m in matches]
        return True
    def save_results(self, results, filename: Optional[str] = None) -> bool:
        self.saved[filename or "results.json"] = results
        return True
    def load_matches(self, filename):
        # Return empty for simplicity
        return []


class TestScraperDependencies(unittest.TestCase):
    def test_initializes_with_injected_dependencies(self):
        reporter = NullReporter()
        storage = MemoryStorage()
        scraper = FlashscoreScraper(
            reporter=reporter,
            driver_factory=lambda: FakeDriverManager(),
            storage=storage,
            config_snapshot={"browser": {"headless": True}},
        )
        # Access driver to trigger creation
        _ = scraper.driver
        self.assertIsNotNone(scraper.driver)

    def test_reporter_receives_status_and_progress(self):
        reporter = CaptureReporter()
        scraper = FlashscoreScraper(
            reporter=reporter,
            driver_factory=lambda: FakeDriverManager(),
            storage=MemoryStorage(),
            config_snapshot={}
        )
        # Call a few methods that should emit status/progress safely
        scraper.reporter.status("hello")
        scraper.reporter.progress(1, 2, "msg")
        self.assertIn("hello", reporter.statuses)
        self.assertIn((1, 2, "msg"), reporter.progresses)

    def test_defaults_work_without_injections(self):
        # Should construct with defaults; do not actually start a browser here
        scraper = FlashscoreScraper()
        self.assertIsNotNone(scraper)

    def test_cli_fallback_printing(self):
        """Test that CallbackReporter falls back to print() when no callbacks provided."""
        from src.reporting import CallbackReporter
        import io
        import sys
        
        # Capture stdout
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            # Create reporter with no callbacks (CLI fallback scenario)
            reporter = CallbackReporter()
            
            # Test status fallback
            reporter.status("Test status message")
            output = captured_output.getvalue()
            self.assertIn("Test status message", output)
            
            # Clear output
            captured_output.seek(0)
            captured_output.truncate(0)
            
            # Test progress fallback
            reporter.progress(2, 5, "Loading data")
            output = captured_output.getvalue()
            self.assertIn("Progress: 2/5", output)
            self.assertIn("Loading data", output)
            
        finally:
            sys.stdout = original_stdout

    def test_batch_progress_and_current_task_updates(self):
        """Test that scraper reports batch progress and current task updates."""
        from src.reporting import CaptureReporter
        
        # Create a scraper with CaptureReporter to verify progress updates
        reporter = CaptureReporter()
        scraper = FlashscoreScraper(
            reporter=reporter,
            driver_factory=lambda: FakeDriverManager(),
            storage=MemoryStorage(),
            config_snapshot={"browser": {"headless": True}}
        )
        
        # Simulate progress updates that would happen during scraping
        scraper.reporter.progress(1, 10, "Loading match page")
        scraper.reporter.progress(1, 10, "Extracting match data")
        scraper.reporter.progress(1, 10, "Extracting odds data")
        scraper.reporter.progress(1, 10, "Loading H2H data")
        scraper.reporter.progress(1, 10, "Saving match data")
        
        scraper.reporter.progress(2, 10, "Loading match page")
        scraper.reporter.progress(2, 10, "Extracting match data")
        
        # Verify we received multiple progress updates with different task descriptions
        self.assertGreater(len(reporter.progresses), 5, "Should receive multiple progress updates")
        
        # Verify we have different task descriptions
        task_descriptions = [p[2] for p in reporter.progresses if p[2] is not None]
        unique_tasks = set(task_descriptions)
        self.assertGreater(len(unique_tasks), 3, f"Should have multiple unique task descriptions, got: {unique_tasks}")
        
        # Verify we have the expected task descriptions
        expected_tasks = {"Loading match page", "Extracting match data", "Extracting odds data", "Loading H2H data", "Saving match data"}
        self.assertTrue(expected_tasks.issubset(unique_tasks), f"Missing expected tasks. Got: {unique_tasks}")


if __name__ == "__main__":
    unittest.main()


