#!/usr/bin/env python3
"""
Railway scraper runner — headless, non-interactive, designed for cron.

Usage:
    python run_scraper_railway.py [--day Today|Tomorrow] [--webhook-url URL] [--api-key KEY]

Environment variables:
    SCOREWISE_WEBHOOK_URL  - ScoreWise ingestion endpoint (overrides --webhook-url)
    SCOREWISE_API_KEY      - API key for ingestion (overrides --api-key)
    SCRAPER_LOG_LEVEL      - Log level (default: INFO)

- Runs the scraper headlessly with config.ci.json
- Outputs JSON to output/json/
- Optionally POSTs results to ScoreWise
- Exits 0 on success, 1 on failure
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scraper import FlashscoreScraper, get_ddmmyy_date
from src.storage.json_storage import JSONStorage
from src.utils.config_loader import CONFIG

# Import shared webhook utilities (replaces local _transform_payload / post_to_webhook)
from webhook_utils import post_to_webhook

log_level = os.environ.get("SCRAPER_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("railway_runner")


def apply_railway_config():
    """Apply Railway-optimized config on top of the default config."""
    config_path = os.path.join(os.path.dirname(__file__), "config.ci.json")
    if os.path.exists(config_path):
        import shutil
        target = os.path.join(os.path.dirname(__file__), "src", "config.json")
        shutil.copy2(config_path, target)
        logger.info("Applied Railway config (config.ci.json → src/config.json)")
    else:
        logger.warning("config.ci.json not found; using default config")


def main():
    parser = argparse.ArgumentParser(description="Railway scraper runner")
    parser.add_argument(
        "--day",
        default="Today",
        choices=["Today", "Tomorrow"],
        help="Which day to scrape (default: Today)",
    )
    parser.add_argument(
        "--webhook-url",
        default=None,
        help="ScoreWise ingestion endpoint URL",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for the ingestion endpoint",
    )
    args = parser.parse_args()

    # Environment variables override CLI args
    webhook_url = os.environ.get("SCOREWISE_WEBHOOK_URL", args.webhook_url)
    api_key = os.environ.get("SCOREWISE_API_KEY", args.api_key)

    # ── Apply Railway config ────────────────────────────────────
    apply_railway_config()

    # Reload CONFIG after applying Railway config
    # (config_loader caches, so we need to re-import)
    import importlib
    from src.utils import config_loader as cl
    importlib.reload(cl)
    from src.utils.config_loader import CONFIG as RAILWAY_CONFIG

    # ── Run the scraper ─────────────────────────────────────────
    logger.info(f"Starting scraper for {args.day} ...")
    scraper = FlashscoreScraper()
    try:
        result = scraper.scrape(day=args.day)
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)
    finally:
        try:
            scraper.close()
        except Exception:
            pass

    total = result.get("total_collected", 0) if result else 0
    complete = result.get("complete_matches", 0) if result else 0
    incomplete = result.get("incomplete_matches", 0) if result else 0

    logger.info(
        f"Done. Total: {total}, Complete: {complete}, Incomplete: {incomplete}"
    )

    # ── Find the output JSON ─────────────────────────────────────
    file_date = get_ddmmyy_date(args.day)
    json_path = Path("output/json") / f"matches_{file_date}.json"

    if not json_path.exists():
        logger.error(f"Output file not found: {json_path}")
        sys.exit(1)

    logger.info(f"Output: {json_path} ({json_path.stat().st_size} bytes)")

    # ── POST to webhook if configured ────────────────────────────
    if webhook_url:
        ok = post_to_webhook(json_path, webhook_url, api_key)
        if not ok:
            logger.warning("Webhook delivery failed; JSON is still saved locally.")
    else:
        logger.info("No webhook URL configured; JSON saved locally only.")

    # ── Summary ──────────────────────────────────────────────────
    summary = (
        f"Scraper Results\n"
        f"  Day: {args.day}\n"
        f"  Total matches: {total}\n"
        f"  Complete: {complete}\n"
        f"  Incomplete: {incomplete}\n"
        f"  Output: {json_path}\n"
    )
    print(summary)

    sys.exit(0)


if __name__ == "__main__":
    main()
