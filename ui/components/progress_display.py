import flet as ft
import time
from datetime import datetime
from typing import Optional, Callable

class ProgressDisplay:
    def __init__(self, on_log_update: Optional[Callable] = None):
        self.on_log_update = on_log_update
        self.log_messages = []
        self.max_log_lines = 1000
        
        # Progress tracking
        self.current_match = 0
        self.total_matches = 0
        self.start_time = None
        
        # UI Components
        self.progress_bar = ft.ProgressBar(
            visible=False,
            value=0.0,
            color=ft.Colors.BLUE_400,
            bgcolor=ft.Colors.GREY_300,
        )
        
        self.progress_text = ft.Text(
            "Ready to start",
            color=ft.Colors.GREY_400,
            size=12
        )
        
        self.stats_container = ft.Container(
            content=ft.Row([
                ft.Text("Matches: 0/0", size=12, color=ft.Colors.GREY_400),
                ft.Text("Time: 00:00", size=12, color=ft.Colors.GREY_400),
                ft.Text("Status: Idle", size=12, color=ft.Colors.GREY_400),
            ], spacing=20),
            visible=False
        )
        
        self.log_area = ft.TextField(
            multiline=True,
            min_lines=15,
            max_lines=20,
            read_only=True,
            expand=True,
            value="Scraper not running. Click 'Start Scraper' to begin.",
            border_radius=ft.border_radius.all(8),
            text_style=ft.TextStyle(
                size=11,
                font_family="Consolas",
                color=ft.Colors.WHITE
            ),
            bgcolor=ft.Colors.GREY_900,
            border_color=ft.Colors.GREY_700,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.clear_log_button = ft.IconButton(
            icon=ft.Icons.CLEAR,
            icon_color=ft.Colors.GREY_400,
            tooltip="Clear log",
            on_click=self.clear_log
        )
        
        self.export_log_button = ft.IconButton(
            icon=ft.Icons.DOWNLOAD,
            icon_color=ft.Colors.GREY_400,
            tooltip="Export log",
            on_click=self.export_log
        )
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress bar and text"""
        self.current_match = current
        self.total_matches = total
        
        if total > 0:
            progress_value = current / total
            self.progress_bar.value = progress_value
            self.progress_bar.visible = True
            self.progress_text.value = f"Processing match {current}/{total}"
        else:
            self.progress_bar.visible = False
            self.progress_text.value = message or "Initializing..."
    
    def start_progress(self, total_matches: int):
        """Start progress tracking"""
        self.total_matches = total_matches
        self.current_match = 0
        self.start_time = time.time()
        self.progress_bar.visible = True
        self.progress_bar.value = 0.0
        self.stats_container.visible = True
        self.update_progress(0, total_matches, "Starting...")
        self.add_log("Progress tracking started")
    
    def stop_progress(self):
        """Stop progress tracking"""
        self.progress_bar.visible = False
        self.stats_container.visible = False
        self.progress_text.value = "Completed"
    
    def add_log(self, message: str, level: str = "INFO"):
        """Add a log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        
        self.log_messages.append(formatted_message)
        
        # Keep only the last max_log_lines messages
        if len(self.log_messages) > self.max_log_lines:
            self.log_messages = self.log_messages[-self.max_log_lines:]
        
        # Update log area
        self.log_area.value = "\n".join(self.log_messages)
        
        # Auto-scroll to bottom
        self.log_area.scroll_to(offset=float('inf'))
    
    def clear_log(self, e=None):
        """Clear the log area"""
        self.log_messages.clear()
        self.log_area.value = "Log cleared."
    
    def export_log(self, e=None):
        """Export log to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scraper_log_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.log_messages))
            
            self.add_log(f"Log exported to {filename}", "SUCCESS")
        except Exception as e:
            self.add_log(f"Failed to export log: {e}", "ERROR")
    
    def update_stats(self):
        """Update statistics display"""
        if self.start_time and self.total_matches > 0:
            elapsed_time = time.time() - self.start_time
            elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed_time))
            
            # Calculate ETA
            if self.current_match > 0:
                avg_time_per_match = elapsed_time / self.current_match
                remaining_matches = self.total_matches - self.current_match
                eta_seconds = remaining_matches * avg_time_per_match
                eta_str = time.strftime("%M:%S", time.gmtime(eta_seconds))
            else:
                eta_str = "Calculating..."
            
            # Update stats
            stats_children = [
                ft.Text(f"Matches: {self.current_match}/{self.total_matches}", 
                       size=12, color=ft.Colors.GREY_400),
                ft.Text(f"Time: {elapsed_str}", 
                       size=12, color=ft.Colors.GREY_400),
                ft.Text(f"ETA: {eta_str}", 
                       size=12, color=ft.Colors.GREY_400),
            ]
            
            self.stats_container.content = ft.Row(stats_children, spacing=20)
    
    def build(self):
        return ft.Container(
            content=ft.Column([
                self.progress_bar,
                self.progress_text,
                self.stats_container,
                self.log_area,
            ], spacing=10),
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border_radius=8,
            expand=True
        )
