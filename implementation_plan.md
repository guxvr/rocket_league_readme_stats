# 🚀 Plano de Implementação — Rocket League README Stats

Geração automática de widgets SVG com estatísticas ranqueadas (1v1 / 2v2 / 3v3) do Rocket League, atualizados diariamente via GitHub Actions e exibidos no Profile README do GitHub.

---

## Configurações do Projeto

| Parâmetro | Valor |
|---|---|
| **Epic ID (UUID)** | `20a855994d5146efbd029abb777b2656` |
| **Display Name** | `guxvr` |
| **URL do perfil (TRN)** | `https://rocketleague.tracker.network/rocket-league/profile/epic/guxvr/overview` |
| **Modos exibidos** | 1v1, 2v2, 3v3 (usuário escolhe qual embed no README) |
| **Período do gráfico** | Últimos 30 dias (histórico acumulado no próprio repositório) |
| **Repositório** | `rocket_league_readme_stats` |
| **Identidade visual** | Rocket League — dark theme, azul `#00A8E8`, laranja `#FF6B35`, gradients |

---

## Decisões Técnicas Chave

> [!IMPORTANT]
> **Estratégia de coleta em camadas** — sem API pública do TRN, o scraping é obrigatório. Adota-se uma abordagem progressiva de evasão anti-bot:
>
> 1. **Camada 1 (primária): `curl_cffi`** — impersona o TLS fingerprint exato do Chrome/Firefox. Não precisa de browser instalado, é extremamente leve para o GitHub Actions e é a técnica mais eficaz em 2025/2026 contra Cloudflare.
> 2. **Camada 2 (fallback): Playwright + `playwright-stealth`** — roda browser Chromium headless com patches de anti-detecção.
> 3. **Camada 3 (último recurso): Camoufox** — browser Firefox forkeado com stealth máximo embutido.

> [!NOTE]
> **Histórico de 30 dias auto-acumulado** — em vez de depender do DOM do TRN para dados históricos (que pode mudar ou estar indisponível), o script salva o MMR diário em `data/history.json` dentro do próprio repositório. O GitHub Actions commita esse arquivo junto com o SVG a cada execução. Após 30 dias, o histórico completo fica disponível localmente.

---

## Estrutura Final do Repositório

```
rocket_league_readme_stats/
├── .github/
│   └── workflows/
│       └── update_stats.yml       # Cron job diário
├── assets/
│   ├── rl-stats-1v1.svg           # Widget gerado — Modo 1v1
│   ├── rl-stats-2v2.svg           # Widget gerado — Modo 2v2
│   └── rl-stats-3v3.svg           # Widget gerado — Modo 3v3
├── data/
│   └── history.json               # Histórico acumulado de MMR (30 dias)
├── src/
│   ├── scraper.py                 # Coleta de dados (curl_cffi → Playwright)
│   ├── chart_generator.py         # Gera sparkline matplotlib → base64
│   ├── svg_builder.py             # Injeta dados no template SVG
│   ├── history_manager.py         # Lê/escreve/prune history.json
│   └── main.py                    # Orquestrador principal
├── templates/
│   └── card_template.svg          # Template SVG estático com placeholders
├── requirements.txt
├── README.md
└── project_overview.md
```

---

## Fase 1 — Estruturação do Repositório

### [MODIFY] [.gitignore](file:///f:/Users/gustavo/Documents/Projetos/rocket_league_readme_stats/.gitignore)
```gitignore
.venv/
__pycache__/
*.pyc
.env
playwright_debug/
*.png
*.log
```

### [NEW] `requirements.txt`
```
curl-cffi==0.7.3
playwright==1.44.0
playwright-stealth==1.0.6
beautifulsoup4==4.12.3
lxml==5.2.2
matplotlib==3.9.0
```

### [NEW] `data/history.json`
Arquivo inicial (vazio) para bootstrapping:
```json
{
  "player": "guxvr",
  "modes": {
    "1v1": [],
    "2v2": [],
    "3v3": []
  }
}
```
Cada entrada será: `{"date": "2026-06-10", "mmr": 987, "rank": "Diamond II"}`

### [NEW] `templates/card_template.svg`

Template com identidade visual do Rocket League:
- **Fundo:** `#050B12` (quase preto, estilo RL)
- **Borda:** gradiente de `#00A8E8` → `#FF6B35` (1px, border-radius 12px)
- **Tipografia:** `Inter` (importada via `@font-face` ou fallback `system-ui`)
- **Acento:** azul Rocket League `#00A8E8` e laranja `#FF6B35`
- **Ícone:** Logo do Rocket League (SVG inline)
- **Badge de rank:** cor dinâmica por tier

**Placeholders:**
| Placeholder | Conteúdo |
|---|---|
| `{{PLAYER_NAME}}` | Nome do jogador (`guxvr`) |
| `{{MODE_LABEL}}` | Rótulo do modo (`1v1 · Ranked Duel`) |
| `{{MMR_VALUE}}` | MMR atual (`987`) |
| `{{RANK_NAME}}` | Nome do rank (`Diamond II`) |
| `{{RANK_COLOR}}` | Cor hex do rank (`#2196F3`) |
| `{{PEAK_MMR}}` | MMR mais alto nos 30 dias (`1024`) |
| `{{TREND_ARROW}}` | ▲ ou ▼ dependendo da tendência |
| `{{TREND_VALUE}}` | Variação em pontos (`+42`) |
| `{{TREND_COLOR}}` | Verde `#4CAF50` ou vermelho `#F44336` |
| `{{CHART_B64}}` | Sparkline em base64 |
| `{{LAST_UPDATE}}` | Data da última atualização |

**Paleta de cores por rank tier:**
| Tier | Cor |
|---|---|
| Bronze | `#CD7F32` |
| Silver | `#A8A8A8` |
| Gold | `#FFD700` |
| Platinum | `#00BCD4` |
| Diamond | `#2196F3` |
| Champion | `#9C27B0` |
| Grand Champion | `#F44336` |
| Supersonic Legend | `#FF6B35` |

---

## Fase 2 — Script de Coleta de Dados

### [NEW] `src/scraper.py`

**Fluxo com camadas progressivas:**

```
Camada 1 — curl_cffi:
  1. Fazer GET com impersonação de Chrome 120
  2. Parsear HTML com BeautifulSoup
  3. Localizar seletores de rank por modo
  4. Se dados encontrados → retornar
  5. Se 403/bloqueado → escalar para Camada 2

Camada 2 — Playwright + stealth:
  1. Iniciar Chromium headless
  2. Aplicar playwright-stealth (patches de navigator.webdriver, etc)
  3. Navegar para URL do perfil
  4. Aguardar elemento de rank (timeout 15s)
  5. Extrair MMR e rank de cada modo
  6. Se bloqueado → escalar para Camada 3

Camada 3 — Camoufox:
  1. Iniciar Firefox com Camoufox (stealth máximo)
  2. Repetir extração
  3. Se ainda bloqueado → logar erro e encerrar com código 1
     (Actions falhará, mas sem crashar o histórico)
```

**Estrutura de dados retornada:**
```python
{
    "player_name": "guxvr",
    "scraped_at": "2026-06-10",
    "source_layer": 1,  # qual camada teve sucesso
    "modes": {
        "1v1": {"mmr": 850, "rank": "Platinum III", "rank_tier": "platinum"},
        "2v2": {"mmr": 987, "rank": "Diamond II", "rank_tier": "diamond"},
        "3v3": {"mmr": 1102, "rank": "Diamond III", "rank_tier": "diamond"}
    }
}
```

> [!NOTE]
> O script extrairá apenas o **MMR atual** do TRN — o histórico temporal será construído pelo `history_manager.py`.

### [NEW] `src/history_manager.py`

**Responsabilidades:**
1. Carregar `data/history.json`
2. Fazer append da leitura do dia atual para cada modo
3. Remover entradas com mais de 30 dias (sliding window)
4. Calcular métricas derivadas:
   - MMR peak (30d)
   - Variação vs. ontem (`trend_value`, `trend_arrow`)
5. Salvar `history.json` atualizado

```python
def load_history() -> dict
def append_today(history: dict, data: dict) -> dict
def prune_old_entries(history: dict, days: int = 30) -> dict
def compute_metrics(history: dict, mode: str) -> dict
    # retorna: {"mmr_history": [...], "peak_mmr": 1024, "trend": +42}
def save_history(history: dict) -> None
```

---

## Fase 3 — Geração do Gráfico e Injeção no SVG

### [NEW] `src/chart_generator.py`

**Especificações do sparkline:**
- Dimensões: `380 × 60px`
- Fundo: transparente
- Linha: `#00A8E8`, espessura `2.5px`, com `antialiased`
- Área sob a curva: preenchimento com gradiente de `#00A8E8` (20% opacidade → 0%)
- Pontos: círculo branco (`#FFFFFF`) apenas no primeiro e último ponto
- Sem eixos, ticks, labels ou bordas
- Output: string base64 PNG para embutir no SVG

```python
def generate_sparkline(mmr_history: list[int]) -> str:
    """Retorna string base64 do sparkline PNG."""
```

**Tratamento especial:** Se o histórico tiver menos de 2 pontos (primeiros dias), gerar uma linha reta horizontal como placeholder.

### [NEW] `src/svg_builder.py`

```python
def build_svg(template_path: str, mode: str, player_data: dict, metrics: dict, chart_b64: str) -> str:
    """Substitui todos os placeholders e retorna SVG como string."""

def save_svg(svg_content: str, output_path: str) -> None:
    """Salva SVG final em assets/rl-stats-{mode}.svg"""
```

### [NEW] `src/main.py`

```
1. Chamar scraper.py → dados do dia
2. Chamar history_manager.py → append + prune → métricas por modo
3. Para cada modo (1v1, 2v2, 3v3):
   a. Chamar chart_generator.py → sparkline base64
   b. Chamar svg_builder.py → SVG final
   c. Salvar em assets/rl-stats-{modo}.svg
4. Salvar history.json atualizado
5. Logar resumo no stdout (layer usada, MMR de cada modo)
```

---

## Fase 4 — Automação via GitHub Actions

### [NEW] `.github/workflows/update_stats.yml`

```yaml
name: Update Rocket League Stats

on:
  schedule:
    - cron: '0 9 * * *'     # 09:00 UTC = 06:00 horário de Brasília
  workflow_dispatch:          # Permite disparo manual para testes

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write        # Necessário para git push

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright browsers (fallback)
        run: playwright install chromium --with-deps

      - name: Run stats updater
        run: python src/main.py
        env:
          EPIC_DISPLAY_NAME: ${{ secrets.EPIC_DISPLAY_NAME }}

      - name: Commit and push if changed
        run: |
          git config user.name "rl-stats-bot"
          git config user.email "bot@users.noreply.github.com"
          git add assets/ data/
          git diff --staged --quiet || git commit -m "chore: update RL stats [$(date -u +%Y-%m-%d)]"
          git push
```

**Secrets necessários no repositório:**

| Secret | Valor |
|---|---|
| `EPIC_DISPLAY_NAME` | `guxvr` |

> [!NOTE]
> O `GITHUB_TOKEN` nativo do Actions já tem permissão de escrita configurada via `permissions: contents: write`. Não é necessário criar um PAT separado.

---

## Fase 5 — Integração no Profile README

### Embed no README do perfil (`GuxVR/GuxVR`)

O usuário escolhe **qual modo** exibir adicionando a tag `<img>` correspondente:

```html
<!-- Modo 3v3 (Soccar — mais popular) -->
<a href="https://rocketleague.tracker.network/rocket-league/profile/epic/guxvr/overview">
  <img
    src="https://raw.githubusercontent.com/GuxVR/rocket_league_readme_stats/main/assets/rl-stats-3v3.svg"
    alt="Rocket League 3v3 Stats"
    width="495"
  />
</a>

<!-- Modo 2v2 -->
<img src="...rl-stats-2v2.svg" alt="Rocket League 2v2 Stats" width="495" />

<!-- Modo 1v1 -->
<img src="...rl-stats-1v1.svg" alt="Rocket League 1v1 Stats" width="495" />
```

> [!NOTE]
> O GitHub faz cache de imagens raw por ~5 minutos. Para forçar refresh durante testes, adicione `?nocache=1` à URL.

---

## Plano de Verificação

### Etapa 1 — Teste local do scraper
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

python src/scraper.py   # testar isoladamente com print()
# Verificar: MMR retornado para os 3 modos, qual layer foi usada
```

### Etapa 2 — Teste local completo
```bash
python src/main.py
# Verificar:
# → assets/rl-stats-1v1.svg, 2v2.svg, 3v3.svg gerados
# → data/history.json atualizado com entrada do dia
# → SVGs abrem corretamente no browser
```

### Etapa 3 — Teste no GitHub Actions
1. Push para `main` com workflow configurado
2. Disparar manualmente via **Actions → Run workflow**
3. Verificar logs de cada step (qual layer do scraper teve sucesso)
4. Confirmar commit automático com `[bot]` no histórico
5. Abrir SVG via URL raw do GitHub e verificar renderização

### Etapa 4 — Verificação do cron
- Aguardar execução automática no dia seguinte (09:00 UTC)
- Verificar que `history.json` acumulou 2 entradas

### Critérios de Aceite
- [ ] Scraper retorna dados válidos para os 3 modos localmente
- [ ] `history.json` é atualizado e prunado corretamente
- [ ] SVGs gerados renderizam com identidade visual do RL
- [ ] GitHub Actions executa sem falhas
- [ ] Commit automático aparece no histórico do repositório
- [ ] Widget renderiza corretamente no Profile README
- [ ] Cron job executa no horário configurado

---

## Tabela de Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| `curl_cffi` bloqueado no Actions (IP datacenter) | Média | Alto | Fallback automático para Playwright + stealth |
| Playwright também bloqueado | Baixa-Média | Alto | Fallback para Camoufox; action falha graciosamente sem corromper histórico |
| Estrutura HTML do TRN muda | Média | Médio | Seletores CSS com atributos de dados semânticos; alertas via Action failure |
| Histórico inconsistente (dias sem execução) | Baixa | Baixo | `history_manager` tolera gaps; gráfico exibe apenas os pontos disponíveis |
| Rate limiting do TRN | Baixa | Médio | Execução 1x/dia + delays entre requests |
| Token do GitHub sem permissão de push | Baixa | Alto | Usar `permissions: contents: write` nativo (sem PAT) |
