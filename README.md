# Rocket League README Stats

An auto-generated SVG widget showcasing your Rocket League ranked statistics. It updates daily via GitHub Actions and can be displayed directly on your GitHub Profile README.

---

## Preview

> *The cards below are automatically generated after the first run.*

| Mode | Widget |
|---|---|
| 3v3 - Ranked Standard | `assets/rl-stats-3v3.svg` |
| 2v2 - Ranked Doubles | `assets/rl-stats-2v2.svg` |
| 1v1 - Ranked Duel | `assets/rl-stats-1v1.svg` |

---

## How to Use on Your Profile README

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

## Setup (for fork or personal use)

### 1. Prerequisites

- Python 3.12+
- A [Rocket League Tracker Network](https://rocketleague.tracker.network/) account

### 2. Configure Repository Secrets

Go to **Settings -> Secrets and variables -> Actions -> New repository secret**:

| Name | Value |
|---|---|
| `EPIC_DISPLAY_NAME` | Your TRN display name (e.g., `zen`) (Required) |
| `SCRAPER_API_KEY` | Optional: Your ScraperAPI key for the resilient 3rd proxy layer to bypass WAF. |

### 3. Enable Actions Write Permissions

Go to **Settings -> Actions -> General -> Workflow permissions** and select:
> **Read and write permissions**

### 4. Run Manually to Test

Go to **Actions -> Update Rocket League Stats -> Run workflow**.

### 5. Wait for the Cron Job

The workflow runs automatically every day at **09:00 UTC**.

---

## Project Structure

```
rocket_league_readme_stats/
|-- .github/workflows/update_stats.yml   # CI/CD Automation
|-- assets/                              # Generated SVGs (output)
|   |-- rl-stats-1v1.svg
|   |-- rl-stats-2v2.svg
|   `-- rl-stats-3v3.svg
|-- data/
|   `-- history.json                     # MMR history (last 30 days)
|-- sprites/                             # Official game sprites (ranks and logo)
|-- src/
|   |-- main.py                          # Orchestrator
|   |-- scraper.py                       # 5-layer resilient data collection
|   |-- history_manager.py               # History management
|   |-- chart_generator.py               # matplotlib sparklines
|   `-- svg_builder.py                   # Glassmorphism SVG generation and Base64 sprite injection
|-- templates/
|   `-- card_template.svg                # Base SVG template with placeholders
`-- requirements.txt
```

---

## Technologies & Resiliency

To prevent blocks from Cloudflare WAF on the Tracker Network, this project uses a 5-layer progressive scraping fallback system:

| Component | Technology |
|---|---|
| **Scraper (Layer 1)** | `curl_cffi` - Impersonates browser TLS fingerprints |
| **Scraper (Layer 2)** | `Playwright` + `playwright-stealth` - Headless browser intercept |
| **Scraper (Layer 3)** | `ScraperAPI` - Premium residential proxy bypass (optional) |
| **Scraper (Layer 4)** | `cloudscraper` - Generic JS bypass |
| **Scraper (Layer 5)** | `requests` - Standard HTTP fallback |
| **Processing** | Native `json` for data and history manipulation |
| **Visualization** | `matplotlib` (PNG sparklines) + Glassmorphism SVG aesthetic |
| **Templating** | Base64 injected PNG sprites inside native SVG placeholders |
| **Automation** | GitHub Actions (Daily cron + `xvfb` for headed browser) |

---

## How to Contribute

Contributions are welcome! If you want to add new features, improve the scraping layers, or create new SVG visual themes, feel free to submit a pull request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure to run the script locally (`python src/main.py`) before submitting the PR to ensure everything works as expected.

---

## License

MIT - see [LICENSE](LICENSE).
