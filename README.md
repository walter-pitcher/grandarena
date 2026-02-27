## Grand Arena Scrapers

This repository contains two Playwright-based scrapers for the Grand Arena ecosystem:

- `scrape_contests.py` – scrapes current contests from `https://fantasy.grandarena.gg/contests`
- `scrape_leaderboards.py` – scrapes leaderboard entries from `https://train.grandarena.gg/leaderboards`

All scraped data is written into a dedicated `data` directory so it is easy to keep raw data separated from code.

---

### 1. Prerequisites

- **Python**: 3.10+ recommended
- **OS**: Developed and tested on Windows 10 using Git Bash (but should work on most platforms supported by Playwright)
- **Package manager**: `pip`

You also need Playwright and its browser binaries installed for Python.

---

### 2. Installation & Setup

1. **Clone the repository** (or open the folder if you already have it):

```bash
cd /c/git
git clone <your-repo-url> grandarena
cd grandarena
```

2. **(Optional but recommended) Create and activate a virtual environment**:

```bash
python -m venv .venv
source .venv/Scripts/activate  # in Git Bash / WSL
# or
.venv\Scripts\activate         # in cmd / PowerShell
```

3. **Install Python dependencies** (example – adapt to your environment if you already have them):

```bash
pip install playwright
playwright install chromium
```

If you see import errors for other packages when running the scripts, install them with `pip install <package-name>`.

---

### 3. Data directory layout

All scraping output is written to the `data` directory at the project root:

- `data/contests_YYYYMMDD_HHMM.csv`
- `data/contests_YYYYMMDD_HHMM.json`
- `data/contests_latest.csv`
- `data/contests_latest.json`
- `data/leaderboards_YYYYMMDD_HHMM.csv`
- `data/leaderboards_YYYYMMDD_HHMM.json`
- `data/leaderboards_latest.csv`
- `data/leaderboards_latest.json`
- `data/leaderboards_champion_YYYYMMDD_HHMM.csv`
- `data/leaderboards_champion_YYYYMMDD_HHMM.json`
- `data/leaderboards_champion_latest.csv`
- `data/leaderboards_champion_latest.json`
- `data/leaderboards_non_champion_YYYYMMDD_HHMM.csv`
- `data/leaderboards_non_champion_YYYYMMDD_HHMM.json`
- `data/leaderboards_non_champion_latest.csv`
- `data/leaderboards_non_champion_latest.json`

The timestamp format used is `YYYYMMDD_HHMM` in UTC.

---

### 4. Using the contest scraper (`scrape_contests.py`)

**Script:** `scrape_contests.py`

**What it does**

- Opens `https://fantasy.grandarena.gg/contests`
- Clicks through the filter tabs: `Free`, `100-499`, `500-1000`, `1000+`
- For every visible contest card, collects:
  - `contest_type`
  - `contest_name`
  - `prize_pool`
  - `entry_fee`
  - `spots_remaining`
  - `max_entries_per_player`
  - `start_time`
  - `star_rank_cap`
  - `slot_rarity_caps`
  - `filter_tab`
  - `date_scraped` (UTC)

**How to run**

From the project root:

```bash
python scrape_contests.py
```

By default the browser runs **headless**. To see the browser window while scraping, pass `--show`:

```bash
python scrape_contests.py --show
```

**Outputs**

After a successful run you will get:

- `data/contests_YYYYMMDD_HHMM.csv`
- `data/contests_YYYYMMDD_HHMM.json`
- `data/contests_latest.csv` (overwritten each run)
- `data/contests_latest.json` (overwritten each run)

If no contests are found, the script prints a message and exits with a non-zero status (for easier automation).

---

### 5. Using the leaderboard scraper (`scrape_leaderboards.py`)

**Script:** `scrape_leaderboards.py`

**What it does**

- Opens `https://train.grandarena.gg/leaderboards`
- Scrapes both **Champion** and **Non-Champion** leaderboards (configurable)
- For each leaderboard row, clicks to open the detail modal and collects:
  - `rank`
  - `moki_name`
  - `moki_id`
  - `score`
  - `class`
  - `rarity`
  - `stat_strength`
  - `stat_speed`
  - `stat_defense`
  - `stat_dexterity`
  - `stat_fortitude`
  - `image_url`
  - `thumbnail_url`
  - `category` (`Champion` / `Non-Champion`)
  - `page`
  - `date_scraped` (UTC)

**Basic run (all pages, both categories, headless)**:

```bash
python scrape_leaderboards.py
```

**Options**

- `--show` – run with a visible browser

  ```bash
  python scrape_leaderboards.py --show
  ```

- `--pages N` – limit the number of pages per category (e.g. scrape only first 3 pages)

  ```bash
  python scrape_leaderboards.py --pages 3
  ```

- `--category champion` – scrape only champion leaderboard

  ```bash
  python scrape_leaderboards.py --category champion
  ```

- `--category non-champion` – scrape only non-champion leaderboard

  ```bash
  python scrape_leaderboards.py --category non-champion
  ```

These flags can be combined, for example:

```bash
python scrape_leaderboards.py --category champion --pages 5 --show
```

**Outputs**

On each run you get:

- Combined files:
  - `data/leaderboards_YYYYMMDD_HHMM.csv`
  - `data/leaderboards_YYYYMMDD_HHMM.json`
  - `data/leaderboards_latest.csv` (overwritten each run)
  - `data/leaderboards_latest.json` (overwritten each run)

- Per-category files:
  - `data/leaderboards_champion_YYYYMMDD_HHMM.csv`
  - `data/leaderboards_champion_YYYYMMDD_HHMM.json`
  - `data/leaderboards_champion_latest.csv`
  - `data/leaderboards_champion_latest.json`
  - `data/leaderboards_non_champion_YYYYMMDD_HHMM.csv`
  - `data/leaderboards_non_champion_YYYYMMDD_HHMM.json`
  - `data/leaderboards_non_champion_latest.csv`
  - `data/leaderboards_non_champion_latest.json`

If no entries are scraped, the script prints a message and exits with code 1.

---

### 6. Notes for automation

- Both scripts are suitable for use in scheduled tasks (e.g. Windows Task Scheduler, cron, CI jobs).
- Exit codes:
  - `0` – success (data scraped and written)
  - `1` – no data found or an early-abort condition
- You can safely run these scripts repeatedly; timestamped files will accumulate in `data/`, while the `*_latest.*` files are always overwritten.

Example cron-style usage (pseudo-syntax, adapt for your scheduler):

```bash
cd /c/git/grandarena
source .venv/Scripts/activate
python scrape_contests.py
python scrape_leaderboards.py --pages 5
```

---

### 7. Troubleshooting

- **No data / empty files**
  - Check if the target websites have changed their structure or require login.
  - Try running with `--show` to visually inspect what the browser sees.
- **Playwright errors**
  - Make sure you have run `playwright install chromium`.
  - Ensure your Python version is compatible with the installed Playwright version.
- **Slow or flaky runs**
  - Network or site-side throttling can cause timeouts; re-run the script or reduce pages via `--pages`.

