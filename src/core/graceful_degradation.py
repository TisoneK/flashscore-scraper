import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class SessionState:
    """Represents the current state of a scraping session."""
    session_id: str
    start_time: str
    last_update: str
    total_matches: int
    completed_matches: List[str]
    failed_matches: List[str]
    current_match_index: int
    partial_data: Dict[str, Any]
    is_complete: bool = False

class GracefulDegradation:
    """
    Handles graceful degradation for scraping sessions.
    Saves partial data and allows recovery from interruptions.
    """
    
    def __init__(self, session_file: str = "scraping_session.json"):
        self.session_file = session_file
        self.logger = logging.getLogger(__name__)
        self.current_session: Optional[SessionState] = None
        
    def create_session(self, total_matches: int) -> str:
        """
        Create a new scraping session.
        
        Args:
            total_matches: Total number of matches to process
            
        Returns:
            Session ID
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = SessionState(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            last_update=datetime.now().isoformat(),
            total_matches=total_matches,
            completed_matches=[],
            failed_matches=[],
            current_match_index=0,
            partial_data={},
            is_complete=False
        )
        
        self.logger.info(f"Created new session: {session_id}")
        self._save_session()
        return session_id
    
    def load_session(self) -> Optional[str]:
        """
        Load existing session from file.
        
        Returns:
            Session ID if found, None otherwise
        """
        if not os.path.exists(self.session_file):
            return None
            
        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                
            self.current_session = SessionState(**data)
            self.logger.info(f"Loaded existing session: {self.current_session.session_id}")
            return self.current_session.session_id
            
        except Exception as e:
            self.logger.error(f"Failed to load session: {e}")
            return None
    
    def save_match_progress(self, match_id: str, match_data: Dict[str, Any], 
                           status: str = "completed") -> None:
        """
        Save progress for a single match.
        
        Args:
            match_id: ID of the match
            match_data: Data extracted from the match
            status: Status of the match ("completed", "failed", "partial")
        """
        if not self.current_session:
            self.logger.warning("No active session to save progress")
            return
            
        # Update session state
        self.current_session.last_update = datetime.now().isoformat()
        
        if status == "completed":
            if match_id not in self.current_session.completed_matches:
                self.current_session.completed_matches.append(match_id)
        elif status == "failed":
            if match_id not in self.current_session.failed_matches:
                self.current_session.failed_matches.append(match_id)
        
        # Save partial data
        self.current_session.partial_data[match_id] = {
            "data": match_data,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        self._save_session()
        self.logger.info(f"Saved progress for match {match_id} (status: {status})")
    
    def update_current_match_index(self, index: int) -> None:
        """
        Update the current match index.
        
        Args:
            index: Current match index
        """
        if self.current_session:
            self.current_session.current_match_index = index
            self.current_session.last_update = datetime.now().isoformat()
            self._save_session()
    
    def is_match_completed(self, match_id: str) -> bool:
        """
        Check if a match has been completed.
        
        Args:
            match_id: ID of the match
            
        Returns:
            True if match is completed, False otherwise
        """
        if not self.current_session:
            return False
            
        return match_id in self.current_session.completed_matches
    
    def get_partial_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Get partial data for a match.
        
        Args:
            match_id: ID of the match
            
        Returns:
            Partial data if available, None otherwise
        """
        if not self.current_session:
            return None
            
        return self.current_session.partial_data.get(match_id)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session.
        
        Returns:
            Session summary
        """
        if not self.current_session:
            return {}
            
        return {
            "session_id": self.current_session.session_id,
            "total_matches": self.current_session.total_matches,
            "completed_matches": len(self.current_session.completed_matches),
            "failed_matches": len(self.current_session.failed_matches),
            "current_index": self.current_session.current_match_index,
            "completion_percentage": (
                len(self.current_session.completed_matches) / 
                self.current_session.total_matches * 100
            ),
            "start_time": self.current_session.start_time,
            "last_update": self.current_session.last_update
        }
    
    def complete_session(self) -> None:
        """Mark the current session as complete."""
        if self.current_session:
            self.current_session.is_complete = True
            self.current_session.last_update = datetime.now().isoformat()
            self._save_session()
            self.logger.info(f"Completed session: {self.current_session.session_id}")
    
    def cleanup_session(self) -> None:
        """Clean up the current session file."""
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
            self.logger.info("Cleaned up session file")
    
    def _save_session(self) -> None:
        """Save current session to file."""
        if not self.current_session:
            return
            
        try:
            with open(self.session_file, 'w') as f:
                json.dump(asdict(self.current_session), f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    def resume_from_checkpoint(self, match_ids: List[str]) -> List[str]:
        """
        Resume scraping from the last checkpoint.
        
        Args:
            match_ids: List of all match IDs to process
            
        Returns:
            List of match IDs that still need to be processed
        """
        if not self.current_session:
            return match_ids
            
        # Find matches that haven't been completed
        completed_matches = set(self.current_session.completed_matches)
        remaining_matches = [mid for mid in match_ids if mid not in completed_matches]
        
        self.logger.info(
            f"Resuming session: {len(completed_matches)} completed, "
            f"{len(remaining_matches)} remaining"
        )
        
        return remaining_matches 