import flet as ft
import threading
import time
from typing import Dict, Any

from ui.pages.home_page import HomePage
from ui.pages.scraper_page import ScraperPage
from ui.pages.results_page import ResultsPage
from ui.pages.settings_page import SettingsPage

class FlashscoreScraperApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_page = "home"
        self.pages = {}
        # Initialize pages (will be refactored to use build())
        self.pages["home"] = HomePage(on_navigate=self.navigate_to, page=page)
        self.pages["scraper"] = ScraperPage(on_navigate=self.navigate_to, page=page)
        self.pages["results"] = ResultsPage(on_navigate=self.navigate_to, page=page)
        self.pages["settings"] = SettingsPage(on_settings_save=self.on_settings_save, page=page)
        self.navigation_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Home",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PLAY_ARROW_OUTLINED,
                    selected_icon=ft.Icons.PLAY_ARROW,
                    label="Scraper",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.TABLE_CHART_OUTLINED,
                    selected_icon=ft.Icons.TABLE_CHART,
                    label="Results",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Settings",
                ),
            ],
            on_change=self.navigation_change,
        )
        self.content_area = ft.Container(
            content=ft.Column([
                self.pages["home"].build()
            ], expand=True, scroll=ft.ScrollMode.AUTO),
            expand=True,
        )
        self.status_bar = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.GREEN_400, size=12),
                ft.Text("Ready", color=ft.Colors.GREY_400, size=12),
                ft.Container(expand=True),
                ft.Text("Flashscore Scraper v1.0", color=ft.Colors.GREY_400, size=12),
            ], spacing=5),
            padding=10,
            bgcolor=ft.Colors.GREY_900,
            border=ft.border.only(top=ft.border.BorderSide(1, ft.Colors.GREY_700))
        )
        self.refresh_timer = None
        self.start_auto_refresh()
    def navigation_change(self, e):
        page_map = {0: "home", 1: "scraper", 2: "results", 3: "settings"}
        selected_page = page_map.get(e.control.selected_index, "home")
        self.navigate_to(selected_page)
    def navigate_to(self, page: str):
        if page not in self.pages:
            return
        self.current_page = page
        page_to_index = {"home": 0, "scraper": 1, "results": 2, "settings": 3}
        self.navigation_rail.selected_index = page_to_index.get(page, 0)
        # Update the Column's controls for content_area
        if isinstance(self.content_area.content, ft.Column):
            self.content_area.content.controls.clear()
            self.content_area.content.controls.append(self.pages[page].build())
        else:
            self.content_area.content = ft.Column([
                self.pages[page].build()
            ], expand=True, scroll=ft.ScrollMode.AUTO)
        self.page.update()
        if page == "home":
            self.pages["home"].refresh_stats()
        elif page == "results":
            self.pages["results"].refresh_data()
    def on_settings_save(self, config):
        self.update_status("Settings updated", ft.Colors.BLUE_400)
        if self.current_page == "home":
            self.pages["home"].refresh_stats()
    def update_status(self, status: str, color: str = ft.Colors.GREY_400):
        self.status_bar.content.controls[0].color = color
        self.status_bar.content.controls[1].value = status
        self.page.update()
    def start_auto_refresh(self):
        def refresh_loop():
            while True:
                try:
                    if self.current_page == "home":
                        self.pages["home"].refresh_stats()
                    time.sleep(30)
                except:
                    time.sleep(5)
        self.refresh_timer = threading.Thread(target=refresh_loop, daemon=True)
        self.refresh_timer.start()
    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    self.navigation_rail,
                    ft.VerticalDivider(width=1),
                    self.content_area,
                ], expand=True),
                self.status_bar,
            ]),
            expand=True
        )

def main(page: ft.Page):
    page.title = "Flashscore Scraper"
    page.window_width = 1400
    page.window_height = 900
    page.window_resizable = True
    page.window_maximized = True
    page.theme_mode = ft.ThemeMode.DARK
    page.appbar = ft.AppBar(
        title=ft.Text("Flashscore Scraper", weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.Colors.GREY_900,
        elevation=0,
    )
    app = FlashscoreScraperApp(page)
    page.add(app.build())
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
