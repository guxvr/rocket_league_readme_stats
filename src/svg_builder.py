"""
svg_builder.py
==============
Reads the SVG template, replaces all placeholders with actual data,
and saves the final file to assets/.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
import base64
import re

log = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "card_template.svg"
ASSETS_DIR    = Path(__file__).parent.parent / "assets"
SPRITES_DIR   = Path(__file__).parent.parent / "sprites"

# ---------------------------------------------------------------------------
# Color palette per rank tier
# ---------------------------------------------------------------------------

RANK_COLORS: dict[str, str] = {
    "supersonic_legend": "#FF6B35",
    "grand_champion":    "#F44336",
    "champion":          "#9C27B0",
    "diamond":           "#2196F3",
    "platinum":          "#00BCD4",
    "gold":              "#FFD700",
    "silver":            "#A8A8A8",
    "bronze":            "#CD7F32",
    "unranked":          "#556677",
}

# Display labels for each mode
MODE_LABELS: dict[str, str] = {
    "1v1": "1V1 · RANKED DUEL",
    "2v2": "2V2 · RANKED DOUBLES",
    "3v3": "3V3 · RANKED STANDARD",
}


# ---------------------------------------------------------------------------
# Main Builder
# ---------------------------------------------------------------------------

def build_svg(
    mode: str,
    player_name: str,
    mmr: int,
    rank: str,
    rank_tier: str,
    sprite: str,
    metrics: dict,
    chart_b64: str,
    template_path: Path = TEMPLATE_PATH,
) -> str:
    """
    Reads the SVG template and replaces all placeholders.

    Args:
        mode:          Mode key ("1v1", "2v2", "3v3").
        player_name:   Player's display name.
        mmr:           Current MMR.
        rank:          Full rank name (e.g. "Diamond II").
        rank_tier:     Normalized tier (e.g. "diamond").
        sprite:        Sprite filename (e.g. "diamond2.png").
        metrics:       Dict returned by history_manager.compute_metrics().
        chart_b64:     Base64 string of the sparkline PNG.
        template_path: Path to the SVG template.

    Returns:
        String containing the full SVG, ready to be saved.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"SVG Template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")

    rank_color = RANK_COLORS.get(rank_tier, RANK_COLORS["unranked"])
    today_str  = date.today().strftime("%b %d, %Y")

    def _img_to_b64(path: Path) -> str:
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
        log.warning("  Image not found: %s", path)
        return ""

    logo_b64 = _img_to_b64(SPRITES_DIR / "rocketleague.png")
    rank_icon_b64 = _img_to_b64(SPRITES_DIR / sprite)

    replacements = {
        "{{PLAYER_NAME}}":    player_name,
        "{{MODE_LABEL}}":     MODE_LABELS.get(mode, mode.upper()),
        "{{MMR_VALUE}}":      str(mmr),
        "{{RANK_NAME}}":      rank,
        "{{RANK_COLOR}}":     rank_color,
        "{{PEAK_MMR}}":       str(metrics.get("peak_mmr", mmr)),
        "{{TREND_ARROW}}":    metrics.get("trend_arrow", "→"),
        "{{TREND_VALUE}}":    metrics.get("trend_value", "—"),
        "{{TREND_COLOR}}":    metrics.get("trend_color", "#8899AA"),
        "{{SESSION_COUNT}}":  str(metrics.get("session_count", 1)),
        "{{CHART_B64}}":      chart_b64,
        "{{LOGO_B64}}":       logo_b64,
        "{{RANK_ICON_B64}}":  rank_icon_b64,
        "{{LAST_UPDATE}}":    today_str,
    }

    svg = template
    for placeholder, value in replacements.items():
        svg = svg.replace(placeholder, value)

    # Checks if any unreplaced placeholders remain
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", svg)
    if remaining:
        log.warning("  Unreplaced placeholders found: %s", remaining)

    return svg


def save_svg(svg_content: str, mode: str, output_dir: Path = ASSETS_DIR) -> Path:
    """
    Saves the final SVG to the assets/ directory.

    Returns:
        Path of the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"rl-stats-{mode}.svg"
    output_path.write_text(svg_content, encoding="utf-8")
    log.info("SVG saved: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Direct Execution (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Dummy data to test the template
    sample_metrics = {
        "mmr_history": [950, 960, 945, 970, 985, 1000, 1025, 1015, 1030],
        "peak_mmr": 1030,
        "trend_value": "+80",
        "trend_arrow": "▲",
        "trend_color": "#4CAF50",
        "session_count": 9,
    }

    svg = build_svg(
        mode="3v3",
        player_name="guxvr",
        mmr=1030,
        rank="Diamond III",
        rank_tier="diamond",
        sprite="diamond3.png",
        metrics=sample_metrics,
        chart_b64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    )

    path = save_svg(svg, "3v3")
    print(f"Test SVG saved at: {path}")
