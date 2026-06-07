#!/usr/bin/env python3
"""
Non-interactive scraper runner for CI/CD (GitHub Actions).

Usage:
    python run_scraper_ci.py [--day Today|Tomorrow] [--webhook-url URL] [--api-key KEY]

- Runs the scraper headlessly, outputs JSON to output/json/
- Optionally POSTs results to a ScoreWise ingestion endpoint
- Exits with code 0 on success, 1 on failure
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.scraper import FlashscoreScraper
from src.storage.json_storage import JSONStorage
from src.utils.config_loader import CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ci_runner")


def post_to_webhook(json_path: Path, webhook_url: str, api_key: str = None):
    """POST the scraped JSON to a ScoreWise ingestion endpoint."""
    try:
        import requests

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.info(f"POSTing {json_path.name} to {webhook_url} ...")
        resp = requests.post(webhook_url, json=data, headers=headers, timeout=30)
        resp.raise_for_status()
        logger.info(f"Webhook accepted ({resp.status_code})")
        return True
    except Exception as e:
        logger.error(f"Webhook POST failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="CI scraper runner")
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

    # ── Auto-install ChromeDriver on CI ─────────────────────────
    # Try chromedriver_autoinstaller first (puts chromedriver on system PATH)
    try:
        import chromedriver_autoinstaller
        chromedriver_path = chromedriver_autoinstaller.install()
        logger.info(f"ChromeDriver auto-installed at: {chromedriver_path}")
    except ImportError:
        logger.debug("chromedriver-autoinstaller not available")
    
    # Also try webdriver-manager as a fallback (auto-downloads matching version)
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        chromedriver_path = ChromeDriverManager().install()
        logger.info(f"ChromeDriver available via webdriver-manager at: {chromedriver_path}")
    except ImportError:
        logger.debug("webdriver-manager not available")
    except Exception as e:
        logger.debug(f"webdriver-manager install skipped: {e}")

    # ── Run the scraper ──────────────────────────────────────────
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
    if args.webhook_url:
        ok = post_to_webhook(json_path, args.webhook_url, args.api_key)
        if not ok:
            logger.warning("Webhook delivery failed; JSON is still saved locally.")

    # ── Summary for GitHub Actions ───────────────────────────────
    summary = (
        f"## Scraper Results\n"
        f"- **Day**: {args.day}\n"
        f"- **Total matches**: {total}\n"
        f"- **Complete**: {complete}\n"
        f"- **Incomplete**: {incomplete}\n"
        f"- **Output**: `{json_path}`\n"
    )
    # Write to GITHUB_STEP_SUMMARY if available
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    else:
        print(summary)

    sys.exit(0)


if __name__ == "__main__":
    main()
