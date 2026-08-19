import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta


# ============================================================
# Configuration
# ============================================================

DATA_DIR = Path("data")
HISTORY_DIR = DATA_DIR / "history"

DIFFERENCE_FILE = DATA_DIR / "differences.csv"

JST = timezone(
    timedelta(hours=9)
)


# ============================================================
# Output columns
# ============================================================

FIELDNAMES = [
    "qri_update_time",
    "previous_qri_update_time",
    "collected_at",

    "contract",
    "option_type",
    "strike",

    "previous_volume",
    "current_volume",
    "volume_change",

    "previous_open_interest",
    "current_open_interest",
    "open_interest_change",

    "previous_last_price",
    "current_last_price",
    "last_price_change",

    "previous_iv",
    "current_iv",
    "iv_change",

    "trade_time",
]


# ============================================================
# Number conversion
# ============================================================

def to_number(value):

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    try:

        number = float(
            value.replace(",", "")
        )

        if number.is_integer():
            return int(number)

        return number

    except ValueError:

        return None


# ============================================================
# Get today's history file
# ============================================================

def get_today_history_file():

    today = datetime.now(
        JST
    ).strftime(
        "%Y-%m-%d"
    )

    return (
        HISTORY_DIR /
        f"{today}.csv"
    )


# ============================================================
# Load history
# ============================================================

def load_history(
    history_file
):

    if not history_file.exists():

        print(
            f"[ERROR] "
            f"History file not found: "
            f"{history_file}"
        )

        return []

    with open(
        history_file,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        return list(reader)


# ============================================================
# Sort QRI update times
# ============================================================

def get_update_times(
    rows
):

    times = set()

    for row in rows:

        value = row.get(
            "qri_update_time",
            ""
        )

        if value:

            times.add(value)

    return sorted(times)


# ============================================================
# Get numeric value
# ============================================================

def numeric(
    row,
    key
):

    value = row.get(
        key,
        ""
    )

    return to_number(value)


# ============================================================
# Calculate difference
# ============================================================

def calculate_difference(
    rows
):

    if not rows:

        return []

    update_times = (
        get_update_times(
            rows
        )
    )

    # --------------------------------------------------------
    # Need at least two QRI snapshots
    # --------------------------------------------------------

    if len(update_times) < 2:

        print()
        print(
            "[INFO] "
            "Not enough snapshots."
        )

        print(
            f"Available snapshots: "
            f"{len(update_times)}"
        )

        return []

    previous_time = (
        update_times[-2]
    )

    current_time = (
        update_times[-1]
    )

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

    print(
        f"Previous QRI: "
        f"{previous_time}"
    )

    print(
        f"Current QRI : "
        f"{current_time}"
    )

    # ========================================================
    # Create lookup tables
    # ========================================================

    previous_rows = {}

    current_rows = {}

    for row in rows:

        key = (
            row.get(
                "contract",
                ""
            ),
            row.get(
                "option_type",
                ""
            ),
            row.get(
                "strike",
                ""
            ),
        )

        update_time = row.get(
            "qri_update_time",
            ""
        )

        if update_time == previous_time:

            previous_rows[key] = row

        elif update_time == current_time:

            current_rows[key] = row

    # ========================================================
    # Calculate
    # ========================================================

    differences = []

    for key, current in (
        current_rows.items()
    ):

        previous = (
            previous_rows.get(key)
        )

        # ----------------------------------------------------
        # Contract not found in previous snapshot
        # ----------------------------------------------------

        if previous is None:

            continue

        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

        previous_volume = numeric(
            previous,
            "volume"
        )

        current_volume = numeric(
            current,
            "volume"
        )

        if (
            previous_volume is not None
            and
            current_volume is not None
        ):

            volume_change = (
                current_volume
                -
                previous_volume
            )

        else:

            volume_change = None

        # ----------------------------------------------------
        # Open Interest
        # ----------------------------------------------------

        previous_oi = numeric(
            previous,
            "open_interest"
        )

        current_oi = numeric(
            current,
            "open_interest"
        )

        if (
            previous_oi is not None
            and
            current_oi is not None
        ):

            oi_change = (
                current_oi
                -
                previous_oi
            )

        else:

            oi_change = None

        # ----------------------------------------------------
        # Last price
        # ----------------------------------------------------

        previous_last = numeric(
            previous,
            "last_price"
        )

        current_last = numeric(
            current,
            "last_price"
        )

        if (
            previous_last is not None
            and
            current_last is not None
        ):

            last_change = (
                current_last
                -
                previous_last
            )

        else:

            last_change = None

        # ----------------------------------------------------
        # IV
        # ----------------------------------------------------

        previous_iv = numeric(
            previous,
            "iv"
        )

        current_iv = numeric(
            current,
            "iv"
        )

        if (
            previous_iv is not None
            and
            current_iv is not None
        ):

            iv_change = (
                current_iv
                -
                previous_iv
            )

        else:

            iv_change = None

        # ----------------------------------------------------
        # Record
        # ----------------------------------------------------

        difference = {

            "qri_update_time":
                current_time,

            "previous_qri_update_time":
                previous_time,

            "collected_at":
                current.get(
                    "collected_at",
                    ""
                ),

            "contract":
                current.get(
                    "contract",
                    ""
                ),

            "option_type":
                current.get(
                    "option_type",
                    ""
                ),

            "strike":
                current.get(
                    "strike",
                    ""
                ),

            "previous_volume":
                previous_volume,

            "current_volume":
                current_volume,

            "volume_change":
                volume_change,

            "previous_open_interest":
                previous_oi,

            "current_open_interest":
                current_oi,

            "open_interest_change":
                oi_change,

            "previous_last_price":
                previous_last,

            "current_last_price":
                current_last,

            "last_price_change":
                last_change,

            "previous_iv":
                previous_iv,

            "current_iv":
                current_iv,

            "iv_change":
                iv_change,

            "trade_time":
                current.get(
                    "trade_time",
                    ""
                ),
        }

        differences.append(
            difference
        )

    return differences


# ============================================================
# Save differences
# ============================================================

def save_differences(
    differences
):

    if not differences:

        print(
            "[DIFFERENCE] "
            "No differences to save."
        )

        return

    # --------------------------------------------------------
    # Existing records
    # --------------------------------------------------------

    existing_keys = set()

    if DIFFERENCE_FILE.exists():

        try:

            with open(
                DIFFERENCE_FILE,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as f:

                reader = csv.DictReader(f)

                for row in reader:

                    key = (
                        row.get(
                            "qri_update_time",
                            ""
                        ),
                        row.get(
                            "contract",
                            ""
                        ),
                        row.get(
                            "option_type",
                            ""
                        ),
                        row.get(
                            "strike",
                            ""
                        ),
                    )

                    existing_keys.add(
                        key
                    )

        except Exception as e:

            print(
                f"[WARNING] "
                f"Could not read "
                f"differences.csv: "
                f"{e}"
            )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    new_differences = []

    for row in differences:

        key = (
            row[
                "qri_update_time"
            ],
            row[
                "contract"
            ],
            row[
                "option_type"
            ],
            str(
                row[
                    "strike"
                ]
            ),
        )

        if key not in existing_keys:

            new_differences.append(
                row
            )

    if not new_differences:

        print(
            "[DIFFERENCE] "
            "No new differences."
        )

        return

    # --------------------------------------------------------
    # Append
    # --------------------------------------------------------

    file_exists = (
        DIFFERENCE_FILE.exists()
    )

    with open(
        DIFFERENCE_FILE,
        "a",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES
        )

        if not file_exists:

            writer.writeheader()

        writer.writerows(
            new_differences
        )

    print(
        f"[DIFFERENCE] "
        f"{DIFFERENCE_FILE} "
        f"+{len(new_differences)} records"
    )


# ============================================================
# Show large volume changes
# ============================================================

def show_large_changes(
    differences
):

    if not differences:

        return

    # ========================================================
    # Threshold
    # ========================================================

    threshold = 50

    large_changes = []

    for row in differences:

        change = to_number(
            row.get(
                "volume_change"
            )
        )

        if (
            change is not None
            and
            change >= threshold
        ):

            large_changes.append(
                row
            )

    if not large_changes:

        print()
        print(
            "[LARGE TRADE] "
            "No volume increase >= "
            f"{threshold}"
        )

        return

    # --------------------------------------------------------
    # Sort by volume change
    # --------------------------------------------------------

    large_changes.sort(
        key=lambda x:
            to_number(
                x.get(
                    "volume_change"
                )
            )
            or 0,
        reverse=True,
    )

    print()
    print(
        "========================================"
    )

    print(
        f"LARGE OPTION TRADES "
        f"(Volume +{threshold} or more)"
    )

    print(
        "========================================"
    )

    for row in large_changes:

        print(
            f"{row['contract']} "
            f"{row['option_type']} "
            f"{row['strike']} | "
            f"Volume "
            f"{row['previous_volume']} "
            f"→ "
            f"{row['current_volume']} "
            f"(+{row['volume_change']}) | "
            f"OI "
            f"{row['previous_open_interest']} "
            f"→ "
            f"{row['current_open_interest']} "
            f"({row['open_interest_change']:+})"
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
        "JPX OPTION DIFFERENCE"
    )

    print(
        "========================================"
    )

    history_file = (
        get_today_history_file()
    )

    print(
        f"History: "
        f"{history_file}"
    )

    # ========================================================
    # Load
    # ========================================================

    rows = load_history(
        history_file
    )

    print(
        f"History records: "
        f"{len(rows)}"
    )

    # ========================================================
    # Calculate
    # ========================================================

    differences = (
        calculate_difference(
            rows
        )
    )

    # ========================================================
    # Save
    # ========================================================

    save_differences(
        differences
    )

    # ========================================================
    # Large trade display
    # ========================================================

    show_large_changes(
        differences
    )

    print()
    print(
        "========================================"
    )

    print(
        "DONE"
    )

    print(
        "========================================"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
