"""
chart_generator.py
==================
Gera um sparkline minimalista do histórico de MMR usando matplotlib.
O output é uma string base64 de um PNG transparente, pronta para
ser embutida diretamente no SVG via data URI.
"""

from __future__ import annotations

import base64
import io
import logging

import matplotlib
matplotlib.use("Agg")  # backend sem display, obrigatório em servidores/CI
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes visuais (paleta Rocket League)
# ---------------------------------------------------------------------------

LINE_COLOR   = "#00A8E8"   # azul RL
FILL_COLOR   = "#00A8E8"   # mesmo azul, com alpha reduzido no fill
DOT_COLOR    = "#FFFFFF"   # branco nos pontos de extremidade
CHART_W_IN   = 4.67        # largura em polegadas (467px a 100 DPI)
CHART_H_IN   = 0.55        # altura em polegadas (55px a 100 DPI)
DPI          = 100


# ---------------------------------------------------------------------------
# Sparkline
# ---------------------------------------------------------------------------

def generate_sparkline(mmr_history: list[int]) -> str:
    """
    Gera um sparkline PNG transparente e retorna como string base64.

    Args:
        mmr_history: lista de MMRs em ordem cronológica.

    Returns:
        String base64 do PNG (sem o prefixo 'data:image/png;base64,').
        Retorna uma string vazia se o histórico tiver menos de 2 pontos.
    """
    if len(mmr_history) < 2:
        log.warning("Histórico insuficiente (%d pontos) para gerar sparkline.", len(mmr_history))
        return _placeholder_sparkline()

    fig, ax = plt.subplots(figsize=(CHART_W_IN, CHART_H_IN), dpi=DPI)

    x = list(range(len(mmr_history)))
    y = mmr_history

    # Normaliza para evitar distorção visual com poucos pontos
    y_min = min(y)
    y_max = max(y)
    padding = max((y_max - y_min) * 0.15, 10)  # mínimo 10 pts de padding

    # --- Área preenchida sob a linha (gradiente simulado com alpha) ---
    ax.fill_between(
        x, y,
        alpha=0.15,
        color=FILL_COLOR,
        linewidth=0,
    )

    # --- Segunda camada de fill (gradiente simulado mais denso na base) ---
    ax.fill_between(
        x, [y_min - padding] * len(y), y,
        alpha=0.07,
        color=FILL_COLOR,
        linewidth=0,
    )

    # --- Linha principal ---
    ax.plot(
        x, y,
        color=LINE_COLOR,
        linewidth=2.0,
        solid_capstyle="round",
        solid_joinstyle="round",
        antialiased=True,
    )

    # --- Pontos nas extremidades ---
    for xi, yi in [(x[0], y[0]), (x[-1], y[-1])]:
        ax.plot(xi, yi, "o", color=DOT_COLOR, markersize=4, zorder=5)
        ax.plot(xi, yi, "o", color=LINE_COLOR, markersize=6, zorder=4, alpha=0.5)

    # --- Remove todos os elementos visuais do eixo ---
    ax.set_xlim(x[0] - 0.1, x[-1] + 0.1)
    ax.set_ylim(y_min - padding, y_max + padding)
    ax.axis("off")
    ax.set_facecolor("none")
    fig.patch.set_alpha(0)

    # --- Exporta como PNG transparente em memória ---
    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        transparent=True,
        bbox_inches="tight",
        pad_inches=0,
        dpi=DPI,
    )
    plt.close(fig)
    buf.seek(0)

    b64 = base64.b64encode(buf.read()).decode("utf-8")
    log.info("✅ Sparkline gerado (%d pontos, %d bytes base64).", len(y), len(b64))
    return b64


def _placeholder_sparkline() -> str:
    """Linha reta horizontal para quando há < 2 pontos de dados."""
    fig, ax = plt.subplots(figsize=(CHART_W_IN, CHART_H_IN), dpi=DPI)
    ax.plot([0, 1], [0.5, 0.5], color=LINE_COLOR, linewidth=1.5,
            linestyle="--", alpha=0.4)
    ax.text(0.5, 0.5, "Aguardando dados…",
            transform=ax.transAxes,
            ha="center", va="center",
            color="#445566", fontsize=7)
    ax.axis("off")
    ax.set_facecolor("none")
    fig.patch.set_alpha(0)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True,
                bbox_inches="tight", pad_inches=0, dpi=DPI)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Execução direta (para testes)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Dados de exemplo
    sample = [950, 960, 945, 970, 985, 980, 1000, 995, 1010, 1025, 1015, 1030]
    b64 = generate_sparkline(sample)

    # Salva um PNG de teste para visualização
    import base64 as _b64
    output = "debug_sparkline.png"
    with open(output, "wb") as f:
        f.write(_b64.b64decode(b64))
    print(f"Sparkline salvo em {output}")
