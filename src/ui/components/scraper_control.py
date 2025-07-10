import flet as ft
import threading
import time
import logging
from typing import Callable, Optional
from src.scraper import FlashscoreScraper
from src.utils import setup_logging

class ScraperControl:
    def __init__(self, on_progress_update: Optional[Callable] = None):
        self.on_progress_update = on_progress_update
        self.scraper: Optional[FlashscoreScraper] = None
        self.is_scraping = False
        self.scraping_thread: Optional[threading.Thread] = None
        
        # UI Components
        self.start_button = ft.ElevatedButton(
            "Start Scraper",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_700,
            ),
            width=180,
            on_click=self.start_scraper_click
        )
        
        self.stop_button = ft.ElevatedButton(
            "Stop Scraper",
            icon=ft.Icons.STOP_ROUNDED,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.RED_700,
            ),
            width=180,
            disabled=True,
            on_click=self.stop_scraper_click
        )
        
        self.status_text = ft.Text(
            "Ready to start scraping",
            color=ft.Colors.GREY_400,
            size=14
        )
        
        # Custom logger for UI updates
        self.ui_logger = self._setup_ui_logger()
        
    def _setup_ui_logger(self):
        """Setup a custom logger that sends messages to UI"""
        logger = logging.getLogger('ui_scraper')
        logger.setLevel(logging.INFO)
        
        class UILogHandler(logging.Handler):
            def __init__(self, ui_callback):
                super().__init__()
                self.ui_callback = ui_callback
                
            def emit(self, record):
                if self.ui_callback:
                    self.ui_callback(f"[{record.levelname}] {record.getMessage()}")
        
        handler = UILogHandler(self._update_ui_log)
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)
        return logger
    
    def _update_ui_log(self, message: str):
        """Update UI with log message"""
        if self.on_progress_update:
            self.on_progress_update(message)
    
    def start_scraper_click(self, e):
        """Handle start button click"""
        if not self.is_scraping:
            self.start_scraping()
    
    def stop_scraper_click(self, e):
        """Handle stop button click"""
        if self.is_scraping:
            self.stop_scraping()
    
    def start_scraping(self):
        """Start the scraping process in a separate thread"""
        if self.is_scraping:
            return
            
        self.is_scraping = True
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.status_text.value = "Initializing scraper..."
        self.status_text.color = ft.Colors.BLUE_400
        
        # Start scraping in background thread
        self.scraping_thread = threading.Thread(target=self._run_scraper, daemon=True)
        self.scraping_thread.start()
    
    def stop_scraping(self):
        """Stop the scraping process"""
        if not self.is_scraping:
            return
            
        self.is_scraping = False
        self.status_text.value = "Stopping scraper..."
        self.status_text.color = ft.Colors.ORANGE_400
        
        # Close scraper if it exists
        if self.scraper:
            try:
                self.scraper.close()
            except Exception as e:
                self._update_ui_log(f"Error closing scraper: {e}")
        
        self.start_button.disabled = False
        self.stop_button.disabled = True
        self.status_text.value = "Scraper stopped"
        self.status_text.color = ft.Colors.GREY_400
    
    def _run_scraper(self):
        """Run the scraper in background thread"""
        try:
            # Setup logging
            # TODO: Pass the correct log_file_path for dual logging if available
            setup_logging()
            
            # Initialize scraper
            self._update_ui_log("Initializing Flashscore scraper...")
            self.scraper = FlashscoreScraper()
            
            # Override scraper's logger to send messages to UI
            original_logger = logging.getLogger(__name__)
            original_logger.handlers.clear()
            original_logger.addHandler(logging.Handler())
            
            # Run scraper
            self._update_ui_log("Starting scraping process...")
            self.scraper.scrape()
            
            if self.is_scraping:  # Only show success if not stopped
                self._update_ui_log("Scraping completed successfully!")
                self.status_text.value = "Scraping completed"
                self.status_text.color = ft.Colors.GREEN_400
            else:
                self._update_ui_log("Scraping was stopped by user")
                self.status_text.value = "Scraping stopped"
                self.status_text.color = ft.Colors.ORANGE_400
                
        except Exception as e:
            self._update_ui_log(f"Error during scraping: {str(e)}")
            self.status_text.value = "Scraping failed"
            self.status_text.color = ft.Colors.RED_400
        finally:
            # Reset UI state
            self.is_scraping = False
            self.start_button.disabled = False
            self.stop_button.disabled = True
    
    def build(self):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [self.start_button, self.stop_button],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        content=self.status_text,
                        margin=ft.margin.only(top=10),
                        alignment=ft.alignment.center
                    )
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=20,
        )
