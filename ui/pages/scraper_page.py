import flet as ft
import threading
import time
from typing import Optional
from ui.components.scraper_control import ScraperControl
from ui.components.progress_display import ProgressDisplay

class ScraperPage:
    def __init__(self, on_navigate: callable = None, page: ft.Page = None):
        self.on_navigate = on_navigate
        self.page = page
        
        # Components
        self.scraper_control = ScraperControl(on_progress_update=self._on_progress_update)
        self.progress_display = ProgressDisplay(on_log_update=self._on_log_update)
        
        # Navigation
        self.back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=ft.Colors.GREY_400,
            tooltip="Back to Home",
            on_click=self._on_back_click
        )
        
        self.results_button = ft.IconButton(
            icon=ft.Icons.TABLE_CHART,
            icon_color=ft.Colors.BLUE_400,
            tooltip="View Results",
            on_click=self._on_results_click
        )
        
        # Auto-refresh timer
        self.refresh_timer = None
        self.is_scraping = False
    
    def _on_back_click(self, e):
        """Handle back button click"""
        self._navigate_to("home")
    
    def _on_results_click(self, e):
        """Handle results button click"""
        self._navigate_to("results")
    
    def _navigate_to(self, page: str):
        """Navigate to a specific page"""
        if self.on_navigate:
            self.on_navigate(page)
    
    def _on_progress_update(self, message: str):
        """Handle progress updates from scraper"""
        self.progress_display.add_log(message, "INFO")
        
        # Parse progress information from log messages
        if "Found" in message and "scheduled matches" in message:
            try:
                # Extract number of matches from message like "Found 15 scheduled matches"
                import re
                match = re.search(r"Found (\d+) scheduled matches", message)
                if match:
                    total_matches = int(match.group(1))
                    self.progress_display.start_progress(total_matches)
            except:
                pass
        
        elif "Processing match" in message:
            try:
                # Extract current match from message like "Processing match 5/15"
                import re
                match = re.search(r"Processing match (\d+)/(\d+)", message)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    self.progress_display.update_progress(current, total)
            except:
                pass
        
        elif "Scraping completed" in message or "Scraping was stopped" in message:
            self.progress_display.stop_progress()
            self.is_scraping = False
    
    def _on_log_update(self, message: str, level: str):
        """Handle log updates from progress display"""
        # This can be used for additional logging or notifications
        pass
    
    def start_auto_refresh(self):
        """Start auto-refresh timer for progress updates"""
        def refresh_stats():
            while self.is_scraping:
                try:
                    self.progress_display.update_stats()
                    time.sleep(1)  # Update every second
                except:
                    break
        
        self.refresh_timer = threading.Thread(target=refresh_stats, daemon=True)
        self.refresh_timer.start()
    
    def stop_auto_refresh(self):
        """Stop auto-refresh timer"""
        self.is_scraping = False
        if self.refresh_timer:
            self.refresh_timer.join(timeout=1)
    
    def build(self):
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Row([
                    self.back_button,
                    ft.Text("Scraper", weight=ft.FontWeight.BOLD, size=18),
                    ft.Container(expand=True),
                    self.results_button,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                # Main content
                ft.Row([
                    # Left panel - Scraper control
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PLAY_ARROW, color=ft.Colors.GREEN_400, size=20),
                                ft.Text("Scraper Control", size=18, weight=ft.FontWeight.BOLD),
                                ft.Container(expand=True),
                            ], spacing=10),
                            ft.Text("Configure and run the Flashscore scraper", color=ft.Colors.GREY_400),
                        ], spacing=5),
                        padding=20,
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=10,
                    ),
                    
                    # Right panel - Progress display
                    ft.Container(
                        content=self.progress_display.build(),
                        expand=True,
                    ),
                ], spacing=20, expand=True),
                
            ], spacing=20),
            padding=20,
            expand=True
        ) 