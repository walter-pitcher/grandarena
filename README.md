## Grand Arena Scrapers

This repository contains two Playwright-based scrapers for the Grand Arena ecosystem:

- `scrape_contests.py` – scrapes current contests from `https://fantasy.grandarena.gg/contests`
- `scrape_leaderboards.py` – scrapes leaderboard entries from `https://train.grandarena.gg/leaderboards`

All scraped data is written into a dedicated `data` directory so it is easy to keep raw data separated from code.

---

### How to run this project

1. **Clone and enter the repo:**
   ```bash
   git clone <your-repo-url> grandarena
   cd grandarena
   ```

2. **Create a virtual environment (recommended) and activate it:**
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate   # Git Bash / WSL
   # or:  .venv\Scripts\activate   # cmd / PowerShell
   ```

3. **Install dependencies and Playwright browser:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Run the scrapers:**
   ```bash
   python run_scraping.py
   ```
   This runs both the contest and leaderboard scrapers and writes CSV/JSON under `data/`.  
   - Contests only: `python run_scraping.py --contests`  
   - Leaderboards only: `python run_scraping.py --leaderboards`  
   - Repeat every 30 minutes: `python run_scraping.py --every 30`  
   - Show browser: `python run_scraping.py --show`

**One-click (Windows):** Double-click `run.bat` to set up the venv, install deps, and start the scheduler (runs every 30 minutes until you press Ctrl+C).

See sections below for prerequisites, data layout, and detailed options for each script.

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

All scraping output is written under the `data` directory at the project root, using subdirectories per scraper:

- `data/contests/`
  - `data/contests/contests_open_YYYYMMDD_HHMM.csv`
  - `data/contests/contests_open_YYYYMMDD_HHMM.json`
  - `data/contests/contests_open_latest.csv`
  - `data/contests/contests_open_latest.json`
  - `data/contests/contests_YYYYMMDD_HHMM.csv` (legacy name, still written)
  - `data/contests/contests_YYYYMMDD_HHMM.json` (legacy name, still written)
  - `data/contests/contests_latest.csv` (legacy name, still written)
  - `data/contests/contests_latest.json` (legacy name, still written)

- `data/leaderboards/`
  - `data/leaderboards/leaderboards_all_entries_YYYYMMDD_HHMM.csv`
  - `data/leaderboards/leaderboards_all_entries_YYYYMMDD_HHMM.json`
  - `data/leaderboards/leaderboards_all_entries_latest.csv`
  - `data/leaderboards/leaderboards_all_entries_latest.json`
  - `data/leaderboards/leaderboards_YYYYMMDD_HHMM.csv` (legacy name, still written)
  - `data/leaderboards/leaderboards_YYYYMMDD_HHMM.json` (legacy name, still written)
  - `data/leaderboards/leaderboards_latest.csv` (legacy name, still written)
  - `data/leaderboards/leaderboards_latest.json` (legacy name, still written)
  - `data/leaderboards/leaderboards_champion_YYYYMMDD_HHMM.csv`
  - `data/leaderboards/leaderboards_champion_YYYYMMDD_HHMM.json`
  - `data/leaderboards/leaderboards_champion_latest.csv`
  - `data/leaderboards/leaderboards_champion_latest.json`
  - `data/leaderboards/leaderboards_non_champion_YYYYMMDD_HHMM.csv`
  - `data/leaderboards/leaderboards_non_champion_YYYYMMDD_HHMM.json`
  - `data/leaderboards/leaderboards_non_champion_latest.csv`
  - `data/leaderboards/leaderboards_non_champion_latest.json`

- `data/mokis/`
  - `data/mokis/mokis_all_from_leaderboards_YYYYMMDD_HHMM.csv`
  - `data/mokis/mokis_all_from_leaderboards_YYYYMMDD_HHMM.json`
  - `data/mokis/mokis_all_from_leaderboards_latest.csv`
  - `data/mokis/mokis_all_from_leaderboards_latest.json`

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
  - `start_time` (clock time or countdown, whatever the site shows)
  - `rarity_restriction` (human-friendly summary derived from caps)
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

- `data/contests_open_YYYYMMDD_HHMM.csv`
- `data/contests_open_YYYYMMDD_HHMM.json`
- `data/contests_open_latest.csv` (overwritten each run)
- `data/contests_open_latest.json` (overwritten each run)
- Legacy filenames (`contests_*.csv/json`, `contests_latest.*`) are also still written for compatibility.

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
- Additionally, after scraping all leaderboard entries it builds a **unique Moki catalogue** (Champions and Non-Champions) derived from those entries and saves it separately.

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

- `--max-rank N` / `--top N` – stop after scraping N ranks per category

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

- Combined files (all leaderboard entries):
  - `data/leaderboards/leaderboards_all_entries_YYYYMMDD_HHMM.csv`
  - `data/leaderboards/leaderboards_all_entries_YYYYMMDD_HHMM.json`
  - `data/leaderboards/leaderboards_all_entries_latest.csv` (overwritten each run)
  - `data/leaderboards/leaderboards_all_entries_latest.json` (overwritten each run)
  - Legacy names (`data/leaderboards/leaderboards_*.csv/json`, `data/leaderboards/leaderboards_latest.*`) are also still written.

- Per-category files:
  - `data/leaderboards/leaderboards_champion_YYYYMMDD_HHMM.csv`
  - `data/leaderboards/leaderboards_champion_YYYYMMDD_HHMM.json`
  - `data/leaderboards/leaderboards_champion_latest.csv`
  - `data/leaderboards/leaderboards_champion_latest.json`
  - `data/leaderboards/leaderboards_non_champion_YYYYMMDD_HHMM.csv`
  - `data/leaderboards/leaderboards_non_champion_YYYYMMDD_HHMM.json`
  - `data/leaderboards/leaderboards_non_champion_latest.csv`
  - `data/leaderboards/leaderboards_non_champion_latest.json`

- Unique Moki catalogue (derived from all leaderboard entries):
  - `data/mokis/mokis_all_from_leaderboards_YYYYMMDD_HHMM.csv`
  - `data/mokis/mokis_all_from_leaderboards_YYYYMMDD_HHMM.json`
  - `data/mokis/mokis_all_from_leaderboards_latest.csv`
  - `data/mokis/mokis_all_from_leaderboards_latest.json`

  > Note: this catalogue is as complete as the leaderboard UI itself. If some Mokis do not appear on any leaderboard page, they will not be present here.

If no entries are scraped, the script prints a message and exits with code 1.

---

### 6. Using the combined runner (`run_scraping.py`)

For a simple, clear interface that shows scraping state and output paths, you can use the combined runner:

```bash
python run_scraping.py
```

This will:

- run the contest scraper (open contests) and print how many contests were saved plus all CSV/JSON paths written
- run the leaderboard scraper, print how many entries and unique Mokis were saved, and list output file paths

Common options:

- **Run only contests**:

  ```bash
  python run_scraping.py --contests
  ```

- **Run only leaderboards + Mokis**:

  ```bash
  python run_scraping.py --leaderboards
  ```

- **Run every 30 minutes (scheduler)** – repeat scraping until you press Ctrl+C:

  ```bash
  python run_scraping.py --every 30
  ```

  You can use any interval in minutes, e.g. `--every 15` or `--every 60`.

- **Show browser windows while scraping**:

  ```bash
  python run_scraping.py --show
  ```

- **Limit leaderboard pages / focus on one category**:

  ```bash
  python run_scraping.py --leaderboards --pages 5 --category champion
  ```

- **Limit leaderboard ranks per category** (faster test runs):

  ```bash
  python run_scraping.py --leaderboards --max-rank 500
  ```

The runner prints timestamps and summaries so you can easily see the scraping state from the terminal.

---

### 7. One-click run (Windows, for juniors)

If you want to run the whole project with a single double-click, use the batch file:

1. **Double-click `run.bat`** (in the project root).

The batch file will:

- Create a Python virtual environment (`.venv`) if it doesn’t exist
- Install dependencies from `requirements.txt` (Playwright)
- Install the Playwright Chromium browser
- Start the scraper in **scheduler mode**: run once, then every **30 minutes**, until you press **Ctrl+C** in the window

**Requirements:** Python 3.10+ must be installed and on your PATH ([python.org/downloads](https://www.python.org/downloads/)). On Windows, the Python installer option “Add Python to PATH” should be checked.

To stop the scheduler, focus the command window and press **Ctrl+C** (once is enough; it will finish the current run and then stop).

---

### 8. Notes for automation

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

### 9. Troubleshooting

- **No data / empty files**
  - Check if the target websites have changed their structure or require login.
  - Try running with `--show` to visually inspect what the browser sees.
- **Playwright errors**
  - Make sure you have run `playwright install chromium`.
  - Ensure your Python version is compatible with the installed Playwright version.
- **Slow or flaky runs**
  - Network or site-side throttling can cause timeouts; re-run the script or reduce pages via `--pages`.

