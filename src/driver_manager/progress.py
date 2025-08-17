from typing import Optional
import time
from tqdm import tqdm

class DownloadProgress:
    """Visual progress tracking for downloads using tqdm"""
    
    def __init__(self):
        self.pbar: Optional[tqdm] = None
        self.start_time: float = 0.0
        
    def init(self, total_size: int, desc: str) -> None:
        """Initialize progress bar with ETA calculation"""
        self.start_time = time.time()
        self.pbar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=desc,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{rate_fmt}, ETA: {remaining}]',
            miniters=1
        )
        
    def update(self, chunk_size: int) -> None:
        """Update progress with downloaded chunk"""
        if self.pbar:
            self.pbar.update(chunk_size)
            
    def close(self) -> None:
        """Clean up progress bar"""
        if self.pbar:
            self.pbar.close()
            self.pbar = None
