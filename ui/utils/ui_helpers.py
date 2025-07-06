import flet as ft
from typing import Optional, Callable

def create_card(title: str, content: ft.Control, color: str = ft.Colors.GREY_900) -> ft.Container:
    """Create a styled card container"""
    return ft.Container(
        content=ft.Column([
            ft.Text(title, weight=ft.FontWeight.BOLD, size=14),
            content,
        ], spacing=10),
        padding=15,
        bgcolor=color,
        border_radius=8,
        margin=ft.margin.only(bottom=15)
    )

def create_button(
    text: str, 
    icon: Optional[str] = None, 
    color: str = ft.Colors.BLUE_600,
    on_click: Optional[Callable] = None,
    width: Optional[int] = None
) -> ft.ElevatedButton:
    """Create a styled button"""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            color=ft.Colors.WHITE,
            bgcolor=color,
        ),
        width=width,
        on_click=on_click
    )

def create_icon_button(
    icon: str,
    color: str = ft.Colors.GREY_400,
    tooltip: Optional[str] = None,
    on_click: Optional[Callable] = None
) -> ft.IconButton:
    """Create a styled icon button"""
    return ft.IconButton(
        icon=icon,
        icon_color=color,
        tooltip=tooltip,
        on_click=on_click
    )

def create_text_field(
    label: str,
    value: str = "",
    width: Optional[int] = None,
    on_change: Optional[Callable] = None,
    keyboard_type: Optional[ft.KeyboardType] = None
) -> ft.TextField:
    """Create a styled text field"""
    return ft.TextField(
        label=label,
        value=value,
        width=width,
        on_change=on_change,
        keyboard_type=keyboard_type,
        border_radius=8,
        border_color=ft.Colors.GREY_700,
        focused_border_color=ft.Colors.BLUE_400,
    )

def create_dropdown(
    label: str,
    options: list,
    value: Optional[str] = None,
    width: Optional[int] = None,
    on_change: Optional[Callable] = None
) -> ft.Dropdown:
    """Create a styled dropdown"""
    return ft.Dropdown(
        label=label,
        options=options,
        value=value,
        width=width,
        on_change=on_change,
        border_radius=8,
        border_color=ft.Colors.GREY_700,
        focused_border_color=ft.Colors.BLUE_400,
    )

def create_switch(
    label: str,
    value: bool = False,
    on_change: Optional[Callable] = None
) -> ft.Switch:
    """Create a styled switch"""
    return ft.Switch(
        label=label,
        value=value,
        on_change=on_change,
        active_color=ft.Colors.GREEN_400
    )

def create_progress_bar(
    value: float = 0.0,
    visible: bool = True,
    color: str = ft.Colors.BLUE_400
) -> ft.ProgressBar:
    """Create a styled progress bar"""
    return ft.ProgressBar(
        value=value,
        visible=visible,
        color=color,
        bgcolor=ft.Colors.GREY_300,
    )

def create_data_table(
    columns: list,
    rows: list = None,
    border_color: str = ft.Colors.GREY_700
) -> ft.DataTable:
    """Create a styled data table"""
    return ft.DataTable(
        columns=columns,
        rows=rows or [],
        border=ft.border.all(1, border_color),
        border_radius=8,
        vertical_lines=ft.border.BorderSide(1, border_color),
        horizontal_lines=ft.border.BorderSide(1, border_color),
        column_spacing=20,
    )

def create_status_indicator(
    status: str,
    color: str = ft.Colors.GREY_400,
    icon: str = ft.Icons.CIRCLE
) -> ft.Container:
    """Create a status indicator"""
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, color=color, size=12),
            ft.Text(status, color=color, size=12)
        ], spacing=5),
        padding=10,
        bgcolor=ft.Colors.GREY_900,
        border_radius=8
    )

def create_notification(
    message: str,
    type: str = "info",  # info, success, warning, error
    duration: int = 3000
) -> ft.Banner:
    """Create a notification banner"""
    colors = {
        "info": ft.Colors.BLUE_400,
        "success": ft.Colors.GREEN_400,
        "warning": ft.Colors.ORANGE_400,
        "error": ft.Colors.RED_400
    }
    
    icons = {
        "info": ft.Icons.INFO,
        "success": ft.Icons.CHECK_CIRCLE,
        "warning": ft.Icons.WARNING,
        "error": ft.Icons.ERROR
    }
    
    return ft.Banner(
        bgcolor=ft.Colors.GREY_900,
        leading=ft.Icon(icons.get(type, ft.Icons.INFO), color=colors.get(type, ft.Colors.BLUE_400)),
        content=ft.Text(message, color=ft.Colors.WHITE),
        actions=[
            ft.TextButton("Dismiss", on_click=lambda e: e.control.close()),
        ],
    )

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(seconds: int) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"

def create_loading_spinner() -> ft.ProgressRing:
    """Create a loading spinner"""
    return ft.ProgressRing(
        color=ft.Colors.BLUE_400,
        stroke_width=3,
    )

def create_empty_state(
    icon: str,
    title: str,
    message: str,
    action_button: Optional[ft.Control] = None
) -> ft.Container:
    """Create an empty state display"""
    content = ft.Column([
        ft.Icon(icon, size=64, color=ft.Colors.GREY_400),
        ft.Text(title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Text(message, size=14, color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER),
    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    if action_button:
        content.controls.append(action_button)
    
    return ft.Container(
        content=content,
        padding=40,
        alignment=ft.alignment.center,
    )
