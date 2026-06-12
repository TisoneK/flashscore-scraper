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
import json
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scraper import FlashscoreScraper
from src.storage.json_storage import JSONStorage
from src.utils.config_loader import CONFIG

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


def _convert_h2h_date(date_str: str) -> str:
    """Convert H2H date from DD/MM/YYYY to ISO 8601 (YYYY-MM-DD).

    The scraper stores H2H dates as 'DD/MM/YYYY' (e.g. '19/06/2025'), but
    the ScoreWise engine requires ISO 8601 format ('2025-06-19') for correct
    lexicographic sorting in winning-pattern analysis (s07).

    If the input does not match the expected format, it is returned unchanged
    so that a validation error is raised server-side rather than silently
    producing incorrect predictions.
    """
    if not date_str:
        return date_str
    import re
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(date_str))
    if m:
        day, month, year = m.groups()
        return f"{year}-{month}-{day}"
    return date_str


def _transform_payload(data: dict) -> dict:
    """Transform raw scraper output into a valid IngestRequest for ScoreWise.

    The engine's IngestRequest expects {source, scraped_at, matches} — the
    scraper's raw file uses {metadata, matches} which causes a 422 error.
    This function rebuilds the envelope, converts H2H dates to ISO 8601,
    filters to complete matches only, and strips undeclared fields that
    would break if the engine ever adds extra='forbid' to its schemas.
    """
    raw_matches = data.get("matches", [])

    # Incomplete matches lack odds and H2H data — they always fail validation
    complete_matches = [m for m in raw_matches if m.get("status") == "complete"]

    transformed_matches = []
    for match in complete_matches:
        m = {
            "match_id": match.get("match_id"),
            "home_team": match.get("home_team"),
            "away_team": match.get("away_team"),
        }

        # OddsSchema does not declare match_id — strip it to stay compatible
        odds = match.get("odds")
        if odds and isinstance(odds, dict):
            m["odds"] = {
                k: v for k, v in odds.items() if k != "match_id"
            }
        else:
            m["odds"] = odds

        # Convert dates to ISO 8601 and keep only fields the engine declares
        h2h = match.get("h2h_matches")
        if h2h and isinstance(h2h, list):
            cleaned_h2h = []
            for h in h2h:
                if not isinstance(h, dict):
                    continue
                cleaned = {
                    "home_team": h.get("home_team"),
                    "away_team": h.get("away_team"),
                    "home_score": h.get("home_score"),
                    "away_score": h.get("away_score"),
                    "date": _convert_h2h_date(h.get("date")),
                }
                cleaned_h2h.append(cleaned)
            m["h2h_matches"] = cleaned_h2h
        else:
            m["h2h_matches"] = h2h or []

        transformed_matches.append(m)

    # Rebuild envelope to match IngestRequest: {source, scraped_at, matches}
    payload = {
        "source": "flashscore-scraper",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "matches": transformed_matches,
    }

    logger.info(
        f"Transformed payload: {len(raw_matches)} raw → "
        f"{len(transformed_matches)} complete matches"
    )
    return payload


def post_to_webhook(json_path: Path, webhook_url: str, api_key: str = None):
    """POST the scraped JSON to a ScoreWise ingestion endpoint.

    The raw file is transformed into a valid IngestRequest before posting:
      - Auth header uses X-API-Key (not Bearer) per engine's FastAPI dependency.
      - Payload envelope is rebuilt as {source, scraped_at, matches}.
      - H2H dates are converted from DD/MM/YYYY to ISO 8601 (YYYY-MM-DD).
      - Only complete matches are sent.
      - Extra fields (match_id, competition) are stripped from H2H/odds dicts.
    """
    try:
        import requests

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Transform payload to match engine's IngestRequest schema
        payload = _transform_payload(data)

        headers = {"Content-Type": "application/json"}
        # The engine authenticates via X-API-Key (not Authorization: Bearer)
        if api_key:
            headers["X-API-Key"] = api_key

        logger.info(f"POSTing {json_path.name} to {webhook_url} ...")
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        logger.info(f"Webhook accepted ({resp.status_code})")
        return True
    except Exception as e:
        logger.error(f"Webhook POST failed: {e}")
        return False


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
    from src.scraper import get_ddmmyy_date

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
