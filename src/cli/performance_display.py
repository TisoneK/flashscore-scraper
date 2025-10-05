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
        self.alert_message = None
        self.alert_type = "info"
        self.lock = Lock()
        
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
        
        # Create the body layout with metrics and progress
        self.layout["body"].split_row(
            Layout(self._render_metrics(), name="metrics", ratio=1),
            Layout(self._render_progress(), name="progress", ratio=2)
        )
        
        # Ensure all panels have proper borders and titles
        self.layout["header"].update(self._render_header())
        self.layout["body"]["metrics"].update(self._render_metrics())
        self.layout["body"]["progress"].update(self._render_progress())
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
        task_panel = Panel(Text(self.current_task or "--", style="bold white"), title="[bold blue]Current Task", border_style="blue")
        controls_panel = self._render_controls()
        # Stack vertically using split
        progress_stack = Layout(name="progress_stack")
        progress_stack.split(
            Layout(progress_panel, size=4),
            Layout(batch_panel, size=4),
            Layout(task_panel, size=3),
            Layout(controls_panel, size=8)  # Increased from 3 to 8 for more width
        )
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
        self.layout["body"]["metrics"].update(self._render_metrics())
        self.layout["body"]["progress"].update(self._render_progress())
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

    def update_current_task(self, task: str):
        with self.lock:
            self.current_task = task
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
            logger.error(f"Error in display loop: {e}")
            raise
        finally:
            if self._live is not None:
                try:
                    self._live.__exit__(None, None, None)
                except Exception as e:
                    logger.error(f"Error stopping live display: {e}")
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