"""
Grand Arena Fantasy – Contest Scraper
https://fantasy.grandarena.gg/contests

Clicks filter tabs: Free, 100-499, 500-1000, 1000+
For each tab, clicks every contest card and extracts:
  contest_name, prize_pool, entry_fee, spots_remaining,
  max_entries_per_player, start_time, star_rank_cap, slot_rarity_caps

Output: contests.csv  +  contests.json
"""

import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Write contest data into a dedicated subdirectory
OUTPUT_DIR = Path(__file__).parent / "data" / "contests"
CONTESTS_URL = "https://fantasy.grandarena.gg/contests"

FILTER_TABS = ["Free", "100-499", "500-1000", "1000+"]

CARD_SEL  = "button.flex.w-full.p-3"
LABEL_SEL = "span.font-poppins.text-xs.font-semibold.text-\\[\\#A0B0D1\\]"
VALUE_SEL = "span.font-poppins.text-sm.font-medium.text-\\[\\#F2F7FB\\]"


# ── helpers ──────────────────────────────────────────────────────────────────

def safe_text(el) -> str:
    try:
        return (el.inner_text() or "").strip()
    except Exception:
        return ""


def parse_card(card) -> dict:
    """Extract fields directly visible on the contest list card."""
    html = card.inner_html()

    # contest type  (50/50 | Top 20% | Top 10% | Free Entry …)
    m = re.search(r'text-xs h-4[^>]*>([^<]+)<', html)
    contest_type = m.group(1).strip() if m else ""

    # prize pool  ($875.00)
    m = re.search(r'text-2xl[^>]*>([^<]+)<', html)
    prize_pool = m.group(1).strip() if m else ""

    # contest name
    m = re.search(r'-webkit-line-clamp: 2[^>]*>([^<]+)<', html)
    contest_name = m.group(1).strip() if m else ""

    # start time (value after "Starts" label)
    m = re.search(r'>Starts</span><span[^>]*>([^<]+)<', html)
    start_time = m.group(1).strip() if m else ""

    # spots_remaining (value after "Entries" label)
    m = re.search(r'>Entries</span><span[^>]*>([^<]+)<', html)
    spots_remaining = m.group(1).strip() if m else ""

    # max entries per player  – from title attribute or visible text
    m = re.search(r'title="Up to (\d+) entries per player"', html)
    if m:
        max_entries_per_player = f"{m.group(1)}/player"
    else:
        m2 = re.search(r'"Grand Arena"[^>]*>(\d+/player)<', html)
        max_entries_per_player = m2.group(1).strip() if m2 else ""

    # entry fee  (gem amount – last number before end of card; 0 for free contests)
    m = re.search(r'gem-colored[^>]+>.*?<span[^>]*>(\d[\d,]*)<', html, re.S)
    if m:
        entry_fee = m.group(1).replace(",", "")
    else:
        # Free-entry contests show no gem amount
        entry_fee = "0" if "Free Entry" in html or "free" in contest_name.lower() else ""

    return {
        "contest_type":           contest_type,
        "contest_name":           contest_name,
        "prize_pool":             prize_pool,
        "entry_fee":              entry_fee if entry_fee else "Free",
        "spots_remaining":        spots_remaining,
        "max_entries_per_player": max_entries_per_player,
        "start_time":             start_time,
        # filled in after clicking the card:
        "star_rank_cap":          "",
        "slot_rarity_caps":       "",
        # human-friendly combined rarity rule, derived after detail scrape
        "rarity_restriction":     "",
        "date_scraped":           datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "filter_tab":             "",
    }


def parse_detail_panel(page) -> dict:
    """
    After clicking a card, the detail panel appears in-page (no URL change).
    Reads label→value pairs from the stats grid.
    Returns dict with  star_rank_cap  and  slot_rarity_caps.
    """
    result = {"star_rank_cap": "", "slot_rarity_caps": ""}

    try:
        # Wait for the panel title to appear (e.g. "50/50 Open …")
        page.wait_for_selector("text=Exit", timeout=6000)
    except PWTimeout:
        return result

    # Grab all label/value pairs from the info grid
    labels = page.query_selector_all(
        "span.font-poppins.text-xs.font-semibold"
    )
    for lbl_el in labels:
        lbl = safe_text(lbl_el).lower()
        # The value span is a sibling right after the label
        val_el = lbl_el.evaluate_handle(
            "el => el.parentElement.querySelector('span.font-poppins.text-sm')"
        )
        try:
            val = (val_el.as_element().inner_text() or "").strip()
        except Exception:
            val = ""

        if "star rank" in lbl:
            result["star_rank_cap"] = val
        elif "slot rarity" in lbl:
            result["slot_rarity_caps"] = val

    return result


def close_detail_panel(page):
    try:
        page.click("text=Exit", timeout=4000)
        time.sleep(0.8)
    except PWTimeout:
        pass


def scroll_to_load_all(page):
    """Scroll the page slowly to trigger any lazy-loading."""
    for _ in range(6):
        page.keyboard.press("End")
        time.sleep(0.5)
    page.keyboard.press("Home")
    time.sleep(0.5)


# ── main scraping logic ───────────────────────────────────────────────────────

def scrape_all(headless: bool = True) -> list[dict]:
    seen_names: set[str] = set()
    all_contests: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=200)
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        print(f"[*] Loading {CONTESTS_URL} ...")
        page.goto(CONTESTS_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        for tab_name in FILTER_TABS:
            print(f"\n[+] Clicking filter: {tab_name}")

            # Click the filter button
            try:
                page.click(f"button:has-text('{tab_name}')", timeout=8000)
                time.sleep(2)
            except PWTimeout:
                print(f"    [!] Filter button '{tab_name}' not found – skipping")
                continue

            scroll_to_load_all(page)

            # Collect all visible contest cards
            cards = page.query_selector_all(CARD_SEL)
            print(f"    Found {len(cards)} contest cards")

            for i, card in enumerate(cards):
                # Parse card-level data first (before clicking)
                contest = parse_card(card)
                contest["filter_tab"] = tab_name

                name = contest["contest_name"]
                if not name:
                    continue

                # Skip if we've already processed this contest
                if name in seen_names:
                    print(f"    [{i+1}/{len(cards)}] SKIP (duplicate): {name}")
                    continue

                print(f"    [{i+1}/{len(cards)}] {name}")

                # Click the card to open the detail panel
                try:
                    # Re-query cards in case DOM updated
                    fresh_cards = page.query_selector_all(CARD_SEL)
                    if i < len(fresh_cards):
                        fresh_cards[i].click()
                        time.sleep(1.5)
                        detail = parse_detail_panel(page)
                        contest.update(detail)

                        # Derive a single human-friendly rarity_restriction field
                        rarity = (
                            detail.get("slot_rarity_caps") or
                            detail.get("star_rank_cap") or
                            ""
                        )
                        contest["rarity_restriction"] = rarity or "Open"

                        close_detail_panel(page)
                        time.sleep(0.5)
                except Exception as e:
                    print(f"      [!] Click error: {e}")
                    # Try closing panel if it got stuck
                    close_detail_panel(page)

                seen_names.add(name)
                all_contests.append(contest)

        browser.close()

    return all_contests


# ── output ────────────────────────────────────────────────────────────────────

FIELDNAMES = [
    "contest_name",
    "contest_type",
    "prize_pool",
    "entry_fee",
    "spots_remaining",
    "max_entries_per_player",
    "start_time",             # may be a clock time or countdown, as shown on site
    "rarity_restriction",     # derived summary of rarity / star caps
    "star_rank_cap",
    "slot_rarity_caps",
    "filter_tab",
    "date_scraped",
]


def save_csv(contests: list[dict], path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(contests)
    print(f"[OK] CSV  -> {path}")


def save_json(contests: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(contests, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON -> {path}")


def run_contest_scrape(headless: bool = True) -> dict:
    """
    Run the contest scraper and write both timestamped and *_latest files.
    Returns a summary dict with counts and output paths for use by UIs / schedulers.
    """
    # Ensure data directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    contests = scrape_all(headless=headless)

    if not contests:
        print("\n[!] No contests found. Check if the site requires a wallet login.")
        return {
            "ok": False,
            "count": 0,
            "csv_paths": [],
            "json_paths": [],
        }

    print(f"\n[*] Total unique contests scraped: {len(contests)}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    # New, clearer filenames
    csv_ts_new  = OUTPUT_DIR / f"contests_open_{ts}.csv"
    json_ts_new = OUTPUT_DIR / f"contests_open_{ts}.json"
    csv_latest_new  = OUTPUT_DIR / "contests_open_latest.csv"
    json_latest_new = OUTPUT_DIR / "contests_open_latest.json"

    # Legacy filenames kept for backwards compatibility
    csv_ts_legacy  = OUTPUT_DIR / f"contests_{ts}.csv"
    json_ts_legacy = OUTPUT_DIR / f"contests_{ts}.json"
    csv_latest_legacy  = OUTPUT_DIR / "contests_latest.csv"
    json_latest_legacy = OUTPUT_DIR / "contests_latest.json"

    # Write all variants
    for path in (csv_ts_new, csv_ts_legacy, csv_latest_new, csv_latest_legacy):
        save_csv(contests, path)
    for path in (json_ts_new, json_ts_legacy, json_latest_new, json_latest_legacy):
        save_json(contests, path)

    print("\n=== PREVIEW (first 3 rows) ===")
    for c in contests[:3]:
        for k, v in c.items():
            safe_v = str(v).encode("ascii", "replace").decode("ascii")
            print(f"  {k:28s}: {safe_v}")
        print()

    return {
        "ok": True,
        "count": len(contests),
        "csv_paths": [
            str(csv_ts_new),
            str(csv_ts_legacy),
            str(csv_latest_new),
            str(csv_latest_legacy),
        ],
        "json_paths": [
            str(json_ts_new),
            str(json_ts_legacy),
            str(json_latest_new),
            str(json_latest_legacy),
        ],
    }


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    headless = "--show" not in sys.argv   # pass --show to see the browser
    run_contest_scrape(headless=headless)
