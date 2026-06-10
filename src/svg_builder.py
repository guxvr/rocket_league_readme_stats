"""
svg_builder.py
==============
Lê o template SVG, substitui todos os placeholders com os dados reais
e salva o arquivo final em assets/.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "card_template.svg"
ASSETS_DIR    = Path(__file__).parent.parent / "assets"

# ---------------------------------------------------------------------------
# Paleta de cores por rank tier
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

# Rótulos de exibição para cada modo
MODE_LABELS: dict[str, str] = {
    "1v1": "1V1 · RANKED DUEL",
    "2v2": "2V2 · RANKED DOUBLES",
    "3v3": "3V3 · RANKED STANDARD",
}


# ---------------------------------------------------------------------------
# Builder principal
# ---------------------------------------------------------------------------

def build_svg(
    mode: str,
    player_name: str,
    mmr: int,
    rank: str,
    rank_tier: str,
    metrics: dict,
    chart_b64: str,
    template_path: Path = TEMPLATE_PATH,
) -> str:
    """
    Lê o template SVG e substitui todos os placeholders.

    Args:
        mode:        Chave do modo ("1v1", "2v2", "3v3").
        player_name: Nome de exibição do jogador.
        mmr:         MMR atual.
        rank:        Nome completo do rank (ex: "Diamond II").
        rank_tier:   Tier normalizado (ex: "diamond").
        metrics:     Dict retornado por history_manager.compute_metrics().
        chart_b64:   String base64 do sparkline PNG.
        template_path: Caminho para o template SVG.

    Returns:
        String com o SVG completo e pronto para salvar.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Template SVG não encontrado: {template_path}")

    template = template_path.read_text(encoding="utf-8")

    rank_color = RANK_COLORS.get(rank_tier, RANK_COLORS["unranked"])
    today_str  = date.today().strftime("%b %d, %Y")

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
        "{{LAST_UPDATE}}":    today_str,
    }

    svg = template
    for placeholder, value in replacements.items():
        svg = svg.replace(placeholder, value)

    # Verifica se sobrou algum placeholder não substituído
    import re
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", svg)
    if remaining:
        log.warning("  ⚠ Placeholders não substituídos: %s", remaining)

    return svg


def save_svg(svg_content: str, mode: str, output_dir: Path = ASSETS_DIR) -> Path:
    """
    Salva o SVG final no diretório assets/.

    Returns:
        Caminho do arquivo salvo.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"rl-stats-{mode}.svg"
    output_path.write_text(svg_content, encoding="utf-8")
    log.info("✅ SVG salvo: %s", output_path)
    return output_path


# ---------------------------------------------------------------------------
# Execução direta (para testes)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Dados fictícios para testar o template
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
        metrics=sample_metrics,
        chart_b64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    )

    path = save_svg(svg, "3v3")
    print(f"SVG de teste salvo em: {path}")
