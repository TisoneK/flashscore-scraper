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
            "country": match.get("country", ""),
            "league": match.get("league", ""),
            "date": match.get("date", ""),
            "time": match.get("time", ""),
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
                home_team = h.get("home_team")
                away_team = h.get("away_team")
                home_score = h.get("home_score")
                away_score = h.get("away_score")
                # Skip H2H entries with missing data — they're useless to the engine
                # and would fail validation. This is NOT forging — we're just
                # filtering out incomplete entries, not making up values.
                if not home_team or not away_team or home_score is None or away_score is None:
                    continue
                cleaned = {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": int(home_score),
                    "away_score": int(away_score),
                    "date": convert_h2h_date(h.get("date")) or "",
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


def forward_results_to_website(
    results: list,
    website_url: str,
    webhook_secret: str,
    date_str: Optional[str] = None,
    source: str = "flashscore-scraper",
    timeout: int = 30,
) -> bool:
    """Push final scores to the website's /api/webhook/result endpoint.

    Called by FlashscoreScraper.scrape_results() after it collects final
    scores for a date. The website updates its Prediction table with
    home_score, away_score, result_status = FINAL, result_source = "scraper".

    The payload is HMAC-SHA256 signed with webhook_secret so the website
    can verify authenticity without needing a session cookie.

    Args:
        results: List of result dicts. Each must have:
            - match_id (str)
            - home_score (int)
            - away_score (int)
            - status (str, e.g. "finished" — only "finished" entries are processed)
        website_url: Base URL of the website (e.g. https://scorewise-ke.vercel.app).
        webhook_secret: Shared HMAC secret. MUST match WEBHOOK_SECRET on the website.
        date_str: Optional date string (DD.MM.YYYY) for logging/context.
        source: Source identifier (default "flashscore-scraper").
        timeout: HTTP request timeout in seconds.

    Returns:
        True if the webhook accepted the payload, False on any failure.
    """
    if not results:
        logger.info("No results to push to website — skipping webhook POST.")
        return True

    if not website_url:
        logger.warning("forward_results_to_website: website_url is empty — skipping.")
        return False

    if not webhook_secret:
        logger.warning("forward_results_to_website: webhook_secret is empty — cannot sign payload. Skipping.")
        return False

    try:
        import hashlib
        import hmac
        import json
        from datetime import datetime, timezone
        import requests

        envelope = {
            "event": "results_push",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "date": date_str,
                "source": source,
                "results": results,
            },
        }
        body = json.dumps(envelope, default=str).encode("utf-8")
        signature = hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        url = f"{website_url.rstrip('/')}/api/webhook/result"
        headers = {
            "Content-Type": "application/json",
            "X-ScoreWise-Event": "results_push",
            "X-ScoreWise-Signature": signature,
        }

        logger.info(
            f"Pushing {len(results)} result(s) to {url} "
            f"(date={date_str or 'n/a'}) ..."
        )
        resp = requests.post(url, data=body, headers=headers, timeout=timeout)

        if resp.ok:
            try:
                resp_data = resp.json()
                stored = resp_data.get("stored", "?")
                skipped = resp_data.get("skipped", "?")
                errors = resp_data.get("errors", "?")
                logger.info(
                    f"Website accepted results ({resp.status_code}) — "
                    f"stored: {stored}, skipped: {skipped}, errors: {errors}"
                )
            except Exception:
                logger.info(f"Website accepted results ({resp.status_code})")
            return True
        else:
            logger.warning(
                f"Website rejected results (HTTP {resp.status_code}): "
                f"{resp.text[:200]}"
            )
            return False
    except ImportError:
        logger.error("The 'requests' library is not installed. Cannot POST results to website.")
        return False
    except Exception as e:
        logger.error(f"Forward results to website failed: {e}")
        return False


def forward_scrape_report_to_website(
    scrape_id: str,
    day: str,
    result: dict,
    website_url: str,
    webhook_secret: str,
    timeout: int = 20,
) -> bool:
    """Push a per-match scrape report to the website's /api/webhook/scrape-report.

    Admins/operators need eyes on EVERYTHING a scrape did — including the
    matches that did NOT qualify for prediction and why (missing odds fields,
    insufficient H2H, ...). Only complete matches travel to the engine, so
    without this report the incomplete ones are invisible outside scraper
    logs. The website stores the report in its activity log and surfaces it
    on the admin dashboard.

    The payload is HMAC-SHA256 signed with webhook_secret (same scheme as
    forward_results_to_website).
    """
    matches = result.get("matches") or []
    report_matches = []
    for m in matches:
        report_matches.append({
            "match_id": getattr(m, "match_id", ""),
            "home_team": getattr(m, "home_team", ""),
            "away_team": getattr(m, "away_team", ""),
            "country": getattr(m, "country", ""),
            "league": getattr(m, "league", ""),
            "date": getattr(m, "date", ""),
            "time": getattr(m, "time", ""),
            "status": getattr(m, "status", "unknown"),
            "skip_reason": getattr(m, "skip_reason", None),
        })

    if not website_url:
        logger.warning("forward_scrape_report_to_website: website_url is empty — skipping.")
        return False
    if not webhook_secret:
        logger.warning("forward_scrape_report_to_website: webhook_secret is empty — cannot sign payload. Skipping.")
        return False

    try:
        import hashlib
        import hmac
        import json
        from datetime import datetime, timezone
        import requests

        envelope = {
            "event": "scrape_report",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "scrape_id": scrape_id,
                "day": day,
                "total_collected": result.get("total_collected", len(report_matches)),
                "complete_matches": result.get("complete_matches", 0),
                "incomplete_matches": result.get("incomplete_matches", 0),
                "matches": report_matches,
            },
        }
        body = json.dumps(envelope, default=str).encode("utf-8")
        signature = hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        url = f"{website_url.rstrip('/')}/api/webhook/scrape-report"
        headers = {
            "Content-Type": "application/json",
            "X-ScoreWise-Event": "scrape_report",
            "X-ScoreWise-Signature": signature,
        }

        logger.info(
            f"Pushing scrape report to {url} "
            f"({len(report_matches)} matches, {result.get('incomplete_matches', 0)} incomplete) ..."
        )
        resp = requests.post(url, data=body, headers=headers, timeout=timeout)
        resp.raise_for_status()
        logger.info(f"Website accepted scrape report ({resp.status_code}).")
        return True
    except ImportError:
        logger.error("The 'requests' library is not installed. Cannot POST scrape report to website.")
        return False
    except Exception as e:
        logger.error(f"Forward scrape report to website failed: {e}")
        return False
