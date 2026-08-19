import csv
import os
import time
from pathlib import Path

import requests


# ============================================================
# Configuration
# ============================================================

DATA_DIR = Path("data")

CURRENT_FILE = DATA_DIR / "latest.csv"
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
# Alert settings
# ============================================================

# 出来高がこの数量以上増えたら通知
VOLUME_THRESHOLD = 100

# 建玉残がこの数量以上増えたら通知
OI_INCREASE_THRESHOLD = 100

# 建玉残がこの数量以上減ったら通知
OI_DECREASE_THRESHOLD = 100

# 価格変化
PRICE_CHANGE_THRESHOLD = 100

# Discord最大通知数
MAX_ALERTS = 20

# Discord送信間隔
DISCORD_INTERVAL = 0.5


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
# Number conversion
# ============================================================

def number(value):

    if value is None:
        return 0.0

    if value == "":
        return 0.0

    try:

        text = str(value).replace(",", "").strip()

        if text == "":
            return 0.0

        return float(text)

    except Exception:

        return 0.0


# ============================================================
# Format number
# ============================================================

def fmt(value):

    try:

        value = float(value)

        if value.is_integer():

            return f"{int(value):,}"

        return f"{value:,.2f}"

    except Exception:

        return "-"


# ============================================================
# Load CSV
# ============================================================

def load_csv(path):

    if not path.exists():

        print(
            f"[WARNING] {path} does not exist."
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
# Build key
# ============================================================

def build_key(row):

    contract = str(
        row.get(
            "contract",
            ""
        )
    ).strip()

    option_type = str(
        row.get(
            "option_type",
            ""
        )
    ).strip()

    strike = str(
        row.get(
            "strike",
            ""
        )
    ).strip()

    return (
        contract,
        option_type,
        strike,
    )


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
    # Previous data map
    # --------------------------------------------------------

    previous_map = {}

    for row in previous_records:

        key = build_key(row)

        previous_map[key] = row


    differences = []


    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    for current in current_records:

        key = build_key(current)

        previous = previous_map.get(
            key
        )


        # ----------------------------------------------------
        # 新しく登場した銘柄
        #
        # 初回値は差分通知しない
        # ----------------------------------------------------

        if previous is None:

            continue


        # ----------------------------------------------------
        # OI
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Last price
        # ----------------------------------------------------

        previous_price_raw = (
            previous.get(
                "last_price",
                ""
            )
        )

        current_price_raw = (
            current.get(
                "last_price",
                ""
            )
        )


        previous_price_exists = (
            str(
                previous_price_raw
            ).strip()
            != ""
        )

        current_price_exists = (
            str(
                current_price_raw
            ).strip()
            != ""
        )


        previous_price = number(
            previous_price_raw
        )

        current_price = number(
            current_price_raw
        )


        # ----------------------------------------------------
        # 価格差
        #
        # 価格が存在する場合のみ計算
        # ----------------------------------------------------

        if (
            previous_price_exists
            and
            current_price_exists
        ):

            price_diff = (
                current_price -
                previous_price
            )

        else:

            price_diff = 0.0


        # ----------------------------------------------------
        # Ask quantity
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Bid quantity
        # ----------------------------------------------------

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
        # Alert classification
        # ====================================================

        alerts = []


        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

        if (
            volume_diff
            >= VOLUME_THRESHOLD
        ):

            alerts.append(
                "VOLUME"
            )


        # ----------------------------------------------------
        # OI increase
        # ----------------------------------------------------

        if (
            oi_diff
            >= OI_INCREASE_THRESHOLD
        ):

            alerts.append(
                "OI_INCREASE"
            )


        # ----------------------------------------------------
        # OI decrease
        # ----------------------------------------------------

        if (
            oi_diff
            <= -OI_DECREASE_THRESHOLD
        ):

            alerts.append(
                "OI_DECREASE"
            )


        # ----------------------------------------------------
        # Price
        #
        # 以下の場合のみ価格アラート
        #
        # 1. 前回価格が存在
        # 2. 今回価格が存在
        # 3. 価格差が閾値以上
        # ----------------------------------------------------

        if (
            previous_price_exists
            and
            current_price_exists
            and
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
        # Save difference
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
        f"[RESULT] "
        f"records={len(differences)}"
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
# Discord webhook test
# ============================================================

def check_discord_config():

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] "
            "ERROR: Webhook URL is NOT configured."
        )

        return False


    print(
        "[DISCORD] "
        "Webhook URL is configured."
    )

    return True


# ============================================================
# Send Discord
# ============================================================

def send_discord_message(
    message
):

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] "
            "ERROR: DISCORD_WEBHOOK_URL is not set."
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
            f"[DISCORD] "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

        return False


    except Exception as e:

        print(
            f"[DISCORD] "
            f"ERROR: {e}"
        )

        return False


# ============================================================
# Build Discord message
# ============================================================

def build_discord_message(
    difference
):

    contract = difference.get(
        "contract",
        "-"
    )

    option_type = difference.get(
        "option_type",
        "-"
    )

    strike = difference.get(
        "strike",
        "-"
    )


    oi_diff = number(
        difference.get(
            "open_interest_diff"
        )
    )

    volume_diff = number(
        difference.get(
            "volume_diff"
        )
    )

    price_diff = number(
        difference.get(
            "last_price_diff"
        )
    )


    current_oi = number(
        difference.get(
            "current_open_interest"
        )
    )

    current_volume = number(
        difference.get(
            "current_volume"
        )
    )

    current_price = number(
        difference.get(
            "current_last_price"
        )
    )


    alert_type = difference.get(
        "alert_type",
        ""
    )


    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if price_diff > 0:

        price_direction = "📈"

    elif price_diff < 0:

        price_direction = "📉"

    else:

        price_direction = "➡️"


    # --------------------------------------------------------
    # Message
    # --------------------------------------------------------

    message = (

        "🚨 **JPX OPTION ALERT**\n"

        "\n"

        f"**{contract} "
        f"{option_type} "
        f"{fmt(strike)}**\n"

        f"Alert: **{alert_type}**\n"

        "\n"

        f"OI差分: "
        f"**{fmt(oi_diff)}**\n"

        f"現在OI: "
        f"{fmt(current_oi)}\n"

        "\n"

        f"出来高差分: "
        f"**{fmt(volume_diff)}**\n"

        f"現在出来高: "
        f"{fmt(current_volume)}\n"

        "\n"

        f"価格差分: "
        f"{price_direction} "
        f"**{fmt(price_diff)}**\n"

        f"現在価格: "
        f"{fmt(current_price)}\n"

    )


    return message


# ============================================================
# Send alerts
# ============================================================

def send_alerts(
    differences
):

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


    if not check_discord_config():

        print(
            "[DISCORD] "
            "Skipping notifications."
        )

        return


    # --------------------------------------------------------
    # Alert candidates
    # --------------------------------------------------------

    alert_records = [

        row

        for row in differences

        if row.get(
            "alert_type",
            ""
        )

    ]


    print(
        f"Alert candidates: "
        f"{len(alert_records)}"
    )


    if not alert_records:

        print(
            "[DISCORD] "
            "No alert candidates."
        )

        return


    # --------------------------------------------------------
    # Limit
    # --------------------------------------------------------

    if len(alert_records) > MAX_ALERTS:

        print(
            f"[DISCORD] "
            f"Limiting alerts to "
            f"{MAX_ALERTS}."
        )

        alert_records = (
            alert_records[:MAX_ALERTS]
        )


    # --------------------------------------------------------
    # Send
    # --------------------------------------------------------

    for index, difference in enumerate(
        alert_records,
        start=1,
    ):


        print()

        print(
            f"[ALERT "
            f"{index}/"
            f"{len(alert_records)}]"
        )


        contract = difference.get(
            "contract",
            "-"
        )

        option_type = difference.get(
            "option_type",
            "-"
        )

        strike = difference.get(
            "strike",
            "-"
        )

        oi_diff = number(
            difference.get(
                "open_interest_diff"
            )
        )

        volume_diff = number(
            difference.get(
                "volume_diff"
            )
        )

        price_diff = number(
            difference.get(
                "last_price_diff"
            )
        )

        alert_type = difference.get(
            "alert_type",
            ""
        )


        print(
            f"{contract} "
            f"{option_type} "
            f"{fmt(strike)}"
        )

        print(
            f"OI diff: "
            f"{fmt(oi_diff)}"
        )

        print(
            f"Volume diff: "
            f"{fmt(volume_diff)}"
        )

        print(
            f"Price diff: "
            f"{fmt(price_diff)}"
        )

        print(
            f"Alert type: "
            f"{alert_type}"
        )


        message = (
            build_discord_message(
                difference
            )
        )


        success = (
            send_discord_message(
                message
            )
        )


        if not success:

            print(
                "[DISCORD] "
                "Failed to send alert."
            )


        # ----------------------------------------------------
        # Rate limit protection
        # ----------------------------------------------------

        if (
            index
            < len(alert_records)
        ):

            time.sleep(
                DISCORD_INTERVAL
            )


# ============================================================
# Save previous
# ============================================================

def save_previous(
    current_records
):

    with open(
        PREVIOUS_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        if not current_records:

            return


        fieldnames = list(
            current_records[0].keys()
        )


        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            current_records
        )


    print(
        f"[SAVE] "
        f"{PREVIOUS_FILE} "
        f"records={len(current_records)}"
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
        CURRENT_FILE
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


    # ========================================================
    # First run
    # ========================================================

    if not previous_records:

        print()
        print(
            "[INFO] "
            "No previous.csv found."
        )

        print(
            "[INFO] "
            "Creating baseline."
        )


        save_previous(
            current_records
        )


        # 空のdifferenceを作成

        save_differences(
            []
        )


        print()
        print(
            "========================================"
        )

        print(
            "BASELINE CREATED"
        )

        print(
            "No Discord alert will be sent."
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
    # Save differences
    # ========================================================

    save_differences(
        differences
    )


    # ========================================================
    # Discord
    # ========================================================

    send_alerts(
        differences
    )


    # ========================================================
    # Update previous
    # ========================================================

    save_previous(
        current_records
    )


    # ========================================================
    # Summary
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

    alert_count = sum(

        1

        for row in differences

        if row.get(
            "alert_type",
            ""
        )

    )

    print(
        f"Alert candidates: "
        f"{alert_count}"
    )

    print(
        "========================================"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
