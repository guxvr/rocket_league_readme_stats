# 🚀 Rocket League README Stats

An auto-generated SVG widget showcasing your Rocket League ranked statistics. It updates daily via GitHub Actions and can be displayed directly on your GitHub Profile README.

---

## 📊 Preview

> *The cards below are automatically generated after the first run.*

| Mode | Widget |
|---|---|
| 3v3 — Ranked Standard | `assets/rl-stats-3v3.svg` |
| 2v2 — Ranked Doubles | `assets/rl-stats-2v2.svg` |
| 1v1 — Ranked Duel | `assets/rl-stats-1v1.svg` |

---

## ⚙️ How to Use on Your Profile README

Add the corresponding `<img>` tag for the mode you want to display in your profile `README.md`:

```html
<!-- Replace YOUR_USERNAME with your actual GitHub username -->

<!-- 3v3 Mode -->
<a href="https://rocketleague.tracker.network/rocket-league/profile/epic/guxvr/overview">
  <img
    src="https://raw.githubusercontent.com/YOUR_USERNAME/rocket_league_readme_stats/main/assets/rl-stats-3v3.svg"
    alt="Rocket League 3v3 Stats"
    width="495"
  />
</a>

<!-- 2v2 Mode -->
<img
  src="https://raw.githubusercontent.com/YOUR_USERNAME/rocket_league_readme_stats/main/assets/rl-stats-2v2.svg"
  alt="Rocket League 2v2 Stats"
  width="495"
/>

<!-- 1v1 Mode -->
<img
  src="https://raw.githubusercontent.com/YOUR_USERNAME/rocket_league_readme_stats/main/assets/rl-stats-1v1.svg"
  alt="Rocket League 1v1 Stats"
  width="495"
/>
```

---

## 🔧 Setup (for fork or personal use)

### 1. Prerequisites

- Python 3.12+
- A [Rocket League Tracker Network](https://rocketleague.tracker.network/) account

### 2. Configure Repository Secret

Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `EPIC_DISPLAY_NAME` | Your TRN display name (e.g., `guxvr`) |

### 3. Enable Actions Write Permissions

Go to **Settings → Actions → General → Workflow permissions** and select:
> ✅ **Read and write permissions**

### 4. Run Manually to Test

Go to **Actions → Update Rocket League Stats → Run workflow**.

### 5. Wait for the Cron Job

The workflow runs automatically every day at **09:00 UTC**.

---

## 🏗️ Project Structure

```
rocket_league_readme_stats/
├── .github/workflows/update_stats.yml   # CI/CD Automation
├── assets/                              # Generated SVGs (output)
│   ├── rl-stats-1v1.svg
│   ├── rl-stats-2v2.svg
│   └── rl-stats-3v3.svg
├── data/
│   └── history.json                     # MMR history (last 30 days)
├── src/
│   ├── main.py                          # Orchestrator
│   ├── scraper.py                       # Data collection (curl_cffi + Playwright)
│   ├── history_manager.py               # History management
│   ├── chart_generator.py               # matplotlib sparklines
│   └── svg_builder.py                   # SVG template injection
├── templates/
│   └── card_template.svg                # Base SVG template with placeholders
└── requirements.txt
```

---

## 🛡️ Technologies

| Component | Technology |
|---|---|
| **Scraper (Layer 1)** | [`curl_cffi`](https://github.com/yifeikong/curl_cffi) — Direct JSON API |
| **Scraper (Layer 2)** | [`Playwright`](https://playwright.dev/python/) + [`playwright-stealth`](https://github.com/AtuboDad/playwright_stealth) |
| **Processing** | Native `json` for data and history manipulation |
| **Visualization** | `matplotlib` (PNG sparkline → base64) |
| **Templating** | Native SVG with placeholders |
| **Automation** | GitHub Actions (Daily cron + `xvfb` for headed browser) |

---

## 📄 License

MIT — see [LICENSE](LICENSE).
