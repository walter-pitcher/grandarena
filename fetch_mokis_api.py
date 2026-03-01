"""
Grand Arena – Mokis data from API

Fetches mokis data from two webhook URLs. Saves the raw API response as JSON
and the row list as CSV. Then groups by each moki "class" and saves per-class
leaderboards:

  - data/mokis/champion, data/mokis/non-champion  (full JSON + CSV)
  - data/leaderboard/champion/[class]/top_[date].json, top_[date].csv
  - data/leaderboard/non-champion/[class]/top_[date].json, top_[date].csv

Usage:
  python fetch_mokis_api.py
  or call run_mokis_api() from run_scraping.py (e.g. run_scraping.py --mokis).
"""

from __future__ import annotations

import csv
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

# ── config ────────────────────────────────────────────────────────────────────

API_URL_CHAMP     = "https://botto-n8n-botto.eelnl8.easypanel.host/webhook/leaderboardChamps"
API_URL_NO_CHAMP  = "https://botto-n8n-botto.eelnl8.easypanel.host/webhook/leaderboardNoChamps"

MOKIS_CHAMPION_DIR    = Path(__file__).parent / "data" / "mokis" / "champion"
MOKIS_NON_CHAMPION_DIR = Path(__file__).parent / "data" / "mokis" / "non-champion"

LEADERBOARD_CHAMPION_DIR    = Path(__file__).parent / "data" / "leaderboard" / "champion"
LEADERBOARD_NON_CHAMPION_DIR = Path(__file__).parent / "data" / "leaderboard" / "non-champion"

# Timestamp for saved filenames: YYYY-MM-DD_HHMM (clear date with dashes)
TS_FMT = "%Y-%m-%d_%H%M"

# Fallback when a moki has no "class" field
CLASS_UNKNOWN = "unknown"

# Leaderboard files keep only these fields: Rank, Moki name / ID, Score, Class
LEADERBOARD_FIELDS = ("rank", "moki_name", "token_id", "score", "class")


def _fetch_raw(url: str):
    """Fetch URL and return parsed JSON as-is (list or dict). No filtering."""
    # Browser-like headers to avoid 403 from hosts that block script/bot User-Agents
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=60, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _rows_for_csv(raw) -> list[dict]:
    """Get list of row dicts for CSV from raw response. No filtering of rows or fields."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("data", "items", "results", "leaderboard", "entries"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]
        for v in raw.values():
            if isinstance(v, list):
                return v
    return []


def _all_keys(rows: list[dict]) -> list[str]:
    """Column order: union of all keys, with common ones first."""
    common = ("rank", "moki_name", "moki_id", "score", "name", "id", "category", "date_scraped")
    all_keys_set = set()
    for row in rows:
        all_keys_set.update(row.keys())
    ordered = [k for k in common if k in all_keys_set]
    added = set(ordered)
    for row in rows:
        for k in row.keys():
            if k not in added:
                added.add(k)
                ordered.append(k)
    return ordered


def _normalize_row(row: dict) -> dict:
    """Ensure values are CSV-friendly (no nested dicts/lists)."""
    out = {}
    for k, v in row.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = str(v).strip()
    return out


def save_csv(rows: list[dict], path: Path, fieldnames: list[str] | None = None) -> None:
    """Save all rows to CSV with all columns. No filtering."""
    if not rows and not fieldnames:
        return
    fieldnames = fieldnames or _all_keys(rows)
    # Normalize only for CSV safety (nested dict/list -> string); no row/column filtering
    rows_norm = [_normalize_row(r) for r in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_norm)
    print(f"[OK] CSV  -> {path}")


def save_json_raw(data, path: Path) -> None:
    """Save raw API response as JSON. No filtering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON -> {path}")


def _leaderboard_row(row: dict) -> dict:
    """Reduce a moki row to leaderboard fields only: rank, moki_name, token_id, score, class."""
    out = {}
    for k in LEADERBOARD_FIELDS:
        v = row.get(k)
        if v is None:
            out[k] = ""
        elif isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    return out


def _get_class_from_row(row: dict) -> str:
    """Get class value from a moki row; safe for use as directory name."""
    c = row.get("class")
    if c is None or (isinstance(c, str) and not c.strip()):
        return CLASS_UNKNOWN
    return str(c).strip()


def _unique_classes(rows: list[dict]) -> list[str]:
    """Return sorted list of unique class values from rows."""
    classes = {_get_class_from_row(r) for r in rows}
    return sorted(classes)


def _save_leaderboard_by_class(
    rows: list[dict],
    base_dir: Path,
    ts: str,
    label: str,
) -> list[str]:
    """
    Group rows by class and save each group to base_dir/[class]/top_[ts].json and .csv.
    Returns list of saved file paths.
    """
    if not rows:
        return []
    saved: list[str] = []
    for class_name in _unique_classes(rows):
        subset = [r for r in rows if _get_class_from_row(r) == class_name]
        if not subset:
            continue
        slim = [_leaderboard_row(r) for r in subset]
        class_dir = base_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        json_path = class_dir / f"top_{ts}.json"
        csv_path = class_dir / f"top_{ts}.csv"
        save_json_raw(slim, json_path)
        save_csv(slim, csv_path, fieldnames=list(LEADERBOARD_FIELDS))
        saved.extend([str(json_path), str(csv_path)])
        print(f"  {label} / {class_name}: {len(subset)} rows -> top_{ts}.json, top_{ts}.csv")
    return saved


def save_error_stub(dir_path: Path, ts: str, error: Exception, label: str) -> None:
    """On API failure, write a stub JSON so the run is visible and paths are clear."""
    dir_path.mkdir(parents=True, exist_ok=True)
    stub = {
        "error": str(error),
        "error_type": type(error).__name__,
        "source": label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "timestamp_short": ts,
    }
    path_latest = dir_path / "mokis_latest.json"
    path_ts = dir_path / f"mokis_{ts}.json"
    for p in (path_latest, path_ts):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(stub, f, ensure_ascii=False, indent=2)
        print(f"[OK] JSON (error stub) -> {p}")


def run_mokis_api() -> dict:
    """
    Fetch mokis data from both API URLs and save to:
      data/mokis/champion/
      data/mokis/non-champion/
    Returns a summary dict for UIs / schedulers.
    """
    print("Mokis API fetch starting...")
    MOKIS_CHAMPION_DIR.mkdir(parents=True, exist_ok=True)
    MOKIS_NON_CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime(TS_FMT)
    csv_paths: list[str] = []
    json_paths: list[str] = []
    leaderboard_paths: list[str] = []
    total_entries = 0

    # Champion: save raw response as JSON; save all rows as CSV (no filtering)
    try:
        champ_raw = _fetch_raw(API_URL_CHAMP)
        json_ts = MOKIS_CHAMPION_DIR / f"mokis_{ts}.json"
        json_latest = MOKIS_CHAMPION_DIR / "mokis_latest.json"
        save_json_raw(champ_raw, json_ts)
        save_json_raw(champ_raw, json_latest)
        json_paths.extend([str(json_ts), str(json_latest)])
        champ_rows = _rows_for_csv(champ_raw)
        if champ_rows:
            csv_ts = MOKIS_CHAMPION_DIR / f"mokis_{ts}.csv"
            csv_latest = MOKIS_CHAMPION_DIR / "mokis_latest.csv"
            fieldnames = _all_keys(champ_rows)
            save_csv(champ_rows, csv_ts, fieldnames)
            save_csv(champ_rows, csv_latest, fieldnames)
            csv_paths.extend([str(csv_ts), str(csv_latest)])
            total_entries += len(champ_rows)
            print(f"  Champion: {len(champ_rows)} rows (JSON + CSV)")
            # Leaderboard by class: data/leaderboard/champion/[class]/top_[date].json + .csv
            leaderboard_paths.extend(
                _save_leaderboard_by_class(champ_rows, LEADERBOARD_CHAMPION_DIR, ts, "champion")
            )
        else:
            print("  Champion: saved JSON only (no row array for CSV)")
    except Exception as e:
        print(f"  Champion API error: {e}")
        save_error_stub(MOKIS_CHAMPION_DIR, ts, e, "champion")

    # Non-champion: save raw response as JSON; save all rows as CSV (no filtering)
    try:
        no_champ_raw = _fetch_raw(API_URL_NO_CHAMP)
        json_ts = MOKIS_NON_CHAMPION_DIR / f"mokis_{ts}.json"
        json_latest = MOKIS_NON_CHAMPION_DIR / "mokis_latest.json"
        save_json_raw(no_champ_raw, json_ts)
        save_json_raw(no_champ_raw, json_latest)
        json_paths.extend([str(json_ts), str(json_latest)])
        no_champ_rows = _rows_for_csv(no_champ_raw)
        if no_champ_rows:
            csv_ts = MOKIS_NON_CHAMPION_DIR / f"mokis_{ts}.csv"
            csv_latest = MOKIS_NON_CHAMPION_DIR / "mokis_latest.csv"
            fieldnames = _all_keys(no_champ_rows)
            save_csv(no_champ_rows, csv_ts, fieldnames)
            save_csv(no_champ_rows, csv_latest, fieldnames)
            csv_paths.extend([str(csv_ts), str(csv_latest)])
            total_entries += len(no_champ_rows)
            print(f"  Non-champion: {len(no_champ_rows)} rows (JSON + CSV)")
            # Leaderboard by class: data/leaderboard/non-champion/[class]/top_[date].json + .csv
            leaderboard_paths.extend(
                _save_leaderboard_by_class(
                    no_champ_rows, LEADERBOARD_NON_CHAMPION_DIR, ts, "non-champion"
                )
            )
        else:
            print("  Non-champion: saved JSON only (no row array for CSV)")
    except Exception as e:
        print(f"  Non-champion API error: {e}")
        save_error_stub(MOKIS_NON_CHAMPION_DIR, ts, e, "non-champion")

    ok = total_entries > 0 or len(json_paths) > 0
    print("\n[*] Output directories:")
    print(f"    Mokis champion:    {MOKIS_CHAMPION_DIR.resolve()}")
    print(f"    Mokis non-champion: {MOKIS_NON_CHAMPION_DIR.resolve()}")
    print(f"    Leaderboard champion:    {LEADERBOARD_CHAMPION_DIR.resolve()}")
    print(f"    Leaderboard non-champion: {LEADERBOARD_NON_CHAMPION_DIR.resolve()}")
    if ok:
        print(f"[*] Saved JSON (raw) + CSV. Row count: {total_entries}")
        if leaderboard_paths:
            print(f"[*] Leaderboard by class: {len(leaderboard_paths)} files")
    elif json_paths or csv_paths:
        print("[*] Saved JSON only (no row array for CSV).")
    else:
        print("[!] No mokis rows; error stubs written to the dirs above.")

    return {
        "ok": ok,
        "entry_count": total_entries,
        "moki_count": total_entries,
        "csv_paths": csv_paths,
        "json_paths": json_paths,
        "leaderboard_paths": leaderboard_paths,
    }


if __name__ == "__main__":
    summary = run_mokis_api()
    exit(0 if summary.get("ok") else 1)
