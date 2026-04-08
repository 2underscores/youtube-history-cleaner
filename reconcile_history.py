#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import json
from collections import defaultdict
from pathlib import Path

SCRAPED_DIR = Path(__file__).parent / "scraped-data"
HISTORY_FILE = SCRAPED_DIR / "history.json"
CLASSIFIED_FILE = SCRAPED_DIR / "history-classified.json"


def load(path: Path):
    with open(path) as f:
        return json.load(f)


def fmt_bar(value: int, total: int, width: int = 20) -> str:
    filled = round(width * value / total) if total else 0
    return f"[{'█' * filled}{'░' * (width - filled)}]"


def section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def main():
    history = load(HISTORY_FILE)
    classified = load(CLASSIFIED_FILE)

    # ── Reconciliation ──────────────────────────────────────────────
    section("RECONCILIATION")
    h_ids = {item["video_id"] for item in history}
    c_ids = {item["video_id"] for item in classified}

    print(f"  history.json           : {len(history):>6,} items")
    print(f"  history-classified.json: {len(classified):>6,} items")

    if len(history) == len(classified) and h_ids == c_ids:
        print(f"\n  ✓ Files match perfectly — {len(history):,} items, same video IDs")
    else:
        print(f"\n  ✗ MISMATCH DETECTED")
        only_in_history = h_ids - c_ids
        only_in_classified = c_ids - h_ids
        if only_in_history:
            print(f"    In history only ({len(only_in_history)}): {list(only_in_history)[:5]}")
        if only_in_classified:
            print(f"    In classified only ({len(only_in_classified)}): {list(only_in_classified)[:5]}")

    # ── Per-category summary ────────────────────────────────────────
    section("PER CATEGORY")
    cat_total: dict[str, int] = defaultdict(int)
    cat_delete: dict[str, int] = defaultdict(int)
    cat_keep: dict[str, int] = defaultdict(int)

    for item in classified:
        cat = item["category"]
        cat_total[cat] += 1
        if item["delete"]:
            cat_delete[cat] += 1
        else:
            cat_keep[cat] += 1

    total = len(classified)
    categories = sorted(cat_total, key=lambda c: cat_total[c], reverse=True)

    col_w = max(len(c) for c in categories)
    print(f"\n  {'Category':<{col_w}}   Total  Delete    Keep   Bar")
    print(f"  {'─' * col_w}   ─────  ──────  ──────   {'─' * 22}")
    for cat in categories:
        t = cat_total[cat]
        d = cat_delete[cat]
        k = cat_keep[cat]
        bar = fmt_bar(d, t)
        print(f"  {cat:<{col_w}}   {t:>5,}   {d:>5,}   {k:>5,}   {bar} {d/t*100:.0f}% del")

    print(f"\n  {'TOTAL':<{col_w}}   {total:>5,}   {sum(cat_delete.values()):>5,}   {sum(cat_keep.values()):>5,}")

    # ── Per-month summary ───────────────────────────────────────────
    section("PER MONTH")
    month_total: dict[str, int] = defaultdict(int)
    month_delete: dict[str, int] = defaultdict(int)
    month_keep: dict[str, int] = defaultdict(int)
    month_cat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for item in classified:
        # watched_at is ISO 8601; take first 7 chars → "YYYY-MM"
        month = item["watched_at"][:7]
        cat = item["category"]
        month_total[month] += 1
        month_cat[month][cat] += 1
        if item["delete"]:
            month_delete[month] += 1
        else:
            month_keep[month] += 1

    months = sorted(month_total.keys())

    for month in months:
        t = month_total[month]
        d = month_delete[month]
        k = month_keep[month]
        bar = fmt_bar(d, t)
        print(f"\n  ┌─ {month}  ({t:,} videos | {d:,} delete / {k:,} keep)  {bar} {d/t*100:.0f}% del")

        cats_in_month = sorted(month_cat[month], key=lambda c: month_cat[month][c], reverse=True)
        for cat in cats_in_month:
            count = month_cat[month][cat]
            print(f"  │  {cat:<{col_w}}  {count:>4,}  ({count/t*100:.0f}%)")
        print(f"  └{'─' * (col_w + 20)}")

    # ── Global delete/keep ──────────────────────────────────────────
    section("OVERALL SUMMARY")
    total_del = sum(cat_delete.values())
    total_keep = sum(cat_keep.values())
    print(f"\n  Total videos : {total:>6,}")
    print(f"  To delete    : {total_del:>6,}  ({total_del/total*100:.1f}%)")
    print(f"  To keep      : {total_keep:>6,}  ({total_keep/total*100:.1f}%)")
    print(f"\n  {fmt_bar(total_del, total, 40)} {total_del/total*100:.0f}% delete")
    print()


if __name__ == "__main__":
    main()
