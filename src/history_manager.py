"""
history_manager.py
==================
Gerencia o arquivo data/history.json, que acumula leituras diárias
de MMR para os 3 modos. Mantém uma janela deslizante de 30 dias.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Caminho padrão para o histórico (relativo à raiz do repositório)
HISTORY_FILE = Path(__file__).parent.parent / "data" / "history.json"

# Janela de retenção em dias
RETENTION_DAYS = 30


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_history(path: Path = HISTORY_FILE) -> dict:
    """Carrega o history.json. Se não existir, retorna estrutura vazia."""
    if not path.exists():
        log.warning("history.json não encontrado. Criando estrutura vazia.")
        return _empty_history()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history: dict, path: Path = HISTORY_FILE) -> None:
    """Salva o history.json formatado."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    log.info("💾 history.json salvo em %s", path)


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
# Mutação do histórico
# ---------------------------------------------------------------------------

def append_today(history: dict, scraped_data: dict) -> dict:
    """
    Adiciona (ou atualiza) a entrada de hoje no histórico para cada modo.
    Se já existe uma entrada com a data de hoje, ela é substituída.
    """
    today = date.today().isoformat()
    modes_data: dict = scraped_data.get("modes", {})

    for mode_key in ("1v1", "2v2", "3v3"):
        mode_info = modes_data.get(mode_key)
        if not mode_info:
            log.debug("  – Modo %s sem dados hoje, pulando.", mode_key)
            continue

        entry = {
            "date": today,
            "mmr": mode_info["mmr"],
            "rank": mode_info["rank"],
            "rank_tier": mode_info["rank_tier"],
        }

        entries: list = history["modes"].setdefault(mode_key, [])

        # Remove entrada duplicada de hoje (se houver)
        history["modes"][mode_key] = [e for e in entries if e["date"] != today]
        history["modes"][mode_key].append(entry)

        log.info("  ✓ %s — MMR %d (%s) adicionado para %s",
                 mode_key, entry["mmr"], entry["rank"], today)

    return history


def prune_old_entries(history: dict, days: int = RETENTION_DAYS) -> dict:
    """Remove entradas mais antigas que `days` dias."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    for mode_key in history.get("modes", {}):
        before = len(history["modes"][mode_key])
        history["modes"][mode_key] = [
            e for e in history["modes"][mode_key]
            if e["date"] >= cutoff
        ]
        removed = before - len(history["modes"][mode_key])
        if removed:
            log.debug("  🗑 %s: %d entrada(s) antiga(s) removida(s).", mode_key, removed)

    return history


# ---------------------------------------------------------------------------
# Métricas derivadas
# ---------------------------------------------------------------------------

def compute_metrics(history: dict, mode: str) -> dict:
    """
    Calcula métricas a partir do histórico para um modo específico.

    Retorna:
      mmr_history   : lista de MMRs em ordem cronológica
      peak_mmr      : maior MMR dos últimos 30 dias
      trend_value   : variação entre a leitura mais recente e a mais antiga
      trend_arrow   : "▲" ou "▼"
      trend_color   : "#4CAF50" (verde) ou "#F44336" (vermelho) ou "#8899AA" (neutro)
      session_count : número de dias com dados
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
        arrow, color = "▲", "#4CAF50"
    elif diff < 0:
        arrow, color = "▼", "#F44336"
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
# Execução direta (para testes)
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
