"""
Dynamic console display system for performance metrics and progress bars.

This module provides a sophisticated console output system that can update
performance metrics and progress bars without affecting other console items.
It uses ANSI escape codes for cursor positioning and screen management.
"""

import os
import sys
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import logging
# Simple color constants for ANSI escape codes
class Colors:
    """Simple color constants for console output."""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


@dataclass
class DisplayLine:
    """Represents a line in the dynamic display."""
    id: str
    content: str
    line_number: int
    is_permanent: bool = False
    last_update: float = 0.0


from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, ProgressColumn
from rich.align import Align
from rich.text import Text
from threading import Lock
import time
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque

class PerformanceDisplay:
    """
    Rich-based dynamic console display for performance metrics and progress bars.
    Features:
    - Persistent header and controls
    - Live-updating metrics and progress
    - Alerts panel (optional)
    - Thread-safe updates
    """
    def __init__(self):
        # Local logger to avoid NameError in exception handlers
        self._logger = logging.getLogger(__name__)
        self.console = Console()
        self.layout = Layout()
        self.metrics: Dict[str, Any] = {}
        self.progress_total = 100
        self.progress_current = 0
        self.progress_desc = ""
        self.batch_total = 0
        self.batch_current = 0
        self.batch_desc = ""
        self.current_task = ""
        self.current_match = ""
        self.subtasks = deque(maxlen=6)
        self.status_indicators: Dict[str, str] = {}
        self.schedule_label: str = ""
        self.schedule_next_text: str = ""
        self._schedule_next_dt: Optional[datetime] = None
        self.alert_message = None
        self.alert_type = "info"
        self.lock = Lock()
        self._last_schedule_refresh_ts = 0.0
        
        # Initialize progress bars first
        self._progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            expand=True,
            console=self.console,
            transient=False
        )
        self._progress_task = self._progress.add_task("Overall", total=100)
        self._batch_progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            expand=True,
            console=self.console,
            transient=False
        )
        self._batch_task = self._batch_progress.add_task("Batch", total=100)
        
        # Initialize controls before setting up layout
        self._stop_callback = None
        self._should_stop = False
        self._is_running = True
        self._live = None
        self._controls = [
            ("Pause/Resume", self._action_pause),
            ("Stop Scraper", self._action_stop),
            ("Show Help", self._action_help),
            ("Quit to Main Menu", self._action_quit),
            ("Refresh", self._action_refresh)
        ]
        self._selected_control = 0
        self._paused = False
        
        # Now setup the layout which depends on the progress bars and controls
        self._setup_layout()

    def set_stop_callback(self, callback: Callable[[], None]):
        self._stop_callback = callback

    def _setup_layout(self):
        # Create the main layout structure
        self.layout.split(
            Layout(self._render_header(), name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(self._render_alert(), name="alert", size=3)
        )
        
        # Create the body layout: left column holds Metrics (top) and Controls (below),
        # right column holds the progress and task stack
        self.layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(self._render_progress(), name="progress", ratio=2)
        )
        # Left column split to place Controls below Performance Metrics
        self.layout["body"]["left"].split(
            Layout(self._render_metrics(), name="metrics", size=16),
            Layout(name="status", size=3),
            Layout(self._render_controls(), name="controls", ratio=1)
        )
        
        # Ensure all panels have proper borders and titles
        self.layout["header"].update(self._render_header())
        self.layout["body"]["left"]["metrics"].update(self._render_metrics())
        self.layout["body"]["progress"].update(self._render_progress())
        self.layout["body"]["left"]["controls"].update(self._render_controls())
        self.layout["alert"].update(self._render_alert())

    def _render_header(self):
        return Panel(
            Align.center("Flashscore Scraper - Performance Monitor", vertical="middle"),
            style="bold cyan",
            title="[cyan]Flashscore Scraper"
        )

    def _render_metrics(self):
        table = Table.grid(padding=(0,1))
        table.add_column(justify="right", style="bold")
        table.add_column(justify="left")
        metrics = self.metrics.copy()
        # Helper for coloring percentages
        def _pct_color(p: float) -> str:
            try:
                if p >= 80:
                    return "red"
                if p >= 50:
                    return "yellow"
                return "green"
            except Exception:
                return "white"

        # Primary core metrics
        for key, label in [
            ("memory_usage", "Memory"),
            ("cpu_usage", "CPU"),
            ("active_workers", "Workers"),
            ("tasks_processed", "Tasks"),
            ("success_rate", "Success"),
            ("average_processing_time", "Avg Time")
        ]:
            value = metrics.get(key, "--")
            if key == "memory_usage" and value != "--":
                try:
                    mem_mb = float(value)
                    if mem_mb >= 1024:
                        value = f"{mem_mb/1024:.1f} GB"
                    else:
                        value = f"{mem_mb:.1f} MB"
                except Exception:
                    value = f"{value} MB"
            elif key == "cpu_usage" and value != "--":
                try:
                    cpu_pct = float(value)
                    color = _pct_color(cpu_pct)
                    value = Text(f"{cpu_pct:.1f}%", style=f"bold {color}")
                except Exception:
                    value = f"{value:.1f}%"
            elif key == "success_rate" and value != "--":
                try:
                    sr = float(value)
                    # For success rate, invert (higher is better)
                    color = "green" if sr >= 80 else ("yellow" if sr >= 50 else "red")
                    value = Text(f"{sr:.1f}%", style=f"bold {color}")
                except Exception:
                    value = f"{value:.1f}%"
            elif key == "average_processing_time" and value != "--":
                try:
                    v = float(value)
                    if v > 0 and v < 0.01:
                        v = 0.01
                    value = f"{v:.2f}s"
                except Exception:
                    value = f"{value:.2f}s"
            label_text = Text(f"{label}", style="bold cyan")
            value_text = value if isinstance(value, Text) else Text(str(value), style="bold white")
            table.add_row(label_text, value_text)

        # Expanded memory section if system stats are available
        try:
            sys_total = float(metrics.get("memory_system_total_mb", 0))
            sys_used = float(metrics.get("memory_system_used_mb", 0))
            sys_percent = float(metrics.get("memory_system_percent", 0))
            peak_mb = float(metrics.get("memory_peak_mb", 0))
            proc_mb = float(metrics.get("memory_usage", 0)) if metrics.get("memory_usage") is not None else 0.0
            if sys_total > 0:
                sys_free = max(0.0, sys_total - sys_used)
                # Helper for formatting MB/GB
                def fmt_mb(mb: float) -> str:
                    return f"{mb/1024:.1f} GB" if mb >= 1024 else f"{mb:.1f} MB"
                # System totals
                table.add_row(Text("System Total", style="bold cyan"), Text(fmt_mb(sys_total), style="bold white"))
                table.add_row(
                    Text("System Used", style="bold cyan"),
                    Text(f"{fmt_mb(sys_used)}  ({sys_percent:.1f}%)", style=f"bold {_pct_color(sys_percent)}")
                )
                table.add_row(Text("System Free", style="bold cyan"), Text(fmt_mb(sys_free), style="bold white"))
                # Process memory and peak
                if proc_mb > 0:
                    proc_pct = (proc_mb / sys_total) * 100.0
                    table.add_row(
                        Text("Scraper (RSS)", style="bold cyan"),
                        Text(f"{fmt_mb(proc_mb)}  ({proc_pct:.1f}% of total)", style=f"bold {_pct_color(proc_pct)}")
                    )
                if peak_mb > 0:
                    table.add_row(Text("Peak (RSS)", style="bold cyan"), Text(fmt_mb(peak_mb), style="bold white"))
        except Exception:
            pass
        return Panel(table, title="[bold magenta]Performance Metrics", border_style="magenta")

    def _render_progress(self):
        # Update progress bars
        self._progress.update(self._progress_task, completed=self.progress_current, total=max(self.progress_total,1), description=self.progress_desc or "Overall")
        self._batch_progress.update(self._batch_task, completed=self.batch_current, total=max(self.batch_total,1), description=self.batch_desc or "Batch")
        # Compose progress panels
        progress_panel = Panel(self._progress, title="[bold green]Overall Progress", border_style="green")
        batch_panel = Panel(self._batch_progress, title="[bold yellow]Batch Progress", border_style="yellow")

        # Build Current Task content: match header, subtasks list, and recent messages
        task_table = Table.grid(padding=(0,1))
        task_table.add_column(justify="left")

        # Match-level line
        header_line = self.current_task or self.current_match or "Waiting..."
        task_table.add_row(Text(str(header_line), style="bold white"))

        # Subtasks
        if self.subtasks:
            task_table.add_row(Text("", style="dim"))
            task_table.add_row(Text("Subtasks:", style="bold cyan"))
            for st in list(self.subtasks)[-6:]:
                task_table.add_row(Text(f"• {st}", style="white"))

        # Status indicators removed from Current Task panel (now rendered as a separate panel below)

        task_panel = Panel(task_table, title="[bold blue]Current Task", border_style="blue")
        # Optional schedule panel (separate, centered)
        schedule_panel = None
        if self.schedule_label or self.schedule_next_text:
            schedule_row = Table.grid(expand=True)
            schedule_row.add_column(justify="center")
            text_parts = []
            if self.schedule_label:
                text_parts.append(Text(f"Schedule: {self.schedule_label}", style="bold cyan"))
            if self.schedule_next_text:
                if text_parts:
                    text_parts.append(Text("  •  ", style="dim"))
                # Compute countdown if we have a parsed datetime
                countdown_suffix = ""
                try:
                    if self._schedule_next_dt:
                        remaining = int((self._schedule_next_dt - datetime.now()).total_seconds())
                        if remaining < 0:
                            remaining = 0
                        mins, secs = divmod(remaining, 60)
                        hours, mins = divmod(mins, 60)
                        if hours > 0:
                            countdown_suffix = f" (in {hours}h {mins}m {secs}s)"
                        else:
                            countdown_suffix = f" (in {mins}m {secs}s)"
                except Exception:
                    countdown_suffix = ""
                text_parts.append(Text(f"Next: {self.schedule_next_text}{countdown_suffix}", style="bold white"))
            if text_parts:
                schedule_line = Text()
                for part in text_parts:
                    schedule_line.append(part)
                schedule_row.add_row(schedule_line)
                # Use a distinct border color for the schedule panel for better visibility
                schedule_panel = Panel(schedule_row, title="[bold white]Schedule", border_style="cyan", expand=True)

        # Tip panel shown under schedule with guidance for terminal zoom
        tip_text = Text()
        tip_text.append("• If text appears too large or panels overlap, reduce terminal zoom with Ctrl + -\n", style="bold cyan")
        tip_text.append("• If text appears too small, increase terminal zoom with Ctrl + +", style="bold cyan")
        tip_panel = Panel(
            tip_text,
            title="[bold white]Tip",
            border_style="bright_black",
            expand=True
        )

        # Status panel now rendered in left column below metrics; omit here

        # Stack vertically using split
        progress_stack = Layout(name="progress_stack")
        # Compose the list of layouts in order
        # Make Current Task expand vertically to take remaining space

        layouts = [
            Layout(progress_panel, size=4),
            Layout(batch_panel, size=4),
            Layout(task_panel, ratio=1)
        ]
        if schedule_panel is not None:
            layouts.append(Layout(schedule_panel, size=3))
        # Always show the tip panel below schedule; give extra height for readability
        layouts.append(Layout(tip_panel, size=4))
        progress_stack.split(*layouts)
        return progress_stack

    def _action_pause(self):
        self._paused = not self._paused
        if self._paused:
            self.show_status("Scraping paused.")
        else:
            self.show_status("Scraping in progress...")

    def _action_stop(self):
        self.show_alert("Stopping scraper...", "error", persist=True)
        self._should_stop = True
        if self._stop_callback:
            self._stop_callback()

    def _action_help(self):
        self.show_alert("Use ↑/↓ to navigate, Enter to select. Actions: Pause, Stop, Help, Quit, Refresh.", "info")

    def _action_quit(self):
        self.show_alert("Quitting to main menu...", "warning", persist=True)
        self._should_stop = True
        if self._stop_callback:
            self._stop_callback()

    def _action_refresh(self):
        self.show_alert("Refreshed.", "info")
        self._refresh_layout()

    def _render_controls(self):
        controls = Text()
        for idx, (label, _) in enumerate(self._controls):
            prefix = " > " if idx == self._selected_control else "   "
            style = "bold white on blue" if idx == self._selected_control else "white"
            controls.append(f"{prefix}{label}\n", style=style)
        controls.append("\n[Use ↑/↓ to navigate, Enter to select]", style="dim")
        return Panel(controls, title="[bold white]Controls", border_style="white")

    def _render_alert(self):
        if not self.alert_message:
            return Panel("", title="", border_style="")
        color = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }.get(self.alert_type, "cyan")
        return Panel(Text(self.alert_message, style=f"bold {color}"), title=f"[bold]{self.alert_type.title()}[/bold]", border_style=color)

    def _refresh_layout(self):
        self.layout["header"].update(self._render_header())
        # Update all panels once to render initial state
        self.layout["body"]["left"]["metrics"].update(self._render_metrics())
        # Render status indicators between metrics and controls
        try:
            status_panel = None
            if self.status_indicators:
                def dot(state: str) -> Text:
                    state_l = (state or "").lower()
                    color = "green" if state_l in ("on", "ok", "healthy", "green") else ("yellow" if state_l in ("warn", "warning", "paused", "degraded", "yellow") else "red")
                    return Text("●", style=f"bold {color}")
                status_table = Table.grid(expand=True, padding=(0,1))
                items = list(self.status_indicators.items())
                if items:
                    for _ in items:
                        status_table.add_column(justify="center")
                    cells = []
                    for name, state in items:
                        cells.append(Text.assemble(dot(state), Text(f" {name}", style="bold white")))
                    status_table.add_row(*cells)
                    status_panel = Panel(status_table, title="[bold white]Status", border_style="bright_black", expand=True)
            self.layout["body"]["left"]["status"].update(status_panel or Panel("", border_style="bright_black"))
        except Exception:
            self.layout["body"]["left"]["status"].update(Panel("", border_style="bright_black"))
        self.layout["body"]["progress"].update(self._render_progress())
        self.layout["body"]["left"]["controls"].update(self._render_controls())
        self.layout["alert"].update(self._render_alert())

    def update_metrics(self, metrics: Dict[str, Any]):
        with self.lock:
            self.metrics.update(metrics)
            self._refresh_layout()

    def update_progress(self, current: int, total: int, description: Optional[str] = None):
        with self.lock:
            self.progress_current = current
            self.progress_total = total
            if description:
                self.progress_desc = description
            self._refresh_layout()

    def update_batch_progress(self, current: int, total: int, description: Optional[str] = None):
        with self.lock:
            self.batch_current = current
            self.batch_total = total
            if description:
                self.batch_desc = description
            self._refresh_layout()

    def reset_batch_progress(self, total: int, description: Optional[str] = None):
        """Reset the batch progress timer and counters by recreating the task.
        This ensures the elapsed time column reflects per-batch time.
        """
        with self.lock:
            try:
                if hasattr(self, "_batch_task"):
                    self._batch_progress.remove_task(self._batch_task)
            except Exception:
                pass
            # Recreate task with new total; completed starts at 0
            try:
                self._batch_task = self._batch_progress.add_task("Batch", total=max(int(total), 1))
            except Exception:
                # Fallback in case add_task fails
                self._batch_task = self._batch_progress.add_task("Batch", total=1)
            self.batch_current = 0
            self.batch_total = int(total) if total else 1
            if description:
                self.batch_desc = description
            self._refresh_layout()

    def update_current_task(self, task: str):
        with self.lock:
            self.current_task = task
            self._refresh_layout()

    def update_current_match(self, task: str):
        with self.lock:
            self.current_match = task
            self._refresh_layout()

    def clear_subtasks(self):
        with self.lock:
            self.subtasks.clear()
            self._refresh_layout()

    def add_subtask(self, subtask: str):
        with self.lock:
            if subtask:
                self.subtasks.append(subtask)
                self._refresh_layout()

    def update_status_indicators(self, indicators: Dict[str, str]):
        with self.lock:
            self.status_indicators = dict(indicators or {})
            self._refresh_layout()

    def update_schedule_info(self, label: Optional[str], next_text: Optional[str]):
        with self.lock:
            self.schedule_label = label or ""
            self.schedule_next_text = next_text or ""
            # Best-effort parse of next run time for countdown rendering
            self._schedule_next_dt = None
            try:
                if self.schedule_next_text and self.schedule_next_text.lower() != "now":
                    # Expecting format like 'YYYY-MM-DD HH:MM'
                    self._schedule_next_dt = datetime.strptime(self.schedule_next_text, '%Y-%m-%d %H:%M')
                else:
                    # Immediate run
                    self._schedule_next_dt = datetime.now()
            except Exception:
                self._schedule_next_dt = None
            self._refresh_layout()

    def add_message(self, message: str, level: str = "info"):
        with self.lock:
            if message:
                self.messages.append((message, level))
                self._refresh_layout()

    def show_alert(self, message: str, alert_type: str = "info", persist: bool = False, duration: float = 3.0):
        with self.lock:
            self.alert_message = message
            self.alert_type = alert_type
            self._refresh_layout()
            if not persist:
                # Auto-clear after duration seconds
                def clear():
                    time.sleep(duration)
                    with self.lock:
                        self.alert_message = None
                        self._refresh_layout()
                import threading
                threading.Thread(target=clear, daemon=True).start()

    def show_status(self, message: str):
        """Show a persistent status message in the alert panel."""
        self.show_alert(message, alert_type="info", persist=True)

    def start(self):
        """Start the display in a non-blocking way."""
        self._is_running = True
        
        # Initial render of all components
        self._refresh_layout()
        
        # Start the live display
        self._live = Live(
            self.layout, 
            refresh_per_second=4, 
            screen=True,
            redirect_stdout=False,
            redirect_stderr=False
        )
        
        try:
            self._live.__enter__()
            
            # Main update loop
            while self._is_running and not self._should_stop:
                self._update_display()
                time.sleep(0.1)  # More responsive to input
        except Exception as e:
            try:
                self._logger.error(f"Error in display loop: {e}")
            except Exception:
                pass
            raise
        finally:
            if self._live is not None:
                try:
                    self._live.__exit__(None, None, None)
                except Exception as e:
                    try:
                        self._logger.error(f"Error stopping live display: {e}")
                    except Exception:
                        pass
                finally:
                    self._live = None

    def stop(self):
        """Stop the display."""
        self._is_running = False
        if self._live is not None:
            self._live.__exit__(None, None, None)
            self._live = None

    def _update_display(self):
        """Handle keyboard input and update the display."""
        if not hasattr(self, '_live') or self._live is None:
            return
            
        key = None
        try:
            if os.name == 'nt':
                import msvcrt
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch == '\r':  # Enter
                        key = 'enter'
                    elif ch == '\xe0':  # Arrow keys
                        arrow = msvcrt.getwch()
                        if arrow == 'H':
                            key = 'up'
                        elif arrow == 'P':
                            key = 'down'
                    elif ch == '\x03':  # Ctrl+C
                        raise KeyboardInterrupt
            else:
                import sys, termios, tty, select
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    if select.select([sys.stdin], [], [], 0)[0]:
                        ch = sys.stdin.read(1)
                        if ch == '\n':
                            key = 'enter'
                        elif ch == '\x1b':  # Escape sequence
                            next1 = sys.stdin.read(1)
                            if next1 == '[':
                                next2 = sys.stdin.read(1)
                                if next2 == 'A':
                                    key = 'up'
                                elif next2 == 'B':
                                    key = 'down'
                        elif ch == '\x03':  # Ctrl+C
                            raise KeyboardInterrupt
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
            # Handle key presses
            if key == 'up':
                self._selected_control = (self._selected_control - 1) % len(self._controls)
                self._refresh_layout()
            elif key == 'down':
                self._selected_control = (self._selected_control + 1) % len(self._controls)
                self._refresh_layout()
            elif key == 'enter':
                _, action = self._controls[self._selected_control]
                action()
                self._refresh_layout()
                
        except KeyboardInterrupt:
            self.show_alert("Stopping (Ctrl+C)...", "error")
            self._should_stop = True
            if self._stop_callback:
                self._stop_callback() 
        finally:
            # Ensure the schedule countdown stays live by refreshing roughly once per second
            try:
                if self._schedule_next_dt is not None:
                    now_ts = time.time()
                    if now_ts - self._last_schedule_refresh_ts >= 1.0:
                        self._last_schedule_refresh_ts = now_ts
                        self._refresh_layout()
            except Exception:
                pass