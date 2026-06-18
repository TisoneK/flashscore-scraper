"""schemas.py

Pydantic models for the scraper API's request/response bodies.

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Scrape ──────────────────────────────────────────────────────────


class ScrapeRequest(BaseModel):
    day: str = Field("Today", description="Which day: 'Today' or 'Tomorrow'")


class ScrapeResponse(BaseModel):
    status: str
    message: str
    scrape_id: Optional[str] = None


class ResultsScrapeRequest(BaseModel):
    date: str = Field(
        ...,
        description="Date in DD.MM.YYYY format, e.g. '13.06.2025'",
        pattern=r"^\d{2}\.\d{2}\.\d{4}$",
    )


# ── Config (legacy file-based) ──────────────────────────────────────


class ConfigUpdateRequest(BaseModel):
    config: dict = Field(
        ..., description="Partial or full config to merge into src/config.json"
    )


# ── Schedule ────────────────────────────────────────────────────────


class ScheduleConfigRequest(BaseModel):
    enabled: bool = Field(False, description="Enable recurring scraping")
    interval_minutes: int = Field(
        60, ge=15, le=1440, description="Interval between scrapes (min)"
    )
    day: str = Field("Today", description="Day to scrape: 'Today' or 'Tomorrow'")
    start_time: Optional[str] = Field(
        None,
        description="Start time HH:MM or null for immediate",
        pattern=r"^\d{2}:\d{2}$|^$",
    )


# ── Drivers ─────────────────────────────────────────────────────────


class DriverInstallRequest(BaseModel):
    browser: str = Field("chrome", description="'chrome' or 'firefox'")
    version: Optional[str] = Field(
        None, description="Major version, e.g. '138'. Default = latest"
    )


# ── Init / Results ──────────────────────────────────────────────────


class InitProjectRequest(BaseModel):
    browser: str = Field("chrome", description="'chrome' or 'firefox'")
    version: Optional[str] = Field(
        None, description="Driver major version, e.g. '138'"
    )


class ResultsUpdateRequest(BaseModel):
    json_file: str = Field(
        ...,
        description="Path to JSON results file (absolute or relative to project root)",
    )
    output: Optional[str] = Field(None, description="Optional output CSV path")


# ── Env-config ──────────────────────────────────────────────────────


class EnvConfigEntry(BaseModel):
    key: str
    value: str  # masked if secret
    has_override: bool
    is_secret: bool
    description: Optional[str] = None
    env_var: Optional[str] = None


class EnvConfigListResponse(BaseModel):
    configs: List[EnvConfigEntry]
    total: int


class EnvConfigUpdateRequest(BaseModel):
    updates: Dict[str, str] = Field(
        ...,
        description="Key → value. Empty value removes override.",
    )


class EnvConfigUpdateResponse(BaseModel):
    updated: List[str] = []
    removed: List[str] = []
    failed: Dict[str, str] = {}


# ── Logs ────────────────────────────────────────────────────────────


class LogEntry(BaseModel):
    timestamp: str  # ISO 8601 UTC
    level: str  # DEBUG / INFO / WARNING / ERROR / CRITICAL
    logger: str  # logger name (e.g. "api_server", "src.scraper", "uvicorn.access")
    message: str


class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int
    oldest: Optional[str] = None  # ISO 8601 timestamp of oldest entry in response
    newest: Optional[str] = None  # ISO 8601 timestamp of newest entry in response
