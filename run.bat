@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Grand Arena - One-click run (install + scrape every 30 min)
echo ============================================================
echo.

REM Prefer Windows Python launcher, then python
set PY=python
where py >nul 2>&1
if %errorlevel% equ 0 (
  set PY=py -3
)

REM Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo ERROR: Could not create .venv. Make sure Python 3.10+ is installed.
    echo        Install from https://www.python.org/downloads/
    pause
    exit /b 1
  )
  echo       Done.
) else (
  echo [1/4] Virtual environment already exists.
)

REM Activate venv and install dependencies
echo.
echo [2/4] Checking Python packages...
call .venv\Scripts\activate.bat
python -c "import playwright" 2>nul
if errorlevel 1 (
  echo       Installing required packages...
  pip install -q -r requirements.txt
  if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
  )
  echo       Done.
) else (
  echo       Packages already installed. Skipping.
)

echo.
echo [3/4] Checking Playwright browser (Chromium)...
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); e=p.chromium.executable_path; p.stop(); exit(0 if e and __import__('os').path.exists(e) else 1)" 2>nul
if errorlevel 1 (
  echo       Installing Chromium...
  playwright install chromium
  if errorlevel 1 (
    echo ERROR: playwright install failed.
    pause
    exit /b 1
  )
  echo       Done.
) else (
  echo       Chromium already installed. Skipping.
)

echo.
echo [4/4] Starting scraper - runs every 30 minutes. Press Ctrl+C to stop.
echo ============================================================
python run_scraping.py --leaderboards --pages 2 --max-rank 180 --every 30

echo.
echo Scraping stopped.
pause
