"""
history_manager.py
==================
Manages the data/history.json file, which accumulates daily MMR
readings for the 3 modes. Maintains a 30-day sliding window.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Default path for the history file (relative to the repository root)
HISTORY_FILE = Path(__file__).parent.parent / "data" / "history.json"

# Retention window in days
RETENTION_DAYS = 30


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_history(path: Path = HISTORY_FILE) -> dict:
    """Loads history.json. Returns an empty structure if it doesn't exist."""
    if not path.exists():
        log.warning("history.json not found. Creating empty structure.")
        return _empty_history()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history: dict, path: Path = HISTORY_FILE) -> None:
    """Saves the formatted history.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    log.info("history.json saved in %s", path)


def _empty_history() -> dict:
    return {
        "player": "guxvr",
        "modes": {
            "1v1": [],
            "2v2": [],
            "3v3": [],
        },
    }


# ---------------------------------------------------------------------------
# History Mutation
# ---------------------------------------------------------------------------

def append_today(history: dict, scraped_data: dict) -> dict:
    """
    Appends (or updates) today's entry in the history for each mode.
    If an entry for today already exists, it is replaced.
    """
    today = date.today().isoformat()
    modes_data: dict = scraped_data.get("modes", {})

    for mode_key in ("1v1", "2v2", "3v3"):
        mode_info = modes_data.get(mode_key)
        if not mode_info:
            log.debug("  Mode %s has no data today, skipping.", mode_key)
            continue

        entry = {
            "date": today,
            "mmr": mode_info["mmr"],
            "rank": mode_info["rank"],
            "rank_tier": mode_info["rank_tier"],
        }

        entries: list = history["modes"].setdefault(mode_key, [])

        # Remove today's duplicate entry (if any)
        history["modes"][mode_key] = [e for e in entries if e["date"] != today]
        history["modes"][mode_key].append(entry)

        log.info("  %s - MMR %d (%s) added for %s",
                 mode_key, entry["mmr"], entry["rank"], today)

    return history


def prune_old_entries(history: dict, days: int = RETENTION_DAYS) -> dict:
    """Removes entries older than `days` days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    for mode_key in history.get("modes", {}):
        before = len(history["modes"][mode_key])
        history["modes"][mode_key] = [
            e for e in history["modes"][mode_key]
            if e["date"] >= cutoff
        ]
        removed = before - len(history["modes"][mode_key])
        if removed:
            log.debug("  %s: %d old entry/entries removed.", mode_key, removed)

    return history


# ---------------------------------------------------------------------------
# Derived Metrics
# ---------------------------------------------------------------------------

def compute_metrics(history: dict, mode: str) -> dict:
    """
    Computes metrics from the history for a specific mode.

    Returns:
      mmr_history   : list of MMRs in chronological order
      peak_mmr      : highest MMR in the last 30 days
      trend_value   : difference between the most recent and the oldest reading
      trend_arrow   : "↑" or "↓"
      trend_color   : "#4CAF50" (green) or "#F44336" (red) or "#8899AA" (neutral)
      session_count : number of days with data
    """
    entries: list[dict] = sorted(
        history.get("modes", {}).get(mode, []),
        key=lambda e: e["date"],
    )

    mmr_history = [e["mmr"] for e in entries]
    session_count = len(mmr_history)

    if session_count == 0:
        return _empty_metrics()

    peak_mmr = max(mmr_history)
    latest = mmr_history[-1]
    earliest = mmr_history[0]
    diff = latest - earliest

    if diff > 0:
        arrow, color = "↑", "#4CAF50"
    elif diff < 0:
        arrow, color = "↓", "#F44336"
    else:
        arrow, color = "→", "#8899AA"

    trend_str = f"+{diff}" if diff > 0 else str(diff)

    return {
        "mmr_history": mmr_history,
        "peak_mmr": peak_mmr,
        "trend_value": trend_str,
        "trend_arrow": arrow,
        "trend_color": color,
        "session_count": session_count,
    }


def _empty_metrics() -> dict:
    return {
        "mmr_history": [],
        "peak_mmr": 0,
        "trend_value": "—",
        "trend_arrow": "→",
        "trend_color": "#8899AA",
        "session_count": 0,
    }


# ---------------------------------------------------------------------------
# Direct Execution (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    h = load_history()
    print(json.dumps(h, indent=2, ensure_ascii=False))

    for mode in ("1v1", "2v2", "3v3"):
        metrics = compute_metrics(h, mode)
        print(f"\n--- {mode} ---")
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
