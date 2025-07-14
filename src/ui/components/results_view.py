import flet as ft
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.models import MatchModel
from src.storage.json_storage import JSONStorage

class ResultsView:
    def __init__(self, on_match_select: Optional[callable] = None):
        self.on_match_select = on_match_select
        self.json_storage = JSONStorage()
        self.matches: List[MatchModel] = []
        self.filtered_matches: List[MatchModel] = []
        self.selected_match: Optional[MatchModel] = None
        
        # Filter states
        self.status_filter = "all"  # all, complete, incomplete
        self.country_filter = ""
        self.league_filter = ""
        
        # UI Components
        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color=ft.Colors.BLUE_400,
            tooltip="Refresh data",
            on_click=self.refresh_data
        )
        
        self.export_button = ft.IconButton(
            icon=ft.Icons.DOWNLOAD,
            icon_color=ft.Colors.GREEN_400,
            tooltip="Export to JSON",
            on_click=self.export_data
        )
        
        # Filter controls
        self.status_dropdown = ft.Dropdown(
            label="Status",
            width=120,
            options=[
                ft.dropdown.Option("all", "All"),
                ft.dropdown.Option("complete", "Complete"),
                ft.dropdown.Option("incomplete", "Incomplete"),
            ],
            value="all",
            on_change=self.apply_filters
        )
        
        self.country_field = ft.TextField(
            label="Country",
            width=150,
            on_change=self.apply_filters
        )
        
        self.league_field = ft.TextField(
            label="League",
            width=150,
            on_change=self.apply_filters
        )
        
        # Results table
        self.results_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Match ID")),
                ft.DataColumn(ft.Text("Country")),
                ft.DataColumn(ft.Text("League")),
                ft.DataColumn(ft.Text("Home Team")),
                ft.DataColumn(ft.Text("Away Team")),
                ft.DataColumn(ft.Text("Date")),
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("H2H Count")),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_700),
            border_radius=8,
            vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_700),
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_700),
            column_spacing=20,
        )
        
        # Match details panel
        self.details_panel = ft.Container(
            content=ft.Column([
                ft.Text("Match Details", 
                       weight=ft.FontWeight.BOLD, 
                       size=16),
                ft.Text("Select a match to view details", 
                       color=ft.Colors.GREY_400),
            ]),
            padding=20,
            border=ft.border.all(1, ft.Colors.GREY_700),
            border_radius=8,
            visible=False,
            expand=True
        )
        
        # Statistics
        self.stats_text = ft.Text(
            "No data loaded",
            color=ft.Colors.GREY_400,
            size=12
        )
    
    def refresh_data(self, e=None):
        """Load latest data from JSON files"""
        try:
            self.matches = self._load_latest_matches()
            self.apply_filters()
            self._update_stats()
        except Exception as e:
            self._show_error(f"Failed to refresh data: {e}")
    
    def _load_latest_matches(self) -> List[MatchModel]:
        """Load matches from the latest JSON file"""
        matches = []
        
        # Find the most recent JSON file
        json_dir = Path("output/json")
        if not json_dir.exists():
            return matches
        
        json_files = list(json_dir.glob("matches_*.json"))
        if not json_files:
            return matches
        
        # Sort by modification time and get the latest
        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load complete matches
            for match_data in data.get('matches', []):
                try:
                    match = MatchModel.create(
                        match_id=match_data.get('match_id', ''),
                        country=match_data.get('country', ''),
                        league=match_data.get('league', ''),
                        home_team=match_data.get('home_team', ''),
                        away_team=match_data.get('away_team', ''),
                        date=match_data.get('date', ''),
                        time=match_data.get('time', ''),
                        status=match_data.get('status', 'complete'),
                        skip_reason=match_data.get('skip_reason', '')
                    )
                    
                    # Load odds if available
                    if 'odds' in match_data and match_data['odds']:
                        from src.models import OddsModel
                        odds_data = match_data['odds']
                        match.odds = OddsModel(
                            match_id=match.match_id,
                            home_odds=odds_data.get('home_odds'),
                            away_odds=odds_data.get('away_odds'),
                            over_odds=odds_data.get('over_odds'),
                            under_odds=odds_data.get('under_odds'),
                            match_total=odds_data.get('match_total')
                        )
                    
                    # Load H2H matches if available
                    if 'h2h_matches' in match_data:
                        from src.models import H2HMatchModel
                        for h2h_data in match_data['h2h_matches']:
                            h2h_match = H2HMatchModel(
                                match_id=match.match_id,
                                date=h2h_data.get('date', ''),
                                home_team=h2h_data.get('home_team', ''),
                                away_team=h2h_data.get('away_team', ''),
                                home_score=h2h_data.get('home_score', 0),
                                away_score=h2h_data.get('away_score', 0),
                                competition=h2h_data.get('competition', '')
                            )
                            match.h2h_matches.append(h2h_match)
                    
                    matches.append(match)
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self._show_error(f"Error loading data from {latest_file}: {e}")
            return []
    
    def apply_filters(self, e=None):
        """Apply current filters to matches"""
        self.filtered_matches = []
        
        for match in self.matches:
            # Status filter
            if self.status_filter != "all" and match.status != self.status_filter:
                continue
            
            # Country filter
            if self.country_filter and self.country_filter.lower() not in match.country.lower():
                continue
            
            # League filter
            if self.league_filter and self.league_filter.lower() not in match.league.lower():
                continue
            
            self.filtered_matches.append(match)
        
        self._update_table()
        self._update_stats()
    
    def _update_table(self):
        """Update the results table with filtered matches"""
        self.results_table.rows.clear()
        
        for match in self.filtered_matches:
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(match.match_id, size=10)),
                    ft.DataCell(ft.Text(match.country, size=10)),
                    ft.DataCell(ft.Text(match.league, size=10)),
                    ft.DataCell(ft.Text(match.home_team, size=10)),
                    ft.DataCell(ft.Text(match.away_team, size=10)),
                    ft.DataCell(ft.Text(match.date, size=10)),
                    ft.DataCell(ft.Text(match.time, size=10)),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(
                                match.status.title(),
                                size=10,
                                color=ft.Colors.WHITE
                            ),
                            bgcolor=ft.Colors.GREEN_600 if match.status == "complete" else ft.Colors.ORANGE_600,
                            padding=ft.padding.all(4),
                            border_radius=4
                        )
                    ),
                    ft.DataCell(ft.Text(str(len(match.h2h_matches)), size=10)),
                ],
                on_select_changed=lambda e, m=match: self._on_row_select(m)
            )
            self.results_table.rows.append(row)
    
    def _on_row_select(self, match: MatchModel):
        """Handle row selection"""
        self.selected_match = match
        self._update_details_panel()
        
        if self.on_match_select:
            self.on_match_select(match)
    
    def _update_details_panel(self):
        """Update the details panel with selected match"""
        if not self.selected_match:
            self.details_panel.visible = False
            return
        
        match = self.selected_match
        
        # Create details content
        details_content = ft.Column([
            ft.Text("Match Details", weight=ft.FontWeight.BOLD, size=16),
            
            # Basic info
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Match ID: {match.match_id}", size=12),
                    ft.Text(f"Country: {match.country}", size=12),
                    ft.Text(f"League: {match.league}", size=12),
                    ft.Text(f"Date: {match.date}", size=12),
                    ft.Text(f"Time: {match.time}", size=12),
                    ft.Text(f"Status: {match.status.title()}", size=12),
                ], spacing=5),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            ),
            
            # Teams
            ft.Container(
                content=ft.Column([
                    ft.Text("Teams", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"Home: {match.home_team}", size=12),
                    ft.Text(f"Away: {match.away_team}", size=12),
                ], spacing=5),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            ),
        ])
        
        # Add odds if available
        if match.odds:
            odds_content = ft.Container(
                content=ft.Column([
                    ft.Text("Odds", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"Home: {match.odds.home_odds or 'N/A'}", size=12),
                    ft.Text(f"Away: {match.odds.away_odds or 'N/A'}", size=12),
                    ft.Text(f"Over: {match.odds.over_odds or 'N/A'}", size=12),
                    ft.Text(f"Under: {match.odds.under_odds or 'N/A'}", size=12),
                    ft.Text(f"Total: {match.odds.match_total or 'N/A'}", size=12),
                ], spacing=5),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            )
            details_content.controls.append(odds_content)
        
        # Add H2H matches if available
        if match.h2h_matches:
            h2h_content = ft.Container(
                content=ft.Column([
                    ft.Text(f"H2H Matches ({len(match.h2h_matches)})", 
                           weight=ft.FontWeight.BOLD, size=14),
                    *[ft.Text(
                        f"{h2h.date}: {h2h.home_team} {h2h.home_score}-{h2h.away_score} {h2h.away_team}",
                        size=10,
                        color=ft.Colors.GREY_400
                    ) for h2h in match.h2h_matches[:5]],  # Show first 5
                    ft.Text("..." if len(match.h2h_matches) > 5 else "", 
                           size=10, color=ft.Colors.GREY_400)
                ], spacing=5),
                padding=10,
                bgcolor=ft.Colors.GREY_900,
                border_radius=8
            )
            details_content.controls.append(h2h_content)
        
        self.details_panel.content = details_content
        self.details_panel.visible = True
    
    def _update_stats(self):
        """Update statistics display"""
        total = len(self.matches)
        filtered = len(self.filtered_matches)
        complete = len([m for m in self.matches if m.status == "complete"])
        incomplete = total - complete
        
        self.stats_text.value = (
            f"Total: {total} | Filtered: {filtered} | "
            f"Complete: {complete} | Incomplete: {incomplete}"
        )
    
    def export_data(self, e=None):
        """Export filtered data to JSON"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"exported_matches_{timestamp}.json"
            
            export_data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_matches": len(self.filtered_matches),
                    "filters_applied": {
                        "status": self.status_filter,
                        "country": self.country_filter,
                        "league": self.league_filter
                    }
                },
                "matches": [match.to_dict() for match in self.filtered_matches]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self._show_success(f"Data exported to {filename}")
        except Exception as e:
            self._show_error(f"Failed to export data: {e}")
    
    def _show_error(self, message: str):
        """Show error message"""
        # This could be enhanced with a proper notification system
        pass
    
    def _show_success(self, message: str):
        """Show success message"""
        # This could be enhanced with a proper notification system
        pass
    
    def build(self):
        return ft.Container(
            content=ft.Column([
                # Header with controls
                ft.Row([
                    ft.Text("Results", weight=ft.FontWeight.BOLD, size=14),
                    ft.Container(expand=True),
                    self.refresh_button,
                    self.export_button,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                # Statistics
                self.stats_text,
                
                # Filters
                ft.Container(
                    content=ft.Row([
                        self.status_dropdown,
                        self.country_field,
                        self.league_field,
                    ], spacing=10),
                    margin=ft.margin.only(bottom=15)
                ),
                
                # Main content area
                ft.Row([
                    # Results table
                    ft.Container(
                        content=self.results_table,
                        expand=2,
                    ),
                    
                    # Details panel
                    self.details_panel,
                ], spacing=20, expand=True),
            ], spacing=15),
            padding=20,
            expand=True
        )
