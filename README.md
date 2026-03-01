## Grand Arena Scrapers

This repository contains scrapers and an API fetcher for the Grand Arena ecosystem:

- **`scrape_contests.py`** – Playwright scraper for current contests from `https://fantasy.grandarena.gg/contests`
- **`fetch_mokis_api.py`** – Fetches mokis data from webhook APIs (no browser). Writes to `data/mokis/champion/` and `data/mokis/non-champion/`.
- **`launcher.html`** – Web UI to choose what to run (contests, mokis, or both), browser visibility, and schedule; downloads a custom `.bat` to run from your project folder.

All data is written into a dedicated `data` directory so it is easy to keep raw data separated from code.

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
   This runs both the contest scraper and the mokis fetcher (API, no browser).  
   - Contests only: `python run_scraping.py --contests`  
   - Mokis only: `python run_scraping.py --mokis` (writes to `data/mokis/champion/` and `data/mokis/non-champion/`)  
   - Repeat every 30 minutes: `python run_scraping.py --every 30`  
   - Show browser (contests only): `python run_scraping.py --show`

**One-click (Windows):** Double-click `run.bat` to set up the venv, install deps, and start the runner in scheduler mode: **contests** and **mokis** run once, then every 30 minutes until you press Ctrl+C.

**Custom launcher (any OS):** Open `launcher.html` in a browser to pick options (contests only, mokis only, or both; show browser; run once or every N minutes), then click **Start** to download `run_grandarena.bat`. Save the file in your project folder and double-click it to run (Windows). The batch file uses the project’s `.venv` if present.

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

3. **Install Python dependencies and Playwright browser**:

```bash
pip install -r requirements.txt
playwright install chromium
```

---

### 3. Data directory layout

All scraping output is written under the `data` directory at the project root, using subdirectories per scraper:

- `data/contests/`
  - `data/contests/contests_open_YYYY-MM-DD_HHMM.csv`
  - `data/contests/contests_open_YYYY-MM-DD_HHMM.json`
  - `data/contests/contests_open_latest.csv`
  - `data/contests/contests_open_latest.json`
  - `data/contests/contests_YYYY-MM-DD_HHMM.csv` (legacy name, still written)
  - `data/contests/contests_YYYY-MM-DD_HHMM.json` (legacy name, still written)
  - `data/contests/contests_latest.csv` (legacy name, still written)
  - `data/contests/contests_latest.json` (legacy name, still written)

- `data/mokis/` (from API via `run_scraping.py --mokis` or `fetch_mokis_api.py`):
  - `data/mokis/champion/mokis_YYYY-MM-DD_HHMM.csv`
  - `data/mokis/champion/mokis_YYYY-MM-DD_HHMM.json`
  - `data/mokis/champion/mokis_latest.csv`
  - `data/mokis/champion/mokis_latest.json`
  - `data/mokis/non-champion/mokis_YYYY-MM-DD_HHMM.csv`
  - `data/mokis/non-champion/mokis_YYYY-MM-DD_HHMM.json`
  - `data/mokis/non-champion/mokis_latest.csv`
  - `data/mokis/non-champion/mokis_latest.json`

The timestamp format used is `YYYY-MM-DD_HHMM` in UTC (dashes in date for clarity).

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

After a successful run you will get (under `data/contests/`):

- `data/contests/contests_open_YYYY-MM-DD_HHMM.csv`
- `data/contests/contests_open_YYYY-MM-DD_HHMM.json`
- `data/contests/contests_open_latest.csv` (overwritten each run)
- `data/contests/contests_open_latest.json` (overwritten each run)
- Legacy filenames (`contests_*.csv/json`, `contests_latest.*`) in the same directory are also written for compatibility.

If no contests are found, the script prints a message and exits with a non-zero status (for easier automation).

---

### 5. Mokis data (API) – `fetch_mokis_api.py`

**Script:** `fetch_mokis_api.py`

**What it does**

- Fetches raw JSON from two webhook URLs (Champion and Non-Champion).
- Saves the raw API response as JSON and, when the response contains a list of rows, also saves CSV.
- Writes to `data/mokis/champion/` and `data/mokis/non-champion/`. No filtering of rows or columns.

**How to run**

Standalone:

```bash
python fetch_mokis_api.py
```

Or via the runner:

```bash
python run_scraping.py --mokis
```

**Outputs**

- `data/mokis/champion/mokis_YYYY-MM-DD_HHMM.csv`, `mokis_YYYY-MM-DD_HHMM.json`, `mokis_latest.csv`, `mokis_latest.json`
- `data/mokis/non-champion/` – same pattern.

On API errors, error-stub JSON files are written so the run is visible and paths are clear.

---

### 6. Using the combined runner (`run_scraping.py`)

For a simple, clear interface that shows scraping state and output paths, use the combined runner:

```bash
python run_scraping.py
```

This will:

- run the contest scraper (open contests) and print how many contests were saved plus all CSV/JSON paths written
- run the **mokis** step via API (no browser). Prints entry counts and output file paths.

Common options:

- **Run only contests**:

  ```bash
  python run_scraping.py --contests
  ```

- **Run only mokis** (writes to `data/mokis/champion/` and `data/mokis/non-champion/`):

  ```bash
  python run_scraping.py --mokis
  ```

- **Run every 30 minutes (scheduler)** – repeat until you press Ctrl+C:

  ```bash
  python run_scraping.py --every 30
  ```

  You can use any interval in minutes, e.g. `--every 15` or `--every 60`.

- **Show browser windows** (contests scraper only):

  ```bash
  python run_scraping.py --show
  ```

The runner prints timestamps and summaries so you can easily see the scraping state from the terminal.

---

### 7. One-click run (Windows)

1. **Double-click `run.bat`** (in the project root).

The batch file will:

- Create a Python virtual environment (`.venv`) if it doesn’t exist
- Install dependencies from `requirements.txt` (Playwright)
- Install the Playwright Chromium browser
- Start the runner in **scheduler mode**: run **contests** and **mokis** once, then every **30 minutes**, until you press **Ctrl+C** in the window. Mokis are fetched via API (no browser).

**Requirements:** Python 3.10+ must be installed and on your PATH ([python.org/downloads](https://www.python.org/downloads/)). On Windows, the Python installer option “Add Python to PATH” should be checked.

To stop the scheduler, focus the command window and press **Ctrl+C** (once is enough; it will finish the current run and then stop).

---

### 8. Web launcher (`launcher.html`)

Open **`launcher.html`** in a web browser for a simple UI that lets you:

- Choose what to run: **Both** (contests + mokis), **Contests only**, or **Mokis only**
- Toggle **Show browser windows** (for the contest scraper)
- Set **Run once** or **Every N minutes**

Click **Start – download launcher** to download `run_grandarena.bat`. Save it in your project root (e.g. `C:\git\grandarena`), then double-click to run. The batch file activates `.venv` if it exists and runs `run_scraping.py` with the options you selected. Useful when you want a one-off or custom schedule without editing the command line.

---

### 9. Notes for automation

- All scripts are suitable for use in scheduled tasks (e.g. Windows Task Scheduler, cron, CI jobs). Mokis are fetched via API (no browser).
- Exit codes:
  - `0` – success (data scraped or fetched and written)
  - `1` – no data found or an early-abort condition
- You can safely run these scripts repeatedly; timestamped files will accumulate in `data/`, while the `*_latest.*` files are always overwritten.

Example cron-style usage (pseudo-syntax, adapt for your scheduler):

```bash
cd /c/git/grandarena
source .venv/Scripts/activate
python scrape_contests.py
python run_scraping.py --mokis
```

---

### 10. Troubleshooting

- **No data / empty files**
  - Check if the target websites have changed their structure or require login.
  - Try running with `--show` to visually inspect what the browser sees.
- **Playwright errors**
  - Make sure you have run `playwright install chromium`.
  - Ensure your Python version is compatible with the installed Playwright version.
- **Slow or flaky runs**
  - Network or site-side throttling can cause timeouts; re-run the script.

