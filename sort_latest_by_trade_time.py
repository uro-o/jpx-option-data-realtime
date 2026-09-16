import csv
from datetime import datetime
from pathlib import Path


LATEST_FILE = Path("data/latest.csv")


def trade_time_key(value):
    """Return a sortable key for MM/DD HH:MM trade time."""
    if not value:
        return (1, datetime.max)

    text = str(value).strip()

    for fmt in ("%m/%d %H:%M", "%m/%d %H:%M:%S"):
        try:
            return (0, datetime.strptime(text, fmt))
        except ValueError:
            pass

    # 不明な形式は約定時刻なしと同じ扱いにして最後へ
    return (1, datetime.max)


def main():
    if not LATEST_FILE.exists():
        print(f"[SORT] {LATEST_FILE} does not exist.")
        return

    with open(
        LATEST_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    if not rows:
        print("[SORT] No records.")
        return

    # 約定時刻が早い順。
    # 約定時刻がないOI変化などは最後へ。
    rows.sort(key=lambda row: trade_time_key(row.get("trade_time", "")))

    with open(
        LATEST_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("[SORT] latest.csv sorted by trade_time ascending.")
    print("[SORT] Early trades are first; records without trade_time are last.")

    shown = 0
    for row in rows:
        trade_time = row.get("trade_time", "")
        if trade_time:
            print(
                f"[SORT CHECK] {trade_time} "
                f"{row.get('contract', '')} "
                f"{row.get('option_type', '')} "
                f"{row.get('strike', '')}"
            )
            shown += 1
            if shown >= 5:
                break


if __name__ == "__main__":
    main()
