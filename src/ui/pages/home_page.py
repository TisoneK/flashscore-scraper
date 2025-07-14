import flet as ft
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class HomePage:
    def __init__(self, on_navigate: callable = None, page: ft.Page = None):
        self.on_navigate = on_navigate
        self.page = page
        
        # UI Components
        self.welcome_text = ft.Text(
            "Welcome to Flashscore Scraper",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.WHITE
        )
        
        self.subtitle_text = ft.Text(
            "A powerful tool for scraping basketball match data from Flashscore",
            size=14,
            color=ft.Colors.GREY_400
        )
        
        # Quick stats cards
        self.total_matches_card = self._create_stat_card(
            "Total Matches", "0", ft.Icons.SPORTS_BASKETBALL
        )
        self.complete_matches_card = self._create_stat_card(
            "Complete", "0", ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN_400
        )
        self.incomplete_matches_card = self._create_stat_card(
            "Incomplete", "0", ft.Icons.WARNING, ft.Colors.ORANGE_400
        )
        self.latest_file_card = self._create_stat_card(
            "Latest File", "None", ft.Icons.FILE_OPEN
        )
        
        # Quick action buttons
        self.start_scraping_button = ft.ElevatedButton(
            "Start Scraper",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600,
            ),
            width=200,
            on_click=self._on_start_scraping_click
        )
        
        self.view_results_button = ft.ElevatedButton(
            "View Results",
            icon=ft.Icons.TABLE_CHART,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
            width=200,
            on_click=self._on_view_results_click
        )
        
        self.settings_button = ft.ElevatedButton(
            "Settings",
            icon=ft.Icons.SETTINGS,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREY_600,
            ),
            width=200,
            on_click=self._on_settings_click
        )
        
        # Recent activity
        self.recent_activity_text = ft.Text(
            "Recent Activity",
            weight=ft.FontWeight.BOLD,
            size=16
        )
        
        self.activity_list = ft.ListView(
            spacing=5,
            height=200,
            auto_scroll=True
        )
        
        # Status indicator
        self.status_indicator = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.GREY_400, size=12),
                ft.Text("Ready", color=ft.Colors.GREY_400, size=12)
            ], spacing=5),
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border_radius=8
        )
    
    def _on_start_scraping_click(self, e):
        """Handle start scraping button click"""
        self._navigate_to("scraper")
    
    def _on_view_results_click(self, e):
        """Handle view results button click"""
        self._navigate_to("results")
    
    def _on_settings_click(self, e):
        """Handle settings button click"""
        self._navigate_to("settings")
    
    def _create_stat_card(self, title: str, value: str, icon: str, color: str = ft.Colors.BLUE_400):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=ft.Colors.BLUE_400, size=24),
                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                ], spacing=10),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(expand=True),
            ], spacing=5),
            padding=20,
            bgcolor=ft.Colors.GREY_900,
            border_radius=10,
            expand=True,
        )
    
    def _navigate_to(self, page: str):
        """Navigate to a specific page"""
        if self.on_navigate:
            self.on_navigate(page)
    
    def refresh_stats(self):
        """Refresh statistics from data files"""
        try:
            # Load latest data
            json_dir = Path("output/json")
            if not json_dir.exists():
                return
            
            json_files = list(json_dir.glob("matches_*.json"))
            if not json_files:
                return
            
            # Get latest file
            latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update stats
            total_matches = len(data.get('matches', []))
            skipped_matches = len(data.get('metadata', {}).get('skipped_matches', {}).get('details', []))
            complete_matches = total_matches
            incomplete_matches = skipped_matches
            
            # Update cards
            self.total_matches_card.content.controls[0].controls[1].value = str(total_matches + incomplete_matches)
            self.complete_matches_card.content.controls[0].controls[1].value = str(complete_matches)
            self.incomplete_matches_card.content.controls[0].controls[1].value = str(incomplete_matches)
            self.latest_file_card.content.controls[0].controls[1].value = latest_file.name
            
            # Update activity list
            self._update_activity_list(data)
            
            # Update the UI
            if self.page:
                self.page.update()
            
        except Exception as e:
            pass
    
    def _update_activity_list(self, data: Dict[str, Any]):
        """Update the recent activity list"""
        self.activity_list.controls.clear()
        
        # Add last update time
        last_update = data.get('metadata', {}).get('last_update', 'Unknown')
        if last_update != 'Unknown':
            self.activity_list.controls.append(
                ft.Container(
                    content=ft.Text(f"Last updated: {last_update}", size=12, color=ft.Colors.GREY_400),
                    padding=5
                )
            )
        
        # Add file info
        file_info = data.get('metadata', {}).get('file_info', {})
        if file_info:
            filename = file_info.get('filename', 'Unknown')
            size_bytes = file_info.get('size_bytes', 0)
            size_kb = size_bytes / 1024 if size_bytes > 0 else 0
            
            self.activity_list.controls.append(
                ft.Container(
                    content=ft.Text(f"File: {filename} ({size_kb:.1f} KB)", size=12, color=ft.Colors.GREY_400),
                    padding=5
                )
            )
        
        # Add match summary
        total_matches = len(data.get('matches', []))
        skipped_matches = len(data.get('metadata', {}).get('skipped_matches', {}).get('details', []))
        
        self.activity_list.controls.append(
            ft.Container(
                content=ft.Text(f"Matches processed: {total_matches} complete, {skipped_matches} skipped", 
                               size=12, color=ft.Colors.GREY_400),
                padding=5
            )
        )
    
    def update_status(self, status: str, color: str = ft.Colors.GREY_400):
        """Update the status indicator"""
        self.status_indicator.content.controls[0].color = color
        self.status_indicator.content.controls[1].value = status
        if self.page:
            self.page.update()
    
    def build(self):
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Column([
                        self.welcome_text,
                        self.subtitle_text,
                    ], spacing=5),
                    margin=ft.margin.only(bottom=30)
                ),
                
                # Quick stats
                ft.Container(
                    content=ft.Column([
                        ft.Text("Quick Stats", weight=ft.FontWeight.BOLD, size=16),
                        ft.Row([
                            self.total_matches_card,
                            self.complete_matches_card,
                            self.incomplete_matches_card,
                            self.latest_file_card,
                        ], spacing=10),
                    ], spacing=10),
                    margin=ft.margin.only(bottom=30)
                ),
                
                # Quick actions
                ft.Container(
                    content=ft.Column([
                        ft.Text("Quick Actions", weight=ft.FontWeight.BOLD, size=16),
                        ft.Row([
                            self.start_scraping_button,
                            self.view_results_button,
                            self.settings_button,
                        ], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                    ], spacing=15),
                    margin=ft.margin.only(bottom=30)
                ),
                
                # Recent activity and status
                ft.Row([
                    # Recent activity
                    ft.Container(
                        content=ft.Column([
                            self.recent_activity_text,
                            self.activity_list,
                        ], spacing=10),
                        expand=2,
                    ),
                    
                    # Status
                    ft.Container(
                        content=self.status_indicator,
                        expand=1,
                    ),
                ], spacing=20),
                
            ], spacing=20),
            padding=30,
            expand=True
        )
