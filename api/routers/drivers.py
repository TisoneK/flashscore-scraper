"""drivers.py router

Browser driver management endpoints.

Endpoints:
  GET  /api/drivers/versions  — list available ChromeDriver versions
  POST /api/drivers/install   — install ChromeDriver or GeckoDriver

Extracted from api_server.py during the api modularization.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.schemas import DriverInstallRequest
from src.driver_manager.driver_installer import DriverInstaller

logger = logging.getLogger("api_server")
router = APIRouter()


@router.get("/drivers/versions")
async def list_driver_versions():
    """List available ChromeDriver versions.

    Mirrors the CLI's ``--list-versions`` flag.
    """
    installer = DriverInstaller()
    try:
        versions = installer.get_available_versions()
        # Extract just the version strings
        version_strings = [v["version"] for v in versions] if versions else []
        return {"versions": version_strings[:100], "total": len(version_strings)}
    except Exception as exc:
        raise HTTPException(500, f"Failed to fetch Chrome versions: {exc}")


@router.post("/drivers/install")
async def install_drivers(req: DriverInstallRequest):
    """Install browser drivers.

    Mirrors the CLI's ``--install-drivers [browser [version]]`` flag.
    Installs ChromeDriver (default) or GeckoDriver for Firefox.
    """
    if req.browser not in ("chrome", "firefox"):
        raise HTTPException(422, "browser must be 'chrome' or 'firefox'")

    try:
        installer = DriverInstaller()
        if req.browser == "firefox":
            result = installer.install_firefox_driver(version=req.version)
        else:
            result = installer.install_chrome_driver(version=req.version)
        return {
            "status": "ok",
            "browser": req.browser,
            "version": req.version or "latest",
            "message": f"{req.browser} driver installed",
            "details": str(result),
        }
    except Exception as exc:
        raise HTTPException(500, f"Driver installation failed: {exc}")
