import csv
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

DATA_DIR = Path("data")
LATEST_FILE = DATA_DIR / "latest.csv"
DIFFERENCE_FILE = DATA_DIR / "differences.csv"


# 比較対象となる項目
NUMERIC_FIELDS = [
    "open_interest",
    "volume",
    "ask_price",
    "ask_quantity",
    "bid_price",
    "bid_quantity",
    "iv",
    "last_price",
]


# ============================================================
# Utility
# ============================================================

def to_float(value):
    if value is None:
        return 0.0

    value = str(value).strip()

    if value in ("", "-", "--"):
        return 0.0

    try:
        return float(value.replace(",", ""))
    except ValueError:
        return 0.0


# ============================================================
# Load latest.csv
# ============================================================

def load_latest():

    if not LATEST_FILE.exists():
        print("[ERROR] latest.csv not found.")
        return []

    with open(
        LATEST_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(csv.DictReader(f))


# ============================================================
# Load previous snapshot
# ============================================================

def load_previous_snapshot():

    history_dir = DATA_DIR / "history"

    if not history_dir.exists():
        return []

    files = sorted(
        history_dir.glob("*.csv")
    )

    if not files:
        return []

    # 最新のhistoryファイル
    latest_history = files[-1]

    print(
        f"[PREVIOUS] {latest_history}"
    )

    with open(
        latest_history,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(csv.DictReader(f))


# ============================================================
# Create key
# ============================================================

def make_key(row):

    return (
        row.get("contract", ""),
        row.get("option_type", ""),
        row.get("strike", ""),
    )


# ============================================================
# Calculate differences
# ============================================================

def calculate_difference(
    current,
    previous,
):

    previous_map = {
        make_key(row): row
        for row in previous
    }

    results = []

    for row in current:

        key = make_key(row)

        previous_row = previous_map.get(key)

        # ----------------------------------------
        # 初回データ
        # ----------------------------------------

        if previous_row is None:
            continue

        result = {
            "qri_update_time":
                row.get("qri_update_time", ""),

            "collected_at":
                row.get("collected_at", ""),

            "contract":
                row.get("contract", ""),

            "option_type":
                row.get("option_type", ""),

            "strike":
                row.get("strike", ""),
        }

        # ----------------------------------------
        # 差分計算
        # ----------------------------------------

        for field in NUMERIC_FIELDS:

            current_value = to_float(
                row.get(field)
            )

            previous_value = to_float(
                previous_row.get(field)
            )

            difference = (
                current_value
                - previous_value
            )

            result[
                f"{field}_diff"
            ] = difference

        # ----------------------------------------
        # 特に重要な項目
        # ----------------------------------------

        result["volume_current"] = to_float(
            row.get("volume")
        )

        result["open_interest_current"] = to_float(
            row.get("open_interest")
        )

        result["last_price_current"] = to_float(
            row.get("last_price")
        )

        results.append(result)

    return results


# ============================================================
# Save
# ============================================================

def save_difference(
    records
):

    if not records:

        print(
            "[INFO] No comparable records."
        )

        return

    fieldnames = list(
        records[0].keys()
    )

    with open(
        DIFFERENCE_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            records
        )

    print(
        f"[DIFFERENCE] "
        f"{DIFFERENCE_FILE} "
        f"records={len(records)}"
    )


# ============================================================
# Main
# ============================================================

def main():

    print()
    print(
        "========================================"
    )
    print(
        "CALCULATING DIFFERENCE"
    )
    print(
        "========================================"
    )

    # ----------------------------------------
    # Current
    # ----------------------------------------

    current = load_latest()

    print(
        f"[CURRENT] "
        f"records={len(current)}"
    )

    if not current:
        print(
            "[ERROR] "
            "No current data."
        )
        return

    # ----------------------------------------
    # Previous
    # ----------------------------------------

    previous = load_previous_snapshot()

    print(
        f"[PREVIOUS] "
        f"records={len(previous)}"
    )

    if not previous:

        print(
            "[INFO] "
            "No previous snapshot."
        )

        print(
            "[INFO] "
            "Difference will be available "
            "from the next QRI update."
        )

        return

    # ----------------------------------------
    # Calculate
    # ----------------------------------------

    differences = calculate_difference(
        current=current,
        previous=previous,
    )

    print(
        f"[RESULT] "
        f"records={len(differences)}"
    )

    # ----------------------------------------
    # Save
    # ----------------------------------------

    save_difference(
        differences
    )

    print()
    print(
        "========================================"
    )
    print(
        "DIFFERENCE COMPLETE"
    )
    print(
        "========================================"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()
