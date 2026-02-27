"""
Grand Arena – Leaderboard Scraper
https://train.grandarena.gg/leaderboards

Scrapes both Champion and Non-Champion leaderboards.
For every moki entry on every page, clicks the row to open the
detail modal and extracts:

  rank, moki_name, moki_id, score,
  class, rarity,
  stat_strength, stat_speed, stat_defense, stat_dexterity, stat_fortitude,
  image_url, thumbnail_url,
  category (champion / non-champion),
  page, date_scraped

Pass --pages N  to control how many pages to scrape (default: all).
Pass --show     to run with a visible browser.

Output: leaderboards_YYYYMMDD_HHMM.csv / .json
        leaderboards_latest.csv / .json
"""

import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── config ────────────────────────────────────────────────────────────────────

# Use dedicated subdirectories for leaderboard entries and Moki catalogue data.
OUTPUT_DIR   = Path(__file__).parent / "data" / "leaderboards"
MOKIS_OUTPUT_DIR = Path(__file__).parent / "data" / "mokis"
BASE_URL     = "https://train.grandarena.gg/leaderboards"
CATEGORIES   = [
    ("champion",     "Champion"),
    ("non-champion", "Non-Champion"),
]

ROW_SEL      = "button.flex.p-2.items-center.gap-2"

# Map hex background colour → rarity name
RARITY_MAP = {
    "FFD753": "Legendary",
    "F97316": "Epic",
    "9F5CF0": "Rare",
    "60A5FA": "Uncommon",
    "4ADE80": "Common",
    "232842": "Basic",
}

# ── helpers ───────────────────────────────────────────────────────────────────

def safe(text: str) -> str:
    return (text or "").strip()


def parse_row(row_el, rank: int) -> dict:
    """Extract the data directly visible in the leaderboard row button."""
    html = row_el.inner_html()

    # thumbnail image URL (smallest srcset img)
    m = re.search(r'<img alt="([^"]+)"[^>]*src="([^"]+)"', html)
    moki_name_from_img = m.group(1).strip() if m else ""
    thumbnail_url = ""
    if m:
        raw = m.group(2)
        # decode Next.js image URL to get the real source
        inner = re.search(r'url=([^&]+)', raw)
        if inner:
            from urllib.parse import unquote
            thumbnail_url = unquote(inner.group(1))
        else:
            thumbnail_url = raw

    # name (bold span inside flex col)
    m2 = re.search(r'font-bold[^>]*>([^<]+)</span>', html)
    moki_name = m2.group(1).strip() if m2 else moki_name_from_img

    # moki ID  (#XXXX span)
    m3 = re.search(r'#(\d+)', html)
    moki_id = m3.group(1).lstrip("0") or "0" if m3 else ""

    # score (last bold number)
    scores = re.findall(r'whitespace-nowrap[^>]*>(\d[\d,]+)<', html)
    score = scores[-1].replace(",", "") if scores else ""

    return {
        "rank":          rank,
        "moki_name":     moki_name,
        "moki_id":       moki_id,
        "score":         score,
        "thumbnail_url": thumbnail_url,
        # filled after clicking modal:
        "class":         "",
        "rarity":        "",
        "stat_strength": "",
        "stat_speed":    "",
        "stat_defense":  "",
        "stat_dexterity":"",
        "stat_fortitude":"",
        "image_url":     "",
    }


def parse_modal(page) -> dict:
    """Read the detail modal that opens after clicking a leaderboard row."""
    result = {
        "class": "", "rarity": "",
        "stat_strength": "", "stat_speed": "", "stat_defense": "",
        "stat_dexterity": "", "stat_fortitude": "",
        "image_url": "",
    }

    try:
        modal = page.wait_for_selector('[tabindex="-1"]', timeout=6000)
    except PWTimeout:
        return result

    html = modal.inner_html()

    # rarity – from header background colour  bg-[#XXXXXX]
    m = re.search(r'border-neutral-900 bg-\[#([A-Fa-f0-9]{6})\]', html)
    if m:
        hex_color = m.group(1).upper()
        result["rarity"] = RARITY_MAP.get(hex_color, f"#{hex_color}")

    # full-size image URL  (background-image: url(...))
    m2 = re.search(r'background-image: url\(["\']?([^"\')\s]+)["\']?\)', html)
    if m2:
        result["image_url"] = m2.group(1)

    # class  (pill label inside the header flex block)
    m3 = re.search(r'rounded-full border-neutral-950 border-2[^>]*>.*?<span[^>]*>([^<]+)</span>', html, re.S)
    if m3:
        result["class"] = m3.group(1).strip()

    # stats – each stat block has: label span  +  value span
    stat_patterns = {
        "stat_strength":  r"Strength",
        "stat_speed":     r"Speed",
        "stat_defense":   r"Defense",
        "stat_dexterity": r"Dexterity",
        "stat_fortitude": r"Fortitude",
    }
    for key, label in stat_patterns.items():
        # value is in the bold span right after the label
        m4 = re.search(
            label + r'</span>.*?<span[^>]*font-bold[^>]*>([0-9.,]+)</span>',
            html, re.S
        )
        if m4:
            result[key] = m4.group(1)

    return result


def close_modal(page):
    """Click the X close button of the moki detail modal."""
    try:
        modal = page.query_selector('[tabindex="-1"]')
        if not modal:
            return
        btns = modal.query_selector_all("button")
        if btns:
            # Last button is always the X close button
            btns[-1].click()
            time.sleep(0.6)
    except Exception:
        pass


def get_total_pages(page) -> int:
    """Try to determine total pages from pagination buttons."""
    try:
        # Click 'Last' to jump to last page and read the current page indicator
        page.click("button:has-text('Last')", timeout=4000)
        time.sleep(1.5)
        btns = page.query_selector_all("button")
        nums = []
        for btn in btns:
            t = btn.inner_text().strip()
            if t.isdigit():
                nums.append(int(t))
        total = max(nums) if nums else 1
        # Navigate back to first page
        page.click("button:has-text('Back')", timeout=4000)
        time.sleep(1.5)
        # Keep clicking Back until we're on page 1
        for _ in range(20):
            btns2 = page.query_selector_all("button")
            page_btns = [b for b in btns2 if b.inner_text().strip().isdigit()]
            if page_btns and page_btns[0].inner_text().strip() == "1":
                # Check if "1" is currently selected / active
                # Use keyboard shortcut or just navigate to first page directly
                break
            try:
                page.click("button:has-text('Back')", timeout=2000)
                time.sleep(0.8)
            except Exception:
                break
        return total
    except Exception:
        return 99  # assume large number; caller will stop when "Next" is gone


def navigate_to_page_1(page):
    """Navigate back to the very first page."""
    for _ in range(30):
        try:
            back = page.query_selector("button:has-text('Back')")
            if not back:
                break
            # If Back is disabled (greyed out), we're on page 1
            disabled = back.get_attribute("disabled")
            aria_disabled = back.get_attribute("aria-disabled")
            if disabled is not None or aria_disabled == "true":
                break
            # Check page numbers – stop if 1 is the first visible page button
            btns = page.query_selector_all("button")
            page_nums = [b for b in btns if b.inner_text().strip().isdigit()]
            if page_nums and page_nums[0].inner_text().strip() == "1":
                break
            back.click()
            time.sleep(1)
        except Exception:
            break


# ── main scraping logic ───────────────────────────────────────────────────────

def scrape_leaderboards(
    max_pages: int = 0,
    headless: bool = True,
    only_category: str = "",        # "" = both; "champion" or "non-champion"
    max_rank_per_category: int = 0, # 0 = no limit; otherwise stop after N ranks
) -> list[dict]:
    """
    max_pages=0  means scrape ALL pages.
    only_category filters to one category (case-insensitive param value).
    """
    all_entries: list[dict] = []
    scrape_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=150)
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        active_categories = [
            (p, l) for p, l in CATEGORIES
            if not only_category or p.lower() == only_category.lower()
        ]

        for cat_param, cat_label in active_categories:
            url = f"{BASE_URL}?champion={cat_param}"
            print(f"\n{'='*60}")
            print(f"[+] Scraping: {cat_label}  ({url})")
            print(f"{'='*60}")

            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            current_page = 1
            category_rank = 0

            while True:
                if max_pages > 0 and current_page > max_pages:
                    print(f"    Reached max_pages={max_pages}, stopping.")
                    break

                if max_rank_per_category > 0 and category_rank >= max_rank_per_category:
                    print(f"    Reached max_rank_per_category={max_rank_per_category}, stopping.")
                    break

                print(f"\n  [Page {current_page}]")
                rows = page.query_selector_all(ROW_SEL)
                if not rows:
                    print("    No rows found – end of leaderboard.")
                    break

                print(f"    {len(rows)} entries found")

                for i, row in enumerate(rows):
                    if max_rank_per_category > 0 and category_rank >= max_rank_per_category:
                        print(f"    Rank limit {max_rank_per_category} reached for {cat_label}, skipping remaining rows on this page.")
                        break

                    category_rank += 1
                    rank = category_rank

                    # --- parse row-level data ---
                    entry = parse_row(row, rank)
                    entry["category"]     = cat_label
                    entry["page"]         = current_page
                    entry["date_scraped"] = scrape_ts

                    name_short = entry["moki_name"][:25] if entry["moki_name"] else "?"
                    print(f"    [{rank:4}] {name_short:<25} score={entry['score']}")

                    # --- click row to open modal ---
                    try:
                        # Re-query rows to avoid stale references
                        fresh_rows = page.query_selector_all(ROW_SEL)
                        if i < len(fresh_rows):
                            fresh_rows[i].click()
                            time.sleep(1.2)
                            detail = parse_modal(page)
                            entry.update(detail)
                            close_modal(page)
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"      [!] Modal error: {e}")
                        close_modal(page)

                    all_entries.append(entry)

                # --- pagination: click Next ---
                try:
                    # Ensure no modal is open before clicking Next
                    close_modal(page)
                    time.sleep(0.3)

                    next_btn = page.query_selector("button:has-text('Next')")
                    if not next_btn:
                        print("    No 'Next' button – last page reached.")
                        break

                    # Check if Next is disabled
                    if (next_btn.get_attribute("disabled") is not None or
                            next_btn.get_attribute("aria-disabled") == "true"):
                        print("    'Next' is disabled – last page reached.")
                        break

                    next_btn.click(timeout=8000)
                    time.sleep(2)
                    current_page += 1

                except PWTimeout:
                    print("    'Next' click timed out – stopping.")
                    break
                except Exception as e:
                    print(f"    Pagination error: {e} – stopping.")
                    break

        browser.close()

    return all_entries


# ── output ────────────────────────────────────────────────────────────────────

FIELDNAMES = [
    "rank",
    "moki_name",
    "moki_id",
    "score",
    "class",
    "rarity",
    "stat_strength",
    "stat_speed",
    "stat_defense",
    "stat_dexterity",
    "stat_fortitude",
    "image_url",
    "thumbnail_url",
    "category",
    "page",
    "date_scraped",
]


def save_csv(entries: list[dict], path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(entries)
    print(f"[OK] CSV  -> {path}")


def save_json(entries: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON -> {path}")


def build_unique_mokis(entries: list[dict]) -> list[dict]:
    """
    Aggregate a unique list of Mokis (Champions and Non-Champions) from
    leaderboard entries. This is best-effort and depends on which Mokis
    currently appear in the leaderboards.

    We key by moki_id where available, otherwise by (name, rarity, class).
    For duplicates we keep the highest-score entry.
    """
    best_by_key: dict[tuple, dict] = {}

    for e in entries:
        moki_id = safe(e.get("moki_id", ""))
        if moki_id:
            key = ("id", moki_id)
        else:
            key = (
                "fallback",
                safe(e.get("moki_name", "")),
                safe(e.get("rarity", "")),
                safe(e.get("class", "")),
            )

        current_best = best_by_key.get(key)

        raw_score = safe(e.get("score", "0")).replace(",", "")
        try:
            score_val = int(raw_score)
        except ValueError:
            score_val = 0

        if current_best is None:
            best_by_key[key] = {**e, "_score_val": score_val}
        else:
            prev_score_val = current_best.get("_score_val", 0)
            if score_val > prev_score_val:
                best_by_key[key] = {**e, "_score_val": score_val}

    unique: list[dict] = []
    for _, data in best_by_key.items():
        data.pop("_score_val", None)
        unique.append(data)

    unique.sort(key=lambda d: (safe(d.get("rarity", "")), safe(d.get("moki_name", ""))))
    return unique


def run_leaderboard_scrape(
    headless: bool = True,
    max_pages: int = 0,
    only_category: str = "",
    max_rank_per_category: int = 0,
) -> dict:
    """
    Run the leaderboard scraper and write:
    - combined leaderboard entries (timestamped + *_latest, legacy + clearer names)
    - per-category files
    - unique Moki catalogue derived from all entries

    Returns a summary dict for UIs / schedulers.
    """
    print(f"Leaderboard scraper starting...")
    print(f"  category          : {only_category or 'both'}")
    print(f"  max_pages         : {'all' if max_pages == 0 else max_pages} per category")
    print(f"  max_rank/category : {'all' if max_rank_per_category == 0 else max_rank_per_category}")
    print(f"  headless          : {headless}")

    # Ensure data directories exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MOKIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    entries = scrape_leaderboards(
        max_pages=max_pages,
        headless=headless,
        only_category=only_category,
        max_rank_per_category=max_rank_per_category,
    )

    if not entries:
        print("\n[!] No entries scraped.")
        return {
            "ok": False,
            "entry_count": 0,
            "moki_count": 0,
            "csv_paths": [],
            "json_paths": [],
        }

    print(f"\n[*] Total entries scraped: {len(entries)}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    # Combined leaderboard files – new clearer names plus legacy ones
    csv_ts_new  = OUTPUT_DIR / f"leaderboards_all_entries_{ts}.csv"
    json_ts_new = OUTPUT_DIR / f"leaderboards_all_entries_{ts}.json"
    csv_latest_new  = OUTPUT_DIR / "leaderboards_all_entries_latest.csv"
    json_latest_new = OUTPUT_DIR / "leaderboards_all_entries_latest.json"

    csv_ts_legacy  = OUTPUT_DIR / f"leaderboards_{ts}.csv"
    json_ts_legacy = OUTPUT_DIR / f"leaderboards_{ts}.json"
    csv_latest_legacy  = OUTPUT_DIR / "leaderboards_latest.csv"
    json_latest_legacy = OUTPUT_DIR / "leaderboards_latest.json"

    for path in (csv_ts_new, csv_ts_legacy, csv_latest_new, csv_latest_legacy):
        save_csv(entries, path)
    for path in (json_ts_new, json_ts_legacy, json_latest_new, json_latest_legacy):
        save_json(entries, path)

    # Per-category files (names were already fairly clear; keep as-is)
    for cat_label, slug in [("Champion", "champion"), ("Non-Champion", "non_champion")]:
        subset = [e for e in entries if e["category"] == cat_label]
        if subset:
            save_csv(subset,  OUTPUT_DIR / f"leaderboards_{slug}_{ts}.csv")
            save_json(subset, OUTPUT_DIR / f"leaderboards_{slug}_{ts}.json")
            save_csv(subset,  OUTPUT_DIR / f"leaderboards_{slug}_latest.csv")
            save_json(subset, OUTPUT_DIR / f"leaderboards_{slug}_latest.json")
            print(f"    ({cat_label}: {len(subset)} entries)")

    # Build unique Moki catalogue from all entries
    mokis_unique = build_unique_mokis(entries)
    print(f"\n[*] Unique Mokis derived from leaderboards: {len(mokis_unique)}")

    mokis_csv_ts  = MOKIS_OUTPUT_DIR / f"mokis_all_from_leaderboards_{ts}.csv"
    mokis_json_ts = MOKIS_OUTPUT_DIR / f"mokis_all_from_leaderboards_{ts}.json"
    mokis_csv_latest  = MOKIS_OUTPUT_DIR / "mokis_all_from_leaderboards_latest.csv"
    mokis_json_latest = MOKIS_OUTPUT_DIR / "mokis_all_from_leaderboards_latest.json"

    save_csv(mokis_unique, mokis_csv_ts)
    save_json(mokis_unique, mokis_json_ts)
    save_csv(mokis_unique, mokis_csv_latest)
    save_json(mokis_unique, mokis_json_latest)

    # Print preview
    print("\n=== PREVIEW (first 5 entries) ===")
    for e in entries[:5]:
        line = (
            f"  [{e['category']:13}] "
            f"rank={e['rank']:4}  "
            f"{str(e['moki_name'])[:22]:<22}  "
            f"#{e['moki_id']:<5}  "
            f"score={e['score']:<6}  "
            f"class={e['class']:<10}  "
            f"rarity={e['rarity']}"
        )
        print(line)

    return {
        "ok": True,
        "entry_count": len(entries),
        "moki_count": len(mokis_unique),
        "csv_paths": [
            str(csv_ts_new),
            str(csv_ts_legacy),
            str(csv_latest_new),
            str(csv_latest_legacy),
            str(mokis_csv_ts),
            str(mokis_csv_latest),
        ],
        "json_paths": [
            str(json_ts_new),
            str(json_ts_legacy),
            str(json_latest_new),
            str(json_latest_legacy),
            str(mokis_json_ts),
            str(mokis_json_latest),
        ],
    }


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    headless       = "--show" not in sys.argv
    max_pages      = 0   # 0 = all pages
    only_category  = ""  # "" = both
    max_rank_per_category = 0  # 0 = no rank limit

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--pages" and i + 1 < len(args):
            try:
                max_pages = int(args[i + 1])
            except ValueError:
                pass
        if arg == "--category" and i + 1 < len(args):
            only_category = args[i + 1].lower()
        if arg in ("--top", "--max-rank") and i + 1 < len(args):
            try:
                max_rank_per_category = int(args[i + 1])
            except ValueError:
                pass

    summary = run_leaderboard_scrape(
        headless=headless,
        max_pages=max_pages,
        only_category=only_category,
        max_rank_per_category=max_rank_per_category,
    )

    if not summary.get("ok"):
        sys.exit(1)
