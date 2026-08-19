import csv
import os
import time
import requests
from pathlib import Path


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

# 取引高の増加
VOLUME_THRESHOLD = 100

# 建玉増加
OI_INCREASE_THRESHOLD = 100

# 建玉減少
OI_DECREASE_THRESHOLD = 100

# 最終価格の変化
PRICE_CHANGE_THRESHOLD = 100


# ============================================================
# Difference columns
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
# Number
# ============================================================

def number(value):

    if value is None:
        return 0

    if value == "":
        return 0

    try:

        return float(
            str(value)
            .replace(",", "")
        )

    except Exception:

        return 0


# ============================================================
# Format number
# ============================================================

def fmt(value):

    if value is None:
        return "-"

    try:

        value = float(value)

        if value.is_integer():

            return f"{int(value):,}"

        return f"{value:,.2f}"

    except Exception:

        return str(value)


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

            records = list(
                csv.DictReader(f)
            )

        print(
            f"[LOAD] {path} "
            f"records={len(records)}"
        )

        return records

    except Exception as e:

        print(
            f"[ERROR] Could not read "
            f"{path}: {e}"
        )

        return []


# ============================================================
# Save CSV
# ============================================================

def save_csv(
    path,
    records,
    fieldnames,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerows(
            records
        )

    print(
        f"[SAVE] {path} "
        f"records={len(records)}"
    )


# ============================================================
# Create key
# ============================================================

def make_key(row):

    return (
        str(
            row.get(
                "contract",
                ""
            )
        ).strip(),

        str(
            row.get(
                "option_type",
                ""
            )
        ).strip(),

        str(
            row.get(
                "strike",
                ""
            )
        ).strip(),
    )


# ============================================================
# Calculate differences
# ============================================================

def calculate_differences(
    previous_records,
    current_records,
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
        f"[CURRENT] records="
        f"{len(current_records)}"
    )

    print(
        f"[PREVIOUS] records="
        f"{len(previous_records)}"
    )


    # --------------------------------------------------------
    # Previous map
    # --------------------------------------------------------

    previous_map = {}

    for row in previous_records:

        key = make_key(row)

        previous_map[key] = row


    # --------------------------------------------------------
    # Calculate
    # --------------------------------------------------------

    differences = []

    for current in current_records:

        key = make_key(current)

        previous = previous_map.get(
            key
        )

        # 初回取得などで比較対象がない場合
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


        # ----------------------------------------------------
        # Alert type
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # Difference record
        # ----------------------------------------------------

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
        f"[RESULT] records="
        f"{len(differences)}"
    )

    return differences


# ============================================================
# Build Discord message
# ============================================================

def build_discord_message(
    difference
):

    contract = difference.get(
        "contract",
        ""
    )

    option_type = difference.get(
        "option_type",
        ""
    )

    strike = difference.get(
        "strike",
        ""
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


    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if price_diff > 0:

        price_direction = "▲"

    elif price_diff < 0:

        price_direction = "▼"

    else:

        price_direction = "→"


    message = (

        f"🚨 **JPX OPTION ALERT**\n"

        f"━━━━━━━━━━━━━━━━━━\n"

        f"**{contract} {option_type} {fmt(strike)}**\n\n"

        f"📊 OI差分: **{fmt(oi_diff)}**\n"

        f"📈 Volume差分: **{fmt(volume_diff)}**\n"

        f"💴 Price差分: "
        f"**{price_direction} "
        f"{fmt(price_diff)}**\n\n"

        f"🔔 Alert: **{alert_type}**\n"

        f"━━━━━━━━━━━━━━━━━━"
    )

    return message


# ============================================================
# Send Discord
# ============================================================

def send_discord_message(
    message
):

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] ERROR: "
            "DISCORD_WEBHOOK_URL is not set."
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


    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] ERROR: "
            "Webhook URL is NOT configured."
        )

    else:

        print(
            "[DISCORD] "
            "Webhook URL is configured."
        )


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
            "No alerts."
        )

        return


    # --------------------------------------------------------
    # 最大20件
    # --------------------------------------------------------

    max_alerts = 20

    alert_records = (
        alert_records[:max_alerts]
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


        print(
            f"{difference.get('contract')} "
            f"{difference.get('option_type')} "
            f"{difference.get('strike')}"
        )


        print(
            "OI diff: "
            f"{fmt(difference.get('open_interest_diff'))}"
        )


        print(
            "Volume diff: "
            f"{fmt(difference.get('volume_diff'))}"
        )


        print(
            "Price diff: "
            f"{fmt(difference.get('last_price_diff'))}"
        )


        print(
            "Alert type: "
            f"{difference.get('alert_type')}"
        )


        message = build_discord_message(
            difference
        )


        success = send_discord_message(
            message
        )


        if not success:

            print(
                "[DISCORD] "
                "Failed to send alert."
            )


        # Discordへの連続送信を少し待つ

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
    # IMPORTANT
    #
    # latest.csv は get_option_data.py が今回取得した
    # 最新データ。
    #
    # previous.csv は「前回実行時の latest.csv」。
    # ========================================================


    current_records = load_csv(
        LATEST_FILE
    )


    if not current_records:

        raise RuntimeError(
            "latest.csv is empty."
        )


    previous_records = load_csv(
        PREVIOUS_FILE
    )


    # ========================================================
    # 初回実行
    # ========================================================

    if not previous_records:

        print()
        print(
            "[FIRST RUN]"
        )

        print(
            "No previous.csv found."
        )

        print(
            "Creating previous.csv "
            "without sending Discord alerts."
        )


        save_csv(

            PREVIOUS_FILE,

            current_records,

            list(
                current_records[0].keys()
            ),
        )


        # differences.csv は空で作成

        save_csv(

            DIFFERENCES_FILE,

            [],

            DIFFERENCE_FIELDS,
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
    # Difference
    # ========================================================

    differences = calculate_differences(

        previous_records,

        current_records,
    )


    # ========================================================
    # Save differences
    # ========================================================

    save_csv(

        DIFFERENCES_FILE,

        differences,

        DIFFERENCE_FIELDS,
    )


    # ========================================================
    # Discord
    # ========================================================

    send_alerts(
        differences
    )


    # ========================================================
    # Update previous.csv
    #
    # Discord通知が終わってから更新する
    # ========================================================

    current_fields = list(
        current_records[0].keys()
    )


    save_csv(

        PREVIOUS_FILE,

        current_records,

        current_fields,
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

    print(
        "========================================"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
