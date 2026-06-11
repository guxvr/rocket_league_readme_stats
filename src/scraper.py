"""
scraper.py
==========
Responsible for fetching data from the Rocket League Tracker Network (TRN).
Uses 5 progressive scraping layers to bypass blocks (Cloudflare WAF).
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date
import re

log = logging.getLogger(__name__)

DISPLAY_NAME = os.environ.get("EPIC_DISPLAY_NAME", "guxvr")
PROFILE_URL = f"https://api.tracker.gg/api/v2/rocket-league/standard/profile/epic/{DISPLAY_NAME}"

# Internal mapping from TRN to the modes we care about
PLAYLIST_IDS = {
    10: "1v1",
    11: "2v2",
    13: "3v3",
}

BROWSER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://rocketleague.tracker.network",
    "Referer": "https://rocketleague.tracker.network/",
}


# ---------------------------------------------------------------------------
# Data Structures & Helpers
# ---------------------------------------------------------------------------

def _empty_result() -> dict:
    """Returns the default structure in case of failure."""
    return {
        "player_name": DISPLAY_NAME,
        "scraped_at": date.today().isoformat(),
        "source_layer": None,
        "success": False,
        "modes": {"1v1": None, "2v2": None, "3v3": None},
    }


def _mode_entry(mmr: int, rank: str) -> dict:
    return {
        "mmr": mmr,
        "rank": rank,
        "rank_tier": _rank_to_tier(rank),
        "sprite": _rank_to_sprite(rank),
    }


def _rank_to_tier(rank_name: str) -> str:
    rank_lower = rank_name.lower()
    tiers = [
        ("supersonic legend", "supersonic_legend"),
        ("grand champion",    "grand_champion"),
        ("champion",          "champion"),
        ("diamond",           "diamond"),
        ("platinum",          "platinum"),
        ("gold",              "gold"),
        ("silver",            "silver"),
        ("bronze",            "bronze"),
    ]
    for keyword, tier in tiers:
        if keyword in rank_lower:
            return tier
    return "unranked"

def _rank_to_sprite(rank_name: str) -> str:
    """
    Maps 'Diamond II' to 'diamond2.png', 'Supersonic Legend' to 'supersonic_legend.png'.
    """
    tier = _rank_to_tier(rank_name)
    if tier in ("supersonic_legend", "unranked"):
        return f"{tier}.png"
        
    div_match = re.search(r'\b(III|II|I)\b', rank_name)
    div_str = "1"
    if div_match:
        roman = div_match.group(1)
        if roman == "III": div_str = "3"
        elif roman == "II": div_str = "2"
        elif roman == "I": div_str = "1"
        
    if tier == "grand_champion":
        return f"grandchampion{div_str}.png"
    return f"{tier}{div_str}.png"


# ---------------------------------------------------------------------------
# API JSON Response Parser
# ---------------------------------------------------------------------------

def _parse_api_response(data: dict) -> dict:
    """Extracts MMR and rank for each mode from the TRN API JSON."""
    segments = data.get("data", {}).get("segments", [])
    results: dict[str, dict] = {}

    for seg in segments:
        playlist_id = seg.get("attributes", {}).get("playlistId")
        mode = PLAYLIST_IDS.get(playlist_id)
        if not mode:
            continue

        stats = seg.get("stats", {})
        rating = stats.get("rating")
        tier = stats.get("tier")

        if not rating or not tier:
            log.debug("  Mode %s missing rating/tier - skipping.", mode)
            continue

        mmr = rating.get("value")
        rank_name = tier.get("metadata", {}).get("name", "Unranked")

        if mmr is None:
            continue

        results[mode] = _mode_entry(int(mmr), rank_name)
        log.info("  %s - MMR: %d  Rank: %s", mode, int(mmr), rank_name)

    return results


# ---------------------------------------------------------------------------
# Layer 1 - curl_cffi (Direct API JSON)
# ---------------------------------------------------------------------------

def _scrape_layer1() -> dict:
    try:
        from curl_cffi import requests as cffi_requests
        log.info("Layer 1 - curl_cffi (Direct API) starting...")
        resp = cffi_requests.get(
            PROFILE_URL,
            impersonate="safari15_5",
            headers=BROWSER_HEADERS,
            timeout=20,
        )

        if resp.status_code == 429:
            log.warning("  Rate limited (429). Waiting 5s and escalating.")
            time.sleep(5)
            return {}

        if resp.status_code == 403:
            log.warning("  Blocked (403). Escalating to Layer 2.")
            return {}

        if resp.status_code != 200:
            log.warning("  Unexpected status: %d. Escalating.", resp.status_code)
            return {}

        data = resp.json()
        modes = _parse_api_response(data)
        if not modes:
            log.warning("  API returned 200 but no rank data. Escalating.")
            return {}

        return modes

    except ImportError:
        log.warning("  curl_cffi not installed. Escalating to Layer 2.")
        return {}
    except Exception as exc:
        log.warning("  Error in Layer 1: %s. Escalating.", exc)
        return {}


# ---------------------------------------------------------------------------
# Layer 2 - Playwright with API interception
# ---------------------------------------------------------------------------

def _scrape_layer2() -> dict:
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import stealth_sync

        log.info("Layer 2 - Playwright (API intercept) starting...")
        captured_data: dict = {}

        def intercept_response(response):
            if "api.tracker.gg" in response.url and "profile/epic" in response.url:
                if response.status == 200:
                    try:
                        captured_data["body"] = response.json()
                        log.info("  API intercepted: %s", response.url)
                    except Exception:
                        pass

        with sync_playwright() as p:
            is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
            browser = p.chromium.launch(
                headless=not is_github_actions,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = context.new_page()
            stealth_sync(page)
            page.on("response", intercept_response)

            page_url = f"https://rocketleague.tracker.network/rocket-league/profile/epic/{DISPLAY_NAME}/overview"
            log.info("  Navigating to %s", page_url)

            try:
                page.goto(page_url, wait_until="networkidle", timeout=35_000)
            except Exception:
                log.debug("  networkidle timeout - checking captured data...")

            browser.close()

        if "body" in captured_data:
            modes = _parse_api_response(captured_data["body"])
            if modes:
                return modes

        log.warning("  No data captured via Playwright.")
        return {}

    except ImportError as e:
        log.warning("  Playwright or dependency not installed: %s", e)
        return {}
    except Exception as exc:
        log.error("  Error in Layer 2: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Layer 3 - ScraperAPI
# ---------------------------------------------------------------------------

def _scrape_layer3() -> dict:
    try:
        import requests
        api_key = os.environ.get("SCRAPER_API_KEY")
        if not api_key:
            log.info("Layer 3 - ScraperAPI skipped (SCRAPER_API_KEY not configured).")
            return {}

        log.info("Layer 3 - ScraperAPI starting...")
        payload = {
            'api_key': api_key,
            'url': PROFILE_URL,
            'render': 'false',
        }
        resp = requests.get('http://api.scraperapi.com', params=payload, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            modes = _parse_api_response(data)
            if modes:
                return modes
        log.warning("  ScraperAPI failed (Status: %d). Escalating.", resp.status_code)
        return {}
    except ImportError:
        log.warning("  requests not installed. Escalating.")
        return {}
    except Exception as exc:
        log.warning("  Error in Layer 3: %s", exc)
        return {}

# ---------------------------------------------------------------------------
# Layer 4 - cloudscraper
# ---------------------------------------------------------------------------

def _scrape_layer4() -> dict:
    try:
        import cloudscraper
        log.info("Layer 4 - cloudscraper starting...")
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(PROFILE_URL, headers=BROWSER_HEADERS, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            modes = _parse_api_response(data)
            if modes:
                return modes
        log.warning("  cloudscraper failed (Status: %d). Escalating.", resp.status_code)
        return {}
    except ImportError:
        log.warning("  cloudscraper not installed. Escalating.")
        return {}
    except Exception as exc:
        log.warning("  Error in Layer 4: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Layer 5 - requests fallback
# ---------------------------------------------------------------------------

def _scrape_layer5() -> dict:
    try:
        import requests
        log.info("Layer 5 - requests fallback starting...")
        resp = requests.get(PROFILE_URL, headers=BROWSER_HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            modes = _parse_api_response(data)
            if modes:
                return modes
        log.warning("  requests failed (Status: %d).", resp.status_code)
        return {}
    except ImportError:
        log.warning("  requests not installed.")
        return {}
    except Exception as exc:
        log.warning("  Error in Layer 5: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Public Entrypoint
# ---------------------------------------------------------------------------

def fetch_stats() -> dict:
    """
    Collects stats using progressive layers.
    Returns the structured result or an empty result on total failure.
    """
    result = _empty_result()

    layers = [
        (1, _scrape_layer1, "curl_cffi + Direct API"),
        (2, _scrape_layer2, "Playwright"),
        (3, _scrape_layer3, "ScraperAPI"),
        (4, _scrape_layer4, "cloudscraper"),
        (5, _scrape_layer5, "requests fallback")
    ]

    for layer_idx, func, name in layers:
        modes = func()
        if modes:
            result["modes"].update(modes)
            result["source_layer"] = layer_idx
            result["success"] = True
            log.info("Data collected via Layer %d (%s).", layer_idx, name)
            return result

    log.error("All layers failed. No data collected.")
    return result


# ---------------------------------------------------------------------------
# Direct Execution (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data = fetch_stats()
    print(json.dumps(data, indent=2, ensure_ascii=False))
