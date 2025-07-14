"""Database operations for the Flashscore scraper."""
import logging
from typing import List, Optional
from datetime import datetime
import sqlite3
from pathlib import Path

from src.models import MatchModel

logger = logging.getLogger(__name__)

class Database:
    """Handles database operations for match data."""
    
    def __init__(self, db_path: str = "output/database/matches.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create matches table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS matches (
                        match_id TEXT PRIMARY KEY,
                        country TEXT NOT NULL,
                        league TEXT NOT NULL,
                        home_team TEXT NOT NULL,
                        away_team TEXT NOT NULL,
                        home_scores INTEGER,
                        away_scores INTEGER,
                        match_date TEXT NOT NULL,
                        match_time TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create odds table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS odds (
                        match_id TEXT PRIMARY KEY,
                        home_odds REAL,
                        away_odds REAL,
                        over_odds REAL,
                        under_odds REAL,
                        over_under_total REAL,
                        FOREIGN KEY (match_id) REFERENCES matches(match_id)
                    )
                """)
                
                # Create h2h_matches table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS h2h_matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id TEXT NOT NULL,
                        h2h_date TEXT NOT NULL,
                        home_team TEXT NOT NULL,
                        away_team TEXT NOT NULL,
                        home_score INTEGER NOT NULL,
                        away_score INTEGER NOT NULL,
                        competition TEXT,
                        FOREIGN KEY (match_id) REFERENCES matches(match_id)
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
            
    def save_matches(self, matches: List[MatchModel]) -> None:
        """Save matches to database.
        
        Args:
            matches: List of matches to save
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for match in matches:
                    # Insert match
                    cursor.execute("""
                        INSERT OR REPLACE INTO matches (
                            match_id, country, league, home_team, away_team,
                            home_scores, away_scores, match_date, match_time
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        match.match_id,
                        match.country,
                        match.league,
                        match.home_team,
                        match.away_team,
                        match.home_scores if hasattr(match, 'home_scores') else None,
                        match.away_scores if hasattr(match, 'away_scores') else None,
                        match.date,
                        match.time
                    ))
                    
                    # Insert odds if available
                    if match.odds:
                        cursor.execute("""
                            INSERT OR REPLACE INTO odds (
                                match_id, home_odds, away_odds,
                                over_odds, under_odds, over_under_total
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            match.match_id,
                            match.odds.home_odds,
                            match.odds.away_odds,
                            match.odds.over_odds,
                            match.odds.under_odds,
                            match.odds.over_under_total
                        ))
                    
                    # Insert H2H matches
                    for h2h in match.h2h_matches:
                        cursor.execute("""
                            INSERT INTO h2h_matches (
                                match_id, h2h_date, home_team, away_team,
                                home_score, away_score, competition
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            match.match_id,
                            h2h.date,
                            h2h.home_team,
                            h2h.away_team,
                            h2h.home_score,
                            h2h.away_score,
                            h2h.competition if hasattr(h2h, 'competition') else None
                        ))
                
                conn.commit()
                logger.info(f"Saved {len(matches)} matches to database")
                
        except Exception as e:
            logger.error(f"Error saving matches to database: {e}")
            raise
            
    def get_match(self, match_id: str) -> Optional[MatchModel]:
        """Get a match by ID.
        
        Args:
            match_id: ID of the match to retrieve
            
        Returns:
            Optional[MatchModel]: Match if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get match data
                cursor.execute("""
                    SELECT * FROM matches WHERE match_id = ?
                """, (match_id,))
                match_data = cursor.fetchone()
                
                if not match_data:
                    return None
                    
                # Get odds data
                cursor.execute("""
                    SELECT * FROM odds WHERE match_id = ?
                """, (match_id,))
                odds_data = cursor.fetchone()
                
                # Get H2H matches
                cursor.execute("""
                    SELECT * FROM h2h_matches WHERE match_id = ?
                """, (match_id,))
                h2h_data = cursor.fetchall()
                
                # Create match model
                match = MatchModel.create(
                    match_id=match_data[0],
                    country=match_data[1],
                    league=match_data[2],
                    home_team=match_data[3],
                    away_team=match_data[4],
                    home_scores=match_data[5],
                    away_scores=match_data[6],
                    date=match_data[7],
                    time=match_data[8]
                )
                
                # Add odds if available
                if odds_data:
                    match.odds = MatchOddsModel.create({
                        "home_odds": odds_data[1],
                        "away_odds": odds_data[2],
                        "over_odds": odds_data[3],
                        "under_odds": odds_data[4],
                        "over_under_total": odds_data[5]
                    })
                
                # Add H2H matches
                for h2h in h2h_data:
                    match.h2h_matches.append(H2HMatchModel.create({
                        "date": h2h[2],
                        "home_team": h2h[3],
                        "away_team": h2h[4],
                        "home_score": h2h[5],
                        "away_score": h2h[6],
                        "competition": h2h[7]
                    }))
                
                return match
                
        except Exception as e:
            logger.error(f"Error getting match from database: {e}")
            raise 