import flet as ft
from src.ui.components.results_view import ResultsView

class ResultsPage:
    def __init__(self, on_navigate: callable = None, page: ft.Page = None):
        self.on_navigate = on_navigate
        self.page = page
        self.results_view = ResultsView(on_match_select=self._on_match_select)
        self.back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=ft.Colors.GREY_400,
            tooltip="Back to Home",
            on_click=self._on_back_click
        )
        self.scraper_button = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            icon_color=ft.Colors.GREEN_400,
            tooltip="Start Scraper",
            on_click=self._on_scraper_click
        )
        self.settings_button = ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_color=ft.Colors.GREY_400,
            tooltip="Settings",
            on_click=self._on_settings_click
        )
    def _on_back_click(self, e):
        """Handle back button click"""
        self._navigate_to("home")
    def _on_scraper_click(self, e):
        """Handle scraper button click"""
        self._navigate_to("scraper")
    def _on_settings_click(self, e):
        """Handle settings button click"""
        self._navigate_to("settings")
    def _navigate_to(self, page: str):
        if self.on_navigate:
            self.on_navigate(page)
    def _on_match_select(self, match):
        pass
    def refresh_data(self):
        self.results_view.refresh_data()
    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    self.back_button,
                    ft.Text("Results", weight=ft.FontWeight.BOLD, size=18),
                    ft.Container(expand=True),
                    self.scraper_button,
                    self.settings_button,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.results_view.build(),
            ], spacing=20),
            padding=20,
            expand=True
        )
