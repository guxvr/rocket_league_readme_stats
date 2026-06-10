# 🚀 Rocket League README Stats

Widget SVG gerado automaticamente com as suas estatísticas ranqueadas do Rocket League, atualizado diariamente via GitHub Actions e exibido no Profile README do GitHub.

---

## 📊 Preview

> *Os cards abaixo são gerados automaticamente após a primeira execução.*

| Modo | Widget |
|---|---|
| 3v3 — Ranked Standard | `assets/rl-stats-3v3.svg` |
| 2v2 — Ranked Doubles | `assets/rl-stats-2v2.svg` |
| 1v1 — Ranked Duel | `assets/rl-stats-1v1.svg` |

---

## ⚙️ Como usar no seu Profile README

Adicione a tag `<img>` correspondente ao modo que deseja exibir no seu `README.md` de perfil:

```html
<!-- Substitua SEU_USUARIO pelo seu nome de usuário do GitHub -->

<!-- Modo 3v3 -->
<a href="https://rocketleague.tracker.network/rocket-league/profile/epic/guxvr/overview">
  <img
    src="https://raw.githubusercontent.com/SEU_USUARIO/rocket_league_readme_stats/main/assets/rl-stats-3v3.svg"
    alt="Rocket League 3v3 Stats"
    width="495"
  />
</a>

<!-- Modo 2v2 -->
<img
  src="https://raw.githubusercontent.com/SEU_USUARIO/rocket_league_readme_stats/main/assets/rl-stats-2v2.svg"
  alt="Rocket League 2v2 Stats"
  width="495"
/>

<!-- Modo 1v1 -->
<img
  src="https://raw.githubusercontent.com/SEU_USUARIO/rocket_league_readme_stats/main/assets/rl-stats-1v1.svg"
  alt="Rocket League 1v1 Stats"
  width="495"
/>
```

---

## 🔧 Setup (para fork ou uso próprio)

### 1. Pré-requisitos

- Python 3.12+
- Conta no [Rocket League Tracker Network](https://rocketleague.tracker.network/)

### 2. Configurar o Secret no repositório

Vá em **Settings → Secrets and variables → Actions → New repository secret**:

| Nome | Valor |
|---|---|
| `EPIC_DISPLAY_NAME` | Seu nome de exibição no TRN (ex: `guxvr`) |

### 3. Habilitar permissões de escrita para o Actions

Vá em **Settings → Actions → General → Workflow permissions** e selecione:
> ✅ **Read and write permissions**

### 4. Testar manualmente

Vá em **Actions → Update Rocket League Stats → Run workflow**.

### 5. Aguardar o cron automático

O workflow roda automaticamente todo dia às **09:00 UTC (06:00 horário de Brasília)**.

---

## 🏗️ Estrutura do Projeto

```
rocket_league_readme_stats/
├── .github/workflows/update_stats.yml   # Automação CI/CD
├── assets/                              # SVGs gerados (output)
│   ├── rl-stats-1v1.svg
│   ├── rl-stats-2v2.svg
│   └── rl-stats-3v3.svg
├── data/
│   └── history.json                     # Histórico de MMR (30 dias)
├── src/
│   ├── main.py                          # Orquestrador
│   ├── scraper.py                       # Coleta (curl_cffi + Playwright)
│   ├── history_manager.py               # Gestão do histórico
│   ├── chart_generator.py               # Sparkline matplotlib
│   └── svg_builder.py                   # Injeção no template SVG
├── templates/
│   └── card_template.svg                # Template com placeholders
└── requirements.txt
```

---

## 🛡️ Tecnologias

| Componente | Tecnologia |
|---|---|
| **Coleta (Camada 1)** | [`curl_cffi`](https://github.com/yifeikong/curl_cffi) — API JSON direta |
| **Coleta (Camada 2)** | [`Playwright`](https://playwright.dev/python/) + [`playwright-stealth`](https://github.com/AtuboDad/playwright_stealth) |
| **Processamento** | `json` nativo para manipulação de dados e histórico |
| **Visualização** | `matplotlib` (sparkline PNG → base64) |
| **Template** | SVG nativo com placeholders |
| **Automação** | GitHub Actions (cron diário + `xvfb` para headed browser) |

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE).
