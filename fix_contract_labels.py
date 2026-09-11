import csv
import re
from pathlib import Path


DATA_DIR = Path("data")
LATEST_FILE = DATA_DIR / "latest.csv"
PREVIOUS_FILE = DATA_DIR / "previous.csv"
DIFFERENCES_FILE = DATA_DIR / "differences.csv"
HISTORY_DIR = DATA_DIR / "history"


def contract_from_last_trading_day(value):
    """Return YYYY-MM from QRI's last trading day."""
    if not value:
        return ""

    match = re.search(r"(\d{4})/(\d{1,2})/\d{1,2}", str(value))
    if not match:
        return ""

    return f"{match.group(1)}-{int(match.group(2)):02d}"


def fix_file(path):
    if not path.exists():
        return 0, 0

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    if not rows or "contract" not in fieldnames:
        return 0, 0

    changed = 0
    unresolved = 0

    for row in rows:
        detected = contract_from_last_trading_day(
            row.get("last_trading_day", "")
        )

        if detected:
            if row.get("contract", "") != detected:
                print(
                    f"[FIX] {path}: "
                    f"{row.get('contract', '')} -> {detected} "
                    f"(last trading day={row.get('last_trading_day', '')})"
                )
                row["contract"] = detected
                changed += 1
        else:
            unresolved += 1

    if changed:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return changed, unresolved


def main():
    print("========================================")
    print("FIX QRI CONTRACT LABELS")
    print("========================================")
    print("QRIの『取引最終日』から実際の限月を判定します。")
    print()

    total_changed = 0

    for path in (
        LATEST_FILE,
        PREVIOUS_FILE,
        DIFFERENCES_FILE,
    ):
        changed, unresolved = fix_file(path)
        total_changed += changed
        print(
            f"[RESULT] {path}: changed={changed}, "
            f"unresolved={unresolved}"
        )

    if HISTORY_DIR.exists():
        for path in sorted(HISTORY_DIR.glob("*.csv")):
            changed, unresolved = fix_file(path)
            total_changed += changed
            print(
                f"[RESULT] {path}: changed={changed}, "
                f"unresolved={unresolved}"
            )

    print()
    print("========================================")
    print(f"TOTAL CHANGED: {total_changed}")
    print("========================================")


if __name__ == "__main__":
    main()
