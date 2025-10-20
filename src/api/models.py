from typing import Literal, Optional, Dict, Any, List
from pydantic import BaseModel, Field


class StartScrapeRequest(BaseModel):
    day: str = Field(default="Today", description="Day to scrape, e.g., 'Today' or '2025-10-14'")
    # Optional overrides for common settings
    headless: Optional[bool] = Field(default=None)
    max_matches: Optional[int] = Field(default=None)
    max_tabs: Optional[int] = Field(default=None)
    disable_images: Optional[bool] = Field(default=None)
    proxy: Optional[str] = Field(default=None)
    base_batch_size: Optional[int] = Field(default=None)


class JobInfo(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    detail: Optional[str] = None


class StartScrapeResponse(BaseModel):
    job: JobInfo


class JobStatusResponse(BaseModel):
    job: JobInfo


class ResultFileMetadata(BaseModel):
    filename: str
    size_bytes: int
    last_update: Optional[str] = None


class ResultsListResponse(BaseModel):
    files: List[ResultFileMetadata]


class ResultsFileResponse(BaseModel):
    filename: str
    data: Dict[str, Any]


class StartResultsRequest(BaseModel):
    date: str = Field(..., description="Date string in format 'dd.mm.yyyy' matching file naming, e.g., '12.10.2025'")



