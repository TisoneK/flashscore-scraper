#!/usr/bin/env python3
"""
Shared webhook utilities for forwarding scraped data to the ScoreWise engine.

This module is used by both:
  - run_scraper_railway.py (cron runner)
  - api_server.py (FastAPI control server)

It handles:
  - Converting H2H dates from DD/MM/YYYY to ISO 8601 (YYYY-MM-DD)
  - Transforming raw scraper output into a valid IngestRequest payload
  - POSTing the payload to the engine's /api/ingest endpoint
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def convert_h2h_date(date_str: str) -> str:
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
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(date_str))
    if m:
        day, month, year = m.groups()
        return f"{year}-{month}-{day}"
    return date_str


def transform_payload(data: dict) -> dict:
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
                    "date": convert_h2h_date(h.get("date")),
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


def post_to_webhook(
    json_path: Path,
    webhook_url: str,
    api_key: Optional[str] = None,
    timeout: int = 30,
) -> bool:
    """POST the scraped JSON to a ScoreWise ingestion endpoint.

    The raw file is transformed into a valid IngestRequest before posting:
      - Auth header uses X-API-Key (not Bearer) per engine's FastAPI dependency.
      - Payload envelope is rebuilt as {source, scraped_at, matches}.
      - H2H dates are converted from DD/MM/YYYY to ISO 8601 (YYYY-MM-DD).
      - Only complete matches are sent.
      - Extra fields (match_id, competition) are stripped from H2H/odds dicts.

    Args:
        json_path: Path to the raw scraper output JSON file.
        webhook_url: Full URL of the engine's /api/ingest endpoint.
        api_key: Optional API key for X-API-Key header.
        timeout: HTTP request timeout in seconds.

    Returns:
        True if the webhook accepted the payload, False on any failure.
    """
    try:
        import requests

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Transform payload to match engine's IngestRequest schema
        payload = transform_payload(data)

        # Skip posting if no complete matches after transformation
        if not payload["matches"]:
            logger.warning("No complete matches to send to engine; skipping webhook POST.")
            return True  # Not an error — just nothing to send

        headers = {"Content-Type": "application/json"}
        # The engine authenticates via X-API-Key (not Authorization: Bearer)
        if api_key:
            headers["X-API-Key"] = api_key

        logger.info(f"POSTing {json_path.name} to {webhook_url} "
                     f"({len(payload['matches'])} matches) ...")
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()

        # Try to parse the engine response for better logging
        try:
            engine_response = resp.json()
            succeeded = engine_response.get("succeeded", "?")
            failed = engine_response.get("failed", "?")
            logger.info(f"Webhook accepted ({resp.status_code}) — "
                        f"succeeded: {succeeded}, failed: {failed}")
        except Exception:
            logger.info(f"Webhook accepted ({resp.status_code})")

        return True
    except ImportError:
        logger.error("The 'requests' library is not installed. Cannot POST to webhook.")
        return False
    except Exception as e:
        logger.error(f"Webhook POST failed: {e}")
        return False


def forward_matches_to_engine(
    matches: list,
    webhook_url: str,
    api_key: Optional[str] = None,
    timeout: int = 30,
) -> bool:
    """Forward in-memory match data directly to the engine (no JSON file needed).

    This is used when the scraper API server completes a scrape and wants to
    forward results to the engine without reading from a file. It builds the
    payload from the match objects already in memory.

    Args:
        matches: List of match dicts (raw scraper format with 'status', 'odds', etc.)
        webhook_url: Full URL of the engine's /api/ingest endpoint.
        api_key: Optional API key for X-API-Key header.
        timeout: HTTP request timeout in seconds.

    Returns:
        True if the webhook accepted the payload, False on any failure.
    """
    try:
        import requests
    except ImportError:
        logger.error("The 'requests' library is not installed. Cannot POST to webhook.")
        return False

    # Build the data structure that transform_payload expects
    data = {"matches": matches}
    payload = transform_payload(data)

    # Skip posting if no complete matches after transformation
    if not payload["matches"]:
        logger.warning("No complete matches to send to engine; skipping webhook POST.")
        return True

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        logger.info(f"Forwarding {len(payload['matches'])} complete matches to {webhook_url} ...")
        resp = requests.post(webhook_url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()

        try:
            engine_response = resp.json()
            succeeded = engine_response.get("succeeded", "?")
            failed = engine_response.get("failed", "?")
            logger.info(f"Engine accepted ({resp.status_code}) — "
                        f"succeeded: {succeeded}, failed: {failed}")
        except Exception:
            logger.info(f"Engine accepted ({resp.status_code})")

        return True
    except Exception as e:
        logger.error(f"Forward to engine failed: {e}")
        return False
