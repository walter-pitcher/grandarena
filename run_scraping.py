"""
Grand Arena – Scraping Runner / Simple Status Interface

Provides a small command-line interface to run:
  - contest scraper (fantasy.grandarena.gg/contests)
  - Moki data via API (fetch_mokis_api.py, no browser)

Examples:

  python run_scraping.py                 # contests + mokis (API)
  python run_scraping.py --contests      # contests only
  python run_scraping.py --mokis         # mokis only (API)
  python run_scraping.py --every 30      # contests + mokis every 30 min
  python run_scraping.py --show          # visible browser (contests only)
"""

from __future__ import annotations

import argparse
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from fetch_mokis_api import run_mokis_api
from scrape_contests import run_contest_scrape


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Grand Arena scrapers with a simple status interface.",
    )
    parser.add_argument(
        "--contests",
        action="store_true",
        help="Run only the contests scraper.",
    )
    parser.add_argument(
        "--mokis",
        action="store_true",
        help="Run only Moki fetch (API).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show browser windows (contests scraper only).",
    )
    parser.add_argument(
        "--every",
        type=int,
        default=0,
        metavar="MINUTES",
        help="Run scrapers every N minutes (e.g. 30). Repeat until Ctrl+C. 0 = run once.",
    )

    args = parser.parse_args()

    run_contests = args.contests or not (args.contests or args.mokis)
    run_mokis = args.mokis or not (args.contests or args.mokis)
    headless = not args.show

    print("=" * 72)
    print(f"[{_ts()}] Grand Arena scraping runner starting")
    print(f"  headless    : {headless}")
    print(f"  contests    : {run_contests}")
    print(f"  mokis       : {run_mokis} (API)")
    if args.every:
        print(f"  schedule    : every {args.every} minute(s)")
    print("=" * 72)

    def _run_contests():
        print(f"\n[{_ts()}] ▶ Contests scraper: starting")
        summary = run_contest_scrape(headless=headless)
        if summary.get("ok"):
            print(
                f"[{_ts()}] ✔ Contests scraper: "
                f"{summary.get('count', 0)} contests saved"
            )
            print("  CSV files:")
            for p in summary.get("csv_paths", []):
                print(f"    - {p}")
            print("  JSON files:")
            for p in summary.get("json_paths", []):
                print(f"    - {p}")
        else:
            print(f"[{_ts()}] ✖ Contests scraper: no data scraped or error.")
        return summary

    def _run_mokis():
        print(f"\n[{_ts()}] ▶ Mokis (API): starting")
        summary = run_mokis_api()
        if summary.get("ok"):
            print(
                f"[{_ts()}] ✔ Mokis (API): "
                f"{summary.get('entry_count', 0)} entries"
            )
            print("  CSV files:")
            for p in summary.get("csv_paths", []):
                print(f"    - {p}")
            print("  JSON files:")
            for p in summary.get("json_paths", []):
                print(f"    - {p}")
        else:
            print(f"[{_ts()}] ✖ Mokis (API): no data or error.")
        return summary

    tasks = []
    tasks.append(("contests", _run_contests))
    if run_mokis:
        tasks.append(("mokis", _run_mokis))

    def _run_tasks() -> None:
        if len(tasks) <= 1:
            for _, fn in tasks:
                fn()
        else:
            with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
                future_to_name = {
                    executor.submit(fn): name for name, fn in tasks
                }
                for future in as_completed(future_to_name):
                    name = future_to_name[future]
                    try:
                        future.result()
                    except Exception as exc:
                        print(
                            f"[{_ts()}] ✖ {name.capitalize()} scraper raised an exception: {exc}"
                        )

    run_count = 0
    stop_requested = False

    def _on_signal(_sig: int, _frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        print(f"\n[{_ts()}] Stopping after current run (Ctrl+C again to force)...")

    if args.every:
        signal.signal(signal.SIGINT, _on_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _on_signal)

    while True:
        run_count += 1
        if args.every and run_count > 1:
            print(f"\n[{_ts()}] === Run #{run_count} ===")
        _run_tasks()
        if not args.every or stop_requested:
            break
        interval_sec = args.every * 60
        next_at = datetime.now(timezone.utc).timestamp() + interval_sec
        next_str = datetime.fromtimestamp(next_at, tz=timezone.utc).strftime(
            "%H:%M:%S UTC"
        )
        print(
            f"\n[{_ts()}] Next run in {args.every} minute(s) (at ~{next_str}). Ctrl+C to stop."
        )
        for _ in range(interval_sec):
            if stop_requested:
                break
            time.sleep(1)
        if stop_requested:
            break

    print(f"\n[{_ts()}] All requested scraping tasks finished.")


if __name__ == "__main__":
    main()
