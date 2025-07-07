import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.core.graceful_degradation import GracefulDegradation, SessionState

class TestGracefulDegradation(unittest.TestCase):
    def setUp(self):
        # Create temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.graceful_degradation = GracefulDegradation(self.temp_file.name)
    
    def tearDown(self):
        # Clean up temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_create_session(self):
        """Test creating a new session."""
        session_id = self.graceful_degradation.create_session(10)
        
        self.assertIsNotNone(session_id)
        self.assertIsNotNone(self.graceful_degradation.current_session)
        self.assertEqual(self.graceful_degradation.current_session.total_matches, 10)
        self.assertEqual(len(self.graceful_degradation.current_session.completed_matches), 0)
        self.assertFalse(self.graceful_degradation.current_session.is_complete)
    
    def test_save_match_progress(self):
        """Test saving match progress."""
        self.graceful_degradation.create_session(5)
        match_data = {"id": "test123", "home_team": "Team A", "away_team": "Team B"}
        
        self.graceful_degradation.save_match_progress("test123", match_data, "completed")
        
        self.assertIn("test123", self.graceful_degradation.current_session.completed_matches)
        self.assertIn("test123", self.graceful_degradation.current_session.partial_data)
        self.assertEqual(
            self.graceful_degradation.current_session.partial_data["test123"]["status"],
            "completed"
        )
    
    def test_save_match_progress_failed(self):
        """Test saving failed match progress."""
        self.graceful_degradation.create_session(5)
        match_data = {"id": "test123", "error": "Network timeout"}
        
        self.graceful_degradation.save_match_progress("test123", match_data, "failed")
        
        self.assertIn("test123", self.graceful_degradation.current_session.failed_matches)
        self.assertEqual(
            self.graceful_degradation.current_session.partial_data["test123"]["status"],
            "failed"
        )
    
    def test_is_match_completed(self):
        """Test checking if match is completed."""
        self.graceful_degradation.create_session(5)
        self.graceful_degradation.save_match_progress("test123", {}, "completed")
        
        self.assertTrue(self.graceful_degradation.is_match_completed("test123"))
        self.assertFalse(self.graceful_degradation.is_match_completed("test456"))
    
    def test_get_partial_data(self):
        """Test getting partial data for a match."""
        self.graceful_degradation.create_session(5)
        match_data = {"id": "test123", "odds": {"home": 1.5}}
        self.graceful_degradation.save_match_progress("test123", match_data, "partial")
        
        partial_data = self.graceful_degradation.get_partial_data("test123")
        self.assertIsNotNone(partial_data)
        self.assertEqual(partial_data["status"], "partial")
        self.assertEqual(partial_data["data"]["odds"]["home"], 1.5)
    
    def test_get_session_summary(self):
        """Test getting session summary."""
        self.graceful_degradation.create_session(10)
        self.graceful_degradation.save_match_progress("match1", {}, "completed")
        self.graceful_degradation.save_match_progress("match2", {}, "failed")
        
        summary = self.graceful_degradation.get_session_summary()
        
        self.assertEqual(summary["total_matches"], 10)
        self.assertEqual(summary["completed_matches"], 1)
        self.assertEqual(summary["failed_matches"], 1)
        self.assertEqual(summary["completion_percentage"], 10.0)
        self.assertIn("session_id", summary)
        self.assertIn("start_time", summary)
    
    def test_update_current_match_index(self):
        """Test updating current match index."""
        self.graceful_degradation.create_session(10)
        self.graceful_degradation.update_current_match_index(5)
        
        self.assertEqual(self.graceful_degradation.current_session.current_match_index, 5)
    
    def test_complete_session(self):
        """Test completing a session."""
        self.graceful_degradation.create_session(10)
        self.graceful_degradation.complete_session()
        
        self.assertTrue(self.graceful_degradation.current_session.is_complete)
    
    def test_resume_from_checkpoint(self):
        """Test resuming from checkpoint."""
        self.graceful_degradation.create_session(5)
        self.graceful_degradation.save_match_progress("match1", {}, "completed")
        self.graceful_degradation.save_match_progress("match2", {}, "completed")
        
        all_match_ids = ["match1", "match2", "match3", "match4", "match5"]
        remaining_matches = self.graceful_degradation.resume_from_checkpoint(all_match_ids)
        
        self.assertEqual(len(remaining_matches), 3)
        self.assertIn("match3", remaining_matches)
        self.assertIn("match4", remaining_matches)
        self.assertIn("match5", remaining_matches)
        self.assertNotIn("match1", remaining_matches)
        self.assertNotIn("match2", remaining_matches)
    
    def test_load_session(self):
        """Test loading an existing session."""
        # Create and save a session
        self.graceful_degradation.create_session(5)
        self.graceful_degradation.save_match_progress("match1", {}, "completed")
        
        # Create new instance and load session
        new_gd = GracefulDegradation(self.temp_file.name)
        session_id = new_gd.load_session()
        
        self.assertIsNotNone(session_id)
        self.assertIsNotNone(new_gd.current_session)
        self.assertEqual(new_gd.current_session.total_matches, 5)
        self.assertIn("match1", new_gd.current_session.completed_matches)
    
    def test_load_session_no_file(self):
        """Test loading session when no file exists."""
        session_id = self.graceful_degradation.load_session()
        self.assertIsNone(session_id)
    
    def test_cleanup_session(self):
        """Test cleaning up session file."""
        self.graceful_degradation.create_session(5)
        self.assertTrue(os.path.exists(self.temp_file.name))
        
        self.graceful_degradation.cleanup_session()
        self.assertFalse(os.path.exists(self.temp_file.name))
    
    def test_save_progress_no_session(self):
        """Test saving progress when no session exists."""
        # Should not raise an exception
        self.graceful_degradation.save_match_progress("test123", {}, "completed")
        self.assertIsNone(self.graceful_degradation.current_session)

if __name__ == '__main__':
    unittest.main() 