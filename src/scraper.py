"""
scraper.py
==========
Coleta o MMR atual dos modos 1v1, 2v2 e 3v3 do Rocket League
via API interna do Tracker Network (api.tracker.gg).

Estratégia:
  Camada 1 — curl_cffi (API JSON direta, impersona TLS do Chrome)
  Camada 2 — Playwright (browser headless com interceptação de API)

A API `api.tracker.gg/api/v2/rocket-league/standard/profile/epic/{username}`
retorna JSON estruturado com MMR e rank de cada playlist. Não requer
chave de API explícita — apenas headers de browser legítimo.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

DISPLAY_NAME: str = os.environ.get("EPIC_DISPLAY_NAME", "guxvr")

API_BASE = "https://api.tracker.gg/api/v2/rocket-league/standard/profile/epic"
PROFILE_URL = f"{API_BASE}/{DISPLAY_NAME}"
SESSIONS_URL = f"{API_BASE}/{DISPLAY_NAME}/sessions"

# IDs das playlists ranqueadas no TRN
PLAYLIST_IDS: dict[int, str] = {
    10: "1v1",   # Ranked Duel
    11: "2v2",   # Ranked Doubles
    13: "3v3",   # Ranked Standard
}

# Headers que imitam a API do app mobile oficial do TRN
# Isso contorna o WAF do Cloudflare de forma extremamente eficaz.
BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": "TrackerNetwork/3.10.1 (iPhone; iOS 15.0; Scale/3.00)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate, br",
}


# ---------------------------------------------------------------------------
# Resultado estruturado
# ---------------------------------------------------------------------------

def _empty_result() -> dict:
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


# ---------------------------------------------------------------------------
# Parser da resposta JSON da API
# ---------------------------------------------------------------------------

def _parse_api_response(data: dict) -> dict:
    """
    Extrai MMR e rank de cada modo a partir do JSON da API do TRN.

    Estrutura esperada:
      data.segments[].attributes.playlistId → int (10/11/13)
      data.segments[].stats.rating.value    → int (MMR)
      data.segments[].stats.tier.metadata.name → str (ex: "Diamond II")
    """
    segments = data.get("data", {}).get("segments", [])
    results: dict[str, dict] = {}

    for seg in segments:
        playlist_id = seg.get("attributes", {}).get("playlistId")
        mode = PLAYLIST_IDS.get(playlist_id)
        if not mode:
            continue  # modo não ranqueado (Hoops, Rumble, etc.)

        stats = seg.get("stats", {})
        rating = stats.get("rating")
        tier = stats.get("tier")

        if not rating or not tier:
            log.debug("  Modo %s sem rating/tier — pulando.", mode)
            continue

        mmr = rating.get("value")
        rank_name = tier.get("metadata", {}).get("name", "Unranked")

        if mmr is None:
            continue

        results[mode] = _mode_entry(int(mmr), rank_name)
        log.info("  ✓ %s — MMR: %d  Rank: %s", mode, int(mmr), rank_name)

    return results


# ---------------------------------------------------------------------------
# Camada 1 — curl_cffi (API JSON direta)
# ---------------------------------------------------------------------------

def _scrape_layer1() -> dict:
    """Chama a API do TRN diretamente com curl_cffi (impersona Chrome TLS)."""
    try:
        from curl_cffi import requests as cffi_requests

        log.info("🔵 Camada 1 — curl_cffi (API direta) iniciando...")
        resp = cffi_requests.get(
            PROFILE_URL,
            impersonate="safari15_5",
            headers=BROWSER_HEADERS,
            timeout=20,
        )

        if resp.status_code == 429:
            log.warning("  ✗ Rate limited (429). Aguardando 5s e escalando.")
            time.sleep(5)
            return {}

        if resp.status_code == 403:
            log.warning("  ✗ Bloqueado (403). Escalando para Camada 2.")
            return {}

        if resp.status_code != 200:
            log.warning("  ✗ Status inesperado: %d. Escalando.", resp.status_code)
            return {}

        data = resp.json()
        modes = _parse_api_response(data)

        if not modes:
            log.warning("  ✗ API retornou 200 mas sem dados de rank. Escalando.")
            return {}

        return modes

    except ImportError:
        log.warning("  ✗ curl_cffi não instalado. Escalando para Camada 2.")
        return {}
    except Exception as exc:
        log.warning("  ✗ Erro na Camada 1: %s. Escalando.", exc)
        return {}


# ---------------------------------------------------------------------------
# Camada 2 — Playwright com interceptação de API
# ---------------------------------------------------------------------------

def _scrape_layer2() -> dict:
    """
    Usa Playwright para navegar na página do TRN e interceptar
    a chamada de API JSON feita pelo Vue.js.
    """
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import stealth_sync

        log.info("🟡 Camada 2 — Playwright (intercept de API) iniciando...")

        captured_data: dict = {}

        def intercept_response(response):
            if "api.tracker.gg" in response.url and "profile/epic" in response.url:
                if response.status == 200:
                    try:
                        captured_data["body"] = response.json()
                        log.info("  ✓ API interceptada: %s", response.url)
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
                locale="pt-BR",
            )
            page = context.new_page()
            stealth_sync(page)
            page.on("response", intercept_response)

            page_url = f"https://rocketleague.tracker.network/rocket-league/profile/epic/{DISPLAY_NAME}/overview"
            log.info("  → Navegando para %s", page_url)

            try:
                page.goto(page_url, wait_until="networkidle", timeout=35_000)
            except Exception:
                log.debug("  networkidle timeout — verificando dados capturados...")

            browser.close()

        if "body" in captured_data:
            modes = _parse_api_response(captured_data["body"])
            if modes:
                return modes

        log.warning("  ✗ Nenhum dado capturado via Playwright.")
        return {}

    except ImportError as e:
        log.warning("  ✗ Playwright ou dependência não instalada: %s", e)
        return {}
    except Exception as exc:
        log.error("  ✗ Erro na Camada 2: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Entrypoint público
# ---------------------------------------------------------------------------

def fetch_stats() -> dict:
    """
    Coleta as estatísticas em camadas progressivas.
    Retorna o resultado estruturado ou um resultado vazio em falha total.
    """
    result = _empty_result()

    # Camada 1 — API direta
    modes = _scrape_layer1()
    if modes:
        result["modes"].update(modes)
        result["source_layer"] = 1
        result["success"] = True
        log.info("✅ Dados coletados via Camada 1 (curl_cffi + API direta).")
        return result

    # Camada 2 — Playwright
    modes = _scrape_layer2()
    if modes:
        result["modes"].update(modes)
        result["source_layer"] = 2
        result["success"] = True
        log.info("✅ Dados coletados via Camada 2 (Playwright).")
        return result

    log.error("❌ Todas as camadas falharam. Nenhum dado coletado.")
    return result


# ---------------------------------------------------------------------------
# Execução direta (para testes)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data = fetch_stats()
    print(json.dumps(data, indent=2, ensure_ascii=False))
