"""
main.py
=======
Orquestrador principal do Rocket League README Stats.

Sequência de execução:
  1. Coleta MMR atual via scraper (curl_cffi → Playwright)
  2. Carrega histórico, adiciona leitura de hoje, prune, salva
  3. Para cada modo (1v1, 2v2, 3v3):
     a. Computa métricas do histórico
     b. Gera sparkline (base64)
     c. Injeta no template SVG e salva em assets/
  4. Loga resumo final
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Garante que src/ está no path quando rodado diretamente
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
# Constantes
# ---------------------------------------------------------------------------

MODES = ("1v1", "2v2", "3v3")


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("🚀 Rocket League README Stats — iniciando atualização")
    log.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Coleta de dados
    # ------------------------------------------------------------------
    log.info("\n📡 Etapa 1/4 — Coletando dados do TRN...")
    scraped = scraper.fetch_stats()

    if not scraped["success"]:
        log.error("❌ Falha na coleta de dados. Encerrando sem atualizar arquivos.")
        sys.exit(1)

    log.info("   Player  : %s", scraped["player_name"])
    log.info("   Fonte   : Camada %s", scraped["source_layer"])
    for mode in MODES:
        info = scraped["modes"].get(mode)
        if info:
            log.info("   %s      : %d MMR — %s", mode, info["mmr"], info["rank"])
        else:
            log.warning("   %s      : sem dados", mode)

    # ------------------------------------------------------------------
    # 2. Histórico
    # ------------------------------------------------------------------
    log.info("\n📂 Etapa 2/4 — Atualizando histórico (30 dias)...")
    history = history_manager.load_history()
    history = history_manager.append_today(history, scraped)
    history = history_manager.prune_old_entries(history)
    history_manager.save_history(history)

    # ------------------------------------------------------------------
    # 3. Geração dos SVGs
    # ------------------------------------------------------------------
    log.info("\n🎨 Etapa 3/4 — Gerando SVGs...")

    generated: list[str] = []

    for mode in MODES:
        mode_info = scraped["modes"].get(mode)
        if not mode_info:
            log.warning("  ⏭ Modo %s sem dados — SVG não gerado.", mode)
            continue

        log.info("  Processando modo %s...", mode)

        # Métricas do histórico
        metrics = history_manager.compute_metrics(history, mode)

        # Sparkline
        chart_b64 = chart_generator.generate_sparkline(metrics["mmr_history"])

        # SVG final
        svg_content = svg_builder.build_svg(
            mode=mode,
            player_name=scraped["player_name"],
            mmr=mode_info["mmr"],
            rank=mode_info["rank"],
            rank_tier=mode_info["rank_tier"],
            metrics=metrics,
            chart_b64=chart_b64,
        )
        svg_builder.save_svg(svg_content, mode)
        generated.append(mode)

    # ------------------------------------------------------------------
    # 4. Resumo
    # ------------------------------------------------------------------
    log.info("\n✅ Etapa 4/4 — Concluído!")
    log.info("   SVGs gerados: %s", ", ".join(generated) if generated else "nenhum")
    log.info("   Histórico   : %d entradas (1v1) | %d entradas (2v2) | %d entradas (3v3)",
             len(history["modes"]["1v1"]),
             len(history["modes"]["2v2"]),
             len(history["modes"]["3v3"]))
    log.info("=" * 60)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
