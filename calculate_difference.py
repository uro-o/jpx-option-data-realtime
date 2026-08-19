import csv
import os
import time
from pathlib import Path

import requests


# ============================================================
# Configuration
# ============================================================

DATA_DIR = Path("data")

LATEST_FILE = DATA_DIR / "latest.csv"
PREVIOUS_FILE = DATA_DIR / "previous.csv"
DIFFERENCES_FILE = DATA_DIR / "differences.csv"


# ============================================================
# Discord
# ============================================================

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    ""
)


# ============================================================
# Alert thresholds
# ============================================================

# 通常の個別アラート
VOLUME_THRESHOLD = 100
OI_INCREASE_THRESHOLD = 100
OI_DECREASE_THRESHOLD = 100
PRICE_CHANGE_THRESHOLD = 100


# ============================================================
# Flow thresholds
# ============================================================

# Flow一覧に掲載する最低Volume増加
FLOW_VOLUME_MIN = 5

# Flow一覧に掲載する最低OI変化
FLOW_OI_MIN = 5

# Flowランキング最大件数
FLOW_MAX_ITEMS = 10


# ============================================================
# Discord message limits
# ============================================================

DISCORD_MAX_LENGTH = 1900


# ============================================================
# CSV fields
# ============================================================

DIFFERENCE_FIELDS = [
    "qri_update_time",
    "collected_at",
    "contract",
    "option_type",
    "strike",

    "previous_open_interest",
    "current_open_interest",
    "open_interest_diff",

    "previous_volume",
    "current_volume",
    "volume_diff",

    "previous_last_price",
    "current_last_price",
    "last_price_diff",

    "previous_ask_quantity",
    "current_ask_quantity",
    "ask_quantity_diff",

    "previous_bid_quantity",
    "current_bid_quantity",
    "bid_quantity_diff",

    "alert_type",
]


# ============================================================
# Number helper
# ============================================================

def number(value):

    if value is None:
        return 0.0

    if value == "":
        return 0.0

    try:

        return float(
            str(value)
            .replace(",", "")
        )

    except Exception:

        return 0.0


# ============================================================
# Format number
# ============================================================

def fmt(value):

    value = number(value)

    if value == 0:
        return "0"

    if value.is_integer():
        return f"{int(value):,}"

    return f"{value:,.2f}"


# ============================================================
# Format signed number
# ============================================================

def fmt_signed(value):

    value = number(value)

    if value > 0:

        if value.is_integer():
            return f"+{int(value):,}"

        return f"+{value:,.2f}"

    if value < 0:

        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"

    return "0"


# ============================================================
# Load CSV
# ============================================================

def load_csv(path):

    if not path.exists():

        print(
            f"[WARNING] "
            f"{path} does not exist."
        )

        return []

    try:

        with open(
            path,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:

            rows = list(
                csv.DictReader(f)
            )

        print(
            f"[LOAD] "
            f"{path} "
            f"records={len(rows)}"
        )

        return rows

    except Exception as e:

        print(
            f"[ERROR] "
            f"Could not read {path}: {e}"
        )

        return []


# ============================================================
# Calculate differences
# ============================================================

def calculate_differences(
    current_records,
    previous_records,
):

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
        f"[CURRENT] records={len(current_records)}"
    )

    print(
        f"[PREVIOUS] records={len(previous_records)}"
    )


    # --------------------------------------------------------
    # Previous map
    # --------------------------------------------------------

    previous_map = {}

    for row in previous_records:

        key = (
            row.get("contract", ""),
            row.get("option_type", ""),
            row.get("strike", ""),
        )

        previous_map[key] = row


    # --------------------------------------------------------
    # Difference
    # --------------------------------------------------------

    differences = []

    for current in current_records:

        key = (
            current.get("contract", ""),
            current.get("option_type", ""),
            current.get("strike", ""),
        )

        previous = previous_map.get(key)

        if previous is None:

            continue


        # ====================================================
        # OI
        # ====================================================

        previous_oi = number(
            previous.get(
                "open_interest"
            )
        )

        current_oi = number(
            current.get(
                "open_interest"
            )
        )

        oi_diff = (
            current_oi -
            previous_oi
        )


        # ====================================================
        # Volume
        # ====================================================

        previous_volume = number(
            previous.get(
                "volume"
            )
        )

        current_volume = number(
            current.get(
                "volume"
            )
        )

        volume_diff = (
            current_volume -
            previous_volume
        )


        # ====================================================
        # Last price
        # ====================================================

        previous_price = number(
            previous.get(
                "last_price"
            )
        )

        current_price = number(
            current.get(
                "last_price"
            )
        )

        price_diff = (
            current_price -
            previous_price
        )


        # ====================================================
        # Ask quantity
        # ====================================================

        previous_ask_qty = number(
            previous.get(
                "ask_quantity"
            )
        )

        current_ask_qty = number(
            current.get(
                "ask_quantity"
            )
        )

        ask_qty_diff = (
            current_ask_qty -
            previous_ask_qty
        )


        # ====================================================
        # Bid quantity
        # ====================================================

        previous_bid_qty = number(
            previous.get(
                "bid_quantity"
            )
        )

        current_bid_qty = number(
            current.get(
                "bid_quantity"
            )
        )

        bid_qty_diff = (
            current_bid_qty -
            previous_bid_qty
        )


        # ====================================================
        # Alert type
        # ====================================================

        alerts = []


        if (
            volume_diff
            >= VOLUME_THRESHOLD
        ):

            alerts.append(
                "VOLUME"
            )


        if (
            oi_diff
            >= OI_INCREASE_THRESHOLD
        ):

            alerts.append(
                "OI_INCREASE"
            )


        if (
            oi_diff
            <= -OI_DECREASE_THRESHOLD
        ):

            alerts.append(
                "OI_DECREASE"
            )


        if (
            abs(price_diff)
            >= PRICE_CHANGE_THRESHOLD
        ):

            alerts.append(
                "PRICE"
            )


        alert_type = ",".join(
            alerts
        )


        # ====================================================
        # Save
        # ====================================================

        differences.append({

            "qri_update_time":
                current.get(
                    "qri_update_time",
                    ""
                ),

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

            "previous_open_interest":
                previous_oi,

            "current_open_interest":
                current_oi,

            "open_interest_diff":
                oi_diff,

            "previous_volume":
                previous_volume,

            "current_volume":
                current_volume,

            "volume_diff":
                volume_diff,

            "previous_last_price":
                previous_price,

            "current_last_price":
                current_price,

            "last_price_diff":
                price_diff,

            "previous_ask_quantity":
                previous_ask_qty,

            "current_ask_quantity":
                current_ask_qty,

            "ask_quantity_diff":
                ask_qty_diff,

            "previous_bid_quantity":
                previous_bid_qty,

            "current_bid_quantity":
                current_bid_qty,

            "bid_quantity_diff":
                bid_qty_diff,

            "alert_type":
                alert_type,
        })


    print(
        f"[RESULT] records={len(differences)}"
    )

    return differences


# ============================================================
# Save differences
# ============================================================

def save_differences(
    differences
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        DIFFERENCES_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=DIFFERENCE_FIELDS,
        )

        writer.writeheader()

        writer.writerows(
            differences
        )

    print(
        f"[SAVE] "
        f"{DIFFERENCES_FILE} "
        f"records={len(differences)}"
    )


# ============================================================
# Build individual alert candidates
# ============================================================

def get_alert_candidates(
    differences
):

    candidates = []

    for row in differences:

        if row.get(
            "alert_type",
            ""
        ):

            candidates.append(
                row
            )

    # --------------------------------------------------------
    # 重要度順
    #
    # OI変化 + Volume変化 + Price変化
    # --------------------------------------------------------

    def score(row):

        oi = abs(
            number(
                row.get(
                    "open_interest_diff"
                )
            )
        )

        volume = abs(
            number(
                row.get(
                    "volume_diff"
                )
            )
        )

        price = abs(
            number(
                row.get(
                    "last_price_diff"
                )
            )
        )

        return (
            oi * 3
            +
            volume * 2
            +
            price / 100
        )

    candidates.sort(
        key=score,
        reverse=True,
    )

    return candidates


# ============================================================
# Build flow candidates
# ============================================================

def get_flow_candidates(
    differences
):

    candidates = []

    for row in differences:

        oi_diff = number(
            row.get(
                "open_interest_diff"
            )
        )

        volume_diff = number(
            row.get(
                "volume_diff"
            )
        )

        # ----------------------------------------------------
        # OIもVolumeも動いていないものは除外
        # ----------------------------------------------------

        if (
            abs(oi_diff)
            < FLOW_OI_MIN
            and
            volume_diff
            < FLOW_VOLUME_MIN
        ):

            continue

        candidates.append(
            row
        )


    # --------------------------------------------------------
    # Flowの重要度
    # --------------------------------------------------------

    def score(row):

        oi = abs(
            number(
                row.get(
                    "open_interest_diff"
                )
            )
        )

        volume = max(
            number(
                row.get(
                    "volume_diff"
                )
            ),
            0
        )

        return (
            oi * 3
            +
            volume * 2
        )


    candidates.sort(
        key=score,
        reverse=True,
    )


    return candidates[
        :FLOW_MAX_ITEMS
    ]


# ============================================================
# Build flow message
# ============================================================

def build_flow_message(
    differences
):

    flow = get_flow_candidates(
        differences
    )

    if not flow:

        return None


    # ========================================================
    # Contract grouping
    # ========================================================

    grouped = {}

    for row in flow:

        contract = row.get(
            "contract",
            ""
        )

        option_type = row.get(
            "option_type",
            ""
        )

        if contract not in grouped:

            grouped[contract] = {
                "CALL": [],
                "PUT": [],
            }

        grouped[
            contract
        ][
            option_type
        ].append(
            row
        )


    # ========================================================
    # Message
    # ========================================================

    lines = []

    lines.append(
        "🚨 **JPX OPTION FLOW**"
    )

    lines.append(
        "━━━━━━━━━━━━━━━━"
    )


    for contract in sorted(
        grouped.keys()
    ):

        lines.append(
            f"**{contract}**"
        )

        for option_type in (
            "CALL",
            "PUT",
        ):

            rows = grouped[
                contract
            ][
                option_type
            ]

            if not rows:
                continue

            lines.append(
                f"**{option_type}**"
            )

            for row in rows:

                strike = fmt(
                    row.get(
                        "strike"
                    )
                )

                oi_diff = fmt_signed(
                    row.get(
                        "open_interest_diff"
                    )
                )

                volume_diff = fmt_signed(
                    row.get(
                        "volume_diff"
                    )
                )

                lines.append(
                    f"`{strike:>7}` "
                    f"OI {oi_diff} / "
                    f"Vol {volume_diff}"
                )

        lines.append(
            "━━━━━━━━━━━━━━━━"
        )


    return "\n".join(
        lines
    )


# ============================================================
# Build individual alert message
# ============================================================

def build_alert_message(
    row
):

    contract = row.get(
        "contract",
        ""
    )

    option_type = row.get(
        "option_type",
        ""
    )

    strike = fmt(
        row.get(
            "strike"
        )
    )

    oi_diff = fmt_signed(
        row.get(
            "open_interest_diff"
        )
    )

    volume_diff = fmt_signed(
        row.get(
            "volume_diff"
        )
    )

    price_diff = fmt_signed(
        row.get(
            "last_price_diff"
        )
    )

    alert_type = row.get(
        "alert_type",
        ""
    )


    return (
        "🚨 **JPX OPTION ALERT**\n"
        f"**{contract} {option_type} {strike}**\n"
        "\n"
        f"OI: `{oi_diff}`\n"
        f"Volume: `{volume_diff}`\n"
        f"Price: `{price_diff}`\n"
        f"Type: `{alert_type}`"
    )


# ============================================================
# Send Discord
# ============================================================

def send_discord_message(
    message
):

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] "
            "ERROR: DISCORD_WEBHOOK_URL "
            "is not set."
        )

        return False


    try:

        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={
                "content": message
            },
            timeout=15,
        )


        if response.status_code in (
            200,
            204,
        ):

            print(
                "[DISCORD] "
                "Notification sent."
            )

            return True


        print(
            f"[DISCORD] ERROR: "
            f"HTTP {response.status_code}"
        )

        print(
            response.text
        )

        return False


    except Exception as e:

        print(
            f"[DISCORD] ERROR: "
            f"{e}"
        )

        return False


# ============================================================
# Split Discord message
# ============================================================

def split_message(
    message,
    max_length=DISCORD_MAX_LENGTH,
):

    if len(message) <= max_length:

        return [
            message
        ]


    chunks = []

    current = ""

    for line in message.split(
        "\n"
    ):

        if (
            len(current)
            +
            len(line)
            +
            1
            > max_length
        ):

            if current:

                chunks.append(
                    current
                )

            current = line

        else:

            if current:

                current += "\n"

            current += line


    if current:

        chunks.append(
            current
        )

    return chunks


# ============================================================
# Send flow alert
# ============================================================

def send_flow_alert(
    differences
):

    print()
    print(
        "========================================"
    )
    print(
        "JPX OPTION FLOW"
    )
    print(
        "========================================"
    )


    message = build_flow_message(
        differences
    )


    if not message:

        print(
            "[FLOW] "
            "No significant flow."
        )

        return


    print(
        message
    )


    chunks = split_message(
        message
    )


    for chunk in chunks:

        send_discord_message(
            chunk
        )

        time.sleep(
            0.5
        )


# ============================================================
# Send individual alerts
# ============================================================

def send_individual_alerts(
    differences
):

    candidates = get_alert_candidates(
        differences
    )


    print()
    print(
        "========================================"
    )
    print(
        "DISCORD ALERT"
    )
    print(
        "========================================"
    )


    print(
        f"Alert candidates: "
        f"{len(candidates)}"
    )


    if not candidates:

        print(
            "[DISCORD] "
            "No alert candidates."
        )

        return


    # 最大10件
    candidates = candidates[
        :10
    ]


    for index, row in enumerate(
        candidates,
        start=1,
    ):

        print()
        print(
            f"[ALERT {index}/"
            f"{len(candidates)}]"
        )


        message = build_alert_message(
            row
        )


        print(
            message
        )


        if send_discord_message(
            message
        ):

            print(
                "[DISCORD] "
                "Alert sent."
            )

        else:

            print(
                "[DISCORD] "
                "Failed to send alert."
            )


        time.sleep(
            0.5
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
        "CALCULATE DIFFERENCES"
    )
    print(
        "========================================"
    )


    # ========================================================
    # Load current
    # ========================================================

    current_records = load_csv(
        LATEST_FILE
    )


    if not current_records:

        raise RuntimeError(
            "latest.csv is empty."
        )


    # ========================================================
    # Load previous
    # ========================================================

    previous_records = load_csv(
        PREVIOUS_FILE
    )


    # --------------------------------------------------------
    # 初回実行
    # --------------------------------------------------------

    if not previous_records:

        print()
        print(
            "[FIRST RUN]"
        )

        print(
            "No previous.csv."
        )

        print(
            "Creating baseline."
        )


        # latest -> previous
        save_previous(
            current_records
        )


        # 空の differences
        save_differences(
            []
        )


        print()
        print(
            "========================================"
        )

        print(
            "FIRST RUN COMPLETE"
        )

        print(
            "========================================"
        )

        return


    # ========================================================
    # Calculate
    # ========================================================

    differences = calculate_differences(
        current_records,
        previous_records,
    )


    # ========================================================
    # Save
    # ========================================================

    save_differences(
        differences
    )


    # ========================================================
    # Discord
    # ========================================================

    if DISCORD_WEBHOOK_URL:

        print()
        print(
            "[DISCORD] "
            "Webhook URL is configured."
        )

        # ----------------------------------------------------
        # まずFlow
        # ----------------------------------------------------

        send_flow_alert(
            differences
        )

        # ----------------------------------------------------
        # 個別アラート
        # ----------------------------------------------------

        send_individual_alerts(
            differences
        )

    else:

        print()
        print(
            "[DISCORD] "
            "Webhook URL is NOT configured."
        )


    # ========================================================
    # Update previous
    # ========================================================

    save_previous(
        current_records
    )


    # ========================================================
    # Complete
    # ========================================================

    print()
    print(
        "========================================"
    )

    print(
        "DIFFERENCE COMPLETE"
    )

    print(
        f"Current records: "
        f"{len(current_records)}"
    )

    print(
        f"Previous records: "
        f"{len(previous_records)}"
    )

    print(
        f"Difference records: "
        f"{len(differences)}"
    )

    alert_candidates = get_alert_candidates(
        differences
    )

    flow_candidates = get_flow_candidates(
        differences
    )

    print(
        f"Alert candidates: "
        f"{len(alert_candidates)}"
    )

    print(
        f"Flow candidates: "
        f"{len(flow_candidates)}"
    )

    print(
        "========================================"
    )


# ============================================================
# Save previous
# ============================================================

def save_previous(
    records
):

    with open(
        PREVIOUS_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=records[0].keys()
        )

        writer.writeheader()

        writer.writerows(
            records
        )

    print(
        f"[SAVE] "
        f"{PREVIOUS_FILE} "
        f"records={len(records)}"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
