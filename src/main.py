"""
main.py
=======
Main orchestrator for the Rocket League README Stats.

Execution sequence:
  1. Fetch current MMR via scraper (curl_cffi -> Playwright -> ScraperAPI -> cloudscraper -> requests)
  2. Load history, append today's reading, prune old entries, and save
  3. For each mode (1v1, 2v2, 3v3):
     a. Compute historical metrics
     b. Generate sparkline (base64)
     c. Inject into SVG template and save in assets/
  4. Log final summary
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure src/ is in the path when run directly
sys.path.insert(0, str(Path(__file__).parent))

import scraper
import history_manager
import chart_generator
import svg_builder

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODES = ("1v1", "2v2", "3v3")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("Rocket League README Stats - starting update")
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Data collection
    # ------------------------------------------------------------------
    log.info("\nStep 1/4 - Fetching data from TRN...")
    scraped = scraper.fetch_stats()

    if not scraped["success"]:
        log.error("Failed to collect data. Exiting without updating files.")
        sys.exit(1)

    log.info("   Player  : %s", scraped["player_name"])
    log.info("   Source  : Layer %s", scraped["source_layer"])
    for mode in MODES:
        info = scraped["modes"].get(mode)
        if info:
            log.info("   %s      : %d MMR - %s", mode, info["mmr"], info["rank"])
        else:
            log.warning("   %s      : no data", mode)

    # ------------------------------------------------------------------
    # 2. History
    # ------------------------------------------------------------------
    log.info("\nStep 2/4 - Updating history (30 days)...")
    history = history_manager.load_history()
    history = history_manager.append_today(history, scraped)
    history = history_manager.prune_old_entries(history)
    history_manager.save_history(history)

    # ------------------------------------------------------------------
    # 3. SVG Generation
    # ------------------------------------------------------------------
    log.info("\nStep 3/4 - Generating SVGs...")

    generated: list[str] = []

    for mode in MODES:
        mode_info = scraped["modes"].get(mode)
        if not mode_info:
            log.warning("  Mode %s without data - SVG not generated.", mode)
            continue

        log.info("  Processing mode %s...", mode)

        # Historical metrics
        metrics = history_manager.compute_metrics(history, mode)

        # Sparkline
        chart_b64 = chart_generator.generate_sparkline(metrics["mmr_history"])

        # Final SVG
        svg_content = svg_builder.build_svg(
            mode=mode,
            player_name=scraped["player_name"],
            mmr=mode_info["mmr"],
            rank=mode_info["rank"],
            rank_tier=mode_info["rank_tier"],
            sprite=mode_info.get("sprite", "unranked.png"),
            metrics=metrics,
            chart_b64=chart_b64,
        )
        svg_builder.save_svg(svg_content, mode)
        generated.append(mode)

    # ------------------------------------------------------------------
    # 4. Summary
    # ------------------------------------------------------------------
    log.info("\nStep 4/4 - Done!")
    log.info("   Generated SVGs: %s", ", ".join(generated) if generated else "none")
    log.info("   History       : %d entries (1v1) | %d entries (2v2) | %d entries (3v3)",
             len(history["modes"]["1v1"]),
             len(history["modes"]["2v2"]),
             len(history["modes"]["3v3"]))
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
