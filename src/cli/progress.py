from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from contextlib import contextmanager

class ProgressManager:
    @contextmanager
    def scraping_progress(self):
        """Context manager for scraping progress with rich formatting."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=None,  # Use default console
            transient=False
        ) as progress:
            yield progress 