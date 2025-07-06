import flet as ft
import json
from pathlib import Path
from typing import Dict, Any
from src.config import ScraperConfig

class SettingsPage:
    def __init__(self, on_settings_save: callable = None, page: ft.Page = None):
        self.on_settings_save = on_settings_save
        self.page = page
        self.config = ScraperConfig()
        self.load_config()
        
        # UI Components
        self.save_button = ft.ElevatedButton(
            "Save Settings",
            icon=ft.Icons.SAVE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
            ),
            on_click=self._on_save_click
        )
        
        self.reset_button = ft.OutlinedButton(
            "Reset to Defaults",
            icon=ft.Icons.RESTORE,
            on_click=self._on_reset_click
        )
        
        # Browser settings
        self.headless_switch = ft.Switch(
            label="Headless Mode",
            value=self.config.browser.headless,
            active_color=ft.Colors.GREEN_400
        )
        
        self.window_width_field = ft.TextField(
            label="Window Width",
            value=str(self.config.browser.window_size[0]),
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.window_height_field = ft.TextField(
            label="Window Height",
            value=str(self.config.browser.window_size[1]),
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.disable_images_switch = ft.Switch(
            label="Disable Images",
            value=self.config.browser.disable_images,
            active_color=ft.Colors.GREEN_400
        )
        
        # Timeout settings
        self.page_load_timeout_field = ft.TextField(
            label="Page Load Timeout (seconds)",
            value=str(self.config.timeout.page_load_timeout),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.element_timeout_field = ft.TextField(
            label="Element Timeout (seconds)",
            value=str(self.config.timeout.element_timeout),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.retry_delay_field = ft.TextField(
            label="Retry Delay (seconds)",
            value=str(self.config.timeout.retry_delay),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.max_retries_field = ft.TextField(
            label="Max Retries",
            value=str(self.config.timeout.max_retries),
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Output settings
        self.output_dir_field = ft.TextField(
            label="Output Directory",
            value=self.config.output.directory,
            width=200
        )
        
        self.log_level_dropdown = ft.Dropdown(
            label="Log Level",
            width=120,
            options=[
                ft.dropdown.Option("DEBUG", "Debug"),
                ft.dropdown.Option("INFO", "Info"),
                ft.dropdown.Option("WARNING", "Warning"),
                ft.dropdown.Option("ERROR", "Error"),
            ],
            value=self.config.logging.log_level
        )
        
        # Batch processing settings
        self.batch_size_field = ft.TextField(
            label="Batch Size",
            value=str(self.config.batch.base_batch_size),
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.base_delay_field = ft.TextField(
            label="Base Delay (seconds)",
            value=str(self.config.batch.base_delay),
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.adaptive_delay_switch = ft.Switch(
            label="Adaptive Delay",
            value=self.config.batch.adaptive_delay,
            active_color=ft.Colors.GREEN_400
        )
        
        # Status message
        self.status_text = ft.Text(
            "",
            color=ft.Colors.GREY_400,
            size=12
        )
    
    def load_config(self):
        """Load configuration from file or use defaults"""
        try:
            config_path = Path("config.json")
            if config_path.exists():
                self.config = ScraperConfig.load("config.json")
        except Exception as e:
            print(f"Error loading config: {e}")
            # Use default config
    
    def _on_save_click(self, e):
        """Save current settings to configuration"""
        try:
            # Update browser settings
            self.config.browser.headless = self.headless_switch.value
            self.config.browser.window_size = (
                int(self.window_width_field.value or 1920),
                int(self.window_height_field.value or 1080)
            )
            self.config.browser.disable_images = self.disable_images_switch.value
            
            # Update timeout settings
            self.config.timeout.page_load_timeout = int(self.page_load_timeout_field.value or 30)
            self.config.timeout.element_timeout = int(self.element_timeout_field.value or 10)
            self.config.timeout.retry_delay = int(self.retry_delay_field.value or 5)
            self.config.timeout.max_retries = int(self.max_retries_field.value or 3)
            
            # Update output settings
            self.config.output.directory = self.output_dir_field.value or "output"
            self.config.logging.log_level = self.log_level_dropdown.value or "INFO"
            
            # Update batch settings
            self.config.batch.base_batch_size = int(self.batch_size_field.value or 2)
            self.config.batch.base_delay = float(self.base_delay_field.value or 3.0)
            self.config.batch.adaptive_delay = self.adaptive_delay_switch.value
            
            # Save to file
            self.config.save("config.json")
            
            self.status_text.value = "Settings saved successfully!"
            self.status_text.color = ft.Colors.GREEN_400
            
            # Notify parent
            if self.on_settings_save:
                self.on_settings_save(self.config)
                
        except Exception as e:
            self.status_text.value = f"Error saving settings: {e}"
            self.status_text.color = ft.Colors.RED_400
        
        # Update the UI
        if self.page:
            self.page.update()
        
    def _on_reset_click(self, e):
        """Reset settings to defaults"""
        try:
            # Create new default config
            self.config = ScraperConfig()
            
            # Update UI components
            self.headless_switch.value = self.config.browser.headless
            self.window_width_field.value = str(self.config.browser.window_size[0])
            self.window_height_field.value = str(self.config.browser.window_size[1])
            self.disable_images_switch.value = self.config.browser.disable_images
            
            self.page_load_timeout_field.value = str(self.config.timeout.page_load_timeout)
            self.element_timeout_field.value = str(self.config.timeout.element_timeout)
            self.retry_delay_field.value = str(self.config.timeout.retry_delay)
            self.max_retries_field.value = str(self.config.timeout.max_retries)
            
            self.output_dir_field.value = self.config.output.directory
            self.log_level_dropdown.value = self.config.logging.log_level
            
            self.batch_size_field.value = str(self.config.batch.base_batch_size)
            self.base_delay_field.value = str(self.config.batch.base_delay)
            self.adaptive_delay_switch.value = self.config.batch.adaptive_delay
            
            self.status_text.value = "Settings reset to defaults"
            self.status_text.color = ft.Colors.BLUE_400
            
        except Exception as e:
            self.status_text.value = f"Error resetting settings: {e}"
            self.status_text.color = ft.Colors.RED_400
        
        # Update the UI
        if self.page:
            self.page.update()
    
    def build(self):
        return ft.Container(
            content=ft.Column([
                # Sticky header with Save/Reset
                ft.Container(
                    content=ft.Row([
                        ft.Text("Settings", weight=ft.FontWeight.BOLD, size=22),
                        ft.Container(expand=True),
                        self.save_button,
                        self.reset_button,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(top=10, bottom=10),
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=8,
                    shadow=ft.BoxShadow(blur_radius=4, color=ft.Colors.GREY_900, offset=ft.Offset(0, 2)),
                ),
                self.status_text,
                ft.Divider(height=20, color=ft.Colors.GREY_800),
                # Settings sections
                ft.Container(
                    content=ft.Column([
                        # Browser Settings
                        ft.Text("Browser Settings", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(
                            content=ft.Row([
                                ft.Column([
                                    self.headless_switch,
                                    ft.Row([
                                        self.window_width_field,
                                        self.window_height_field,
                                    ], spacing=10),
                                ], spacing=10),
                                ft.Container(expand=True),
                                self.disable_images_switch,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=15,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=8,
                            margin=ft.margin.only(bottom=20)
                        ),
                        ft.Divider(height=10, color=ft.Colors.GREY_800),
                        # Timeout Settings
                        ft.Text("Timeout Settings", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    self.page_load_timeout_field,
                                    self.element_timeout_field,
                                ], spacing=10),
                                ft.Row([
                                    self.retry_delay_field,
                                    self.max_retries_field,
                                ], spacing=10),
                            ], spacing=10),
                            padding=15,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=8,
                            margin=ft.margin.only(bottom=20)
                        ),
                        ft.Divider(height=10, color=ft.Colors.GREY_800),
                        # Output Settings
                        ft.Text("Output Settings", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    self.output_dir_field,
                                    self.log_level_dropdown,
                                ], spacing=10),
                            ], spacing=10),
                            padding=15,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=8,
                            margin=ft.margin.only(bottom=20)
                        ),
                        ft.Divider(height=10, color=ft.Colors.GREY_800),
                        # Batch Processing Settings
                        ft.Text("Batch Processing Settings", weight=ft.FontWeight.BOLD, size=16),
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    self.batch_size_field,
                                    self.base_delay_field,
                                ], spacing=10),
                                ft.Row([
                                    self.adaptive_delay_switch,
                                ]),
                            ], spacing=10),
                            padding=15,
                            bgcolor=ft.Colors.GREY_900,
                            border_radius=8,
                        ),
                    ], spacing=20),
                    expand=True
                ),
            ], spacing=20),
            padding=20,
            expand=True
        )
