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
CURRENT_FILE = DATA_DIR / "current.csv"
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

# 大口取引
VOLUME_THRESHOLD = 100

# 建玉増加
OI_INCREASE_THRESHOLD = 100

# 建玉減少
OI_DECREASE_THRESHOLD = 100

# 価格変化
PRICE_CHANGE_THRESHOLD = 100

# 1回の実行で最大通知数
MAX_DISCORD_ALERTS = 20

# Discord通知間隔
DISCORD_INTERVAL = 0.5


# ============================================================
# Difference fields
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

            reader = csv.DictReader(f)

            records = list(reader)

        print(
            f"[LOAD] "
            f"{path} "
            f"records={len(records)}"
        )

        return records

    except Exception as e:

        print(
            f"[ERROR] "
            f"Could not read {path}: {e}"
        )

        return []


# ============================================================
# Number
# ============================================================

def number(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value in (
        "-",
        "--",
        "－",
        "―",
    ):

        return None

    value = value.replace(
        ",",
        ""
    )

    try:

        return float(value)

    except Exception:

        return None


# ============================================================
# Format
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
        f"[CURRENT] "
        f"records={len(current_records)}"
    )

    print(
        f"[PREVIOUS] "
        f"records={len(previous_records)}"
    )


    # ========================================================
    # Previous map
    # ========================================================

    previous_map = {}


    for row in previous_records:

        key = (

            row.get(
                "contract",
                "",
            ),

            row.get(
                "option_type",
                "",
            ),

            row.get(
                "strike",
                "",
            ),

        )

        previous_map[key] = row


    # ========================================================
    # Calculate
    # ========================================================

    differences = []


    for current in current_records:

        key = (

            current.get(
                "contract",
                "",
            ),

            current.get(
                "option_type",
                "",
            ),

            current.get(
                "strike",
                "",
            ),

        )


        previous = previous_map.get(
            key
        )


        # ----------------------------------------------------
        # 初回取得などで前回データがない場合
        # ----------------------------------------------------

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


        if (
            previous_oi is not None
            and
            current_oi is not None
        ):

            oi_diff = (
                current_oi
                -
                previous_oi
            )

        else:

            oi_diff = 0


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


        if (
            previous_volume is not None
            and
            current_volume is not None
        ):

            volume_diff = (
                current_volume
                -
                previous_volume
            )

        else:

            volume_diff = 0


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


        # ----------------------------------------------------
        # 重要
        #
        # 両方に価格がある場合だけ差分計算
        # ----------------------------------------------------

        if (
            previous_price is not None
            and
            current_price is not None
        ):

            price_diff = (
                current_price
                -
                previous_price
            )

        else:

            price_diff = 0


        # ====================================================
        # Ask quantity
        # ====================================================

        previous_ask = number(
            previous.get(
                "ask_quantity"
            )
        )

        current_ask = number(
            current.get(
                "ask_quantity"
            )
        )


        if (
            previous_ask is not None
            and
            current_ask is not None
        ):

            ask_diff = (
                current_ask
                -
                previous_ask
            )

        else:

            ask_diff = 0


        # ====================================================
        # Bid quantity
        # ====================================================

        previous_bid = number(
            previous.get(
                "bid_quantity"
            )
        )

        current_bid = number(
            current.get(
                "bid_quantity"
            )
        )


        if (
            previous_bid is not None
            and
            current_bid is not None
        ):

            bid_diff = (
                current_bid
                -
                previous_bid
            )

        else:

            bid_diff = 0


        # ====================================================
        # Alert
        # ====================================================

        alerts = []


        # Volume

        if (
            volume_diff
            >=
            VOLUME_THRESHOLD
        ):

            alerts.append(
                "VOLUME"
            )


        # OI increase

        if (
            oi_diff
            >=
            OI_INCREASE_THRESHOLD
        ):

            alerts.append(
                "OI_INCREASE"
            )


        # OI decrease

        if (
            oi_diff
            <=
            -OI_DECREASE_THRESHOLD
        ):

            alerts.append(
                "OI_DECREASE"
            )


        # Price

        if (
            previous_price is not None
            and
            current_price is not None
            and
            abs(price_diff)
            >=
            PRICE_CHANGE_THRESHOLD
        ):

            alerts.append(
                "PRICE"
            )


        alert_type = ",".join(
            alerts
        )


        # ====================================================
        # Record
        # ====================================================

        differences.append({

            "qri_update_time":
                current.get(
                    "qri_update_time",
                    "",
                ),

            "collected_at":
                current.get(
                    "collected_at",
                    "",
                ),

            "contract":
                current.get(
                    "contract",
                    "",
                ),

            "option_type":
                current.get(
                    "option_type",
                    "",
                ),

            "strike":
                current.get(
                    "strike",
                    "",
                ),

            "previous_open_interest":
                previous_oi
                if previous_oi is not None
                else 0,

            "current_open_interest":
                current_oi
                if current_oi is not None
                else 0,

            "open_interest_diff":
                oi_diff,

            "previous_volume":
                previous_volume
                if previous_volume is not None
                else 0,

            "current_volume":
                current_volume
                if current_volume is not None
                else 0,

            "volume_diff":
                volume_diff,

            "previous_last_price":
                previous_price
                if previous_price is not None
                else "",

            "current_last_price":
                current_price
                if current_price is not None
                else "",

            "last_price_diff":
                price_diff,

            "previous_ask_quantity":
                previous_ask
                if previous_ask is not None
                else 0,

            "current_ask_quantity":
                current_ask
                if current_ask is not None
                else 0,

            "ask_quantity_diff":
                ask_diff,

            "previous_bid_quantity":
                previous_bid
                if previous_bid is not None
                else 0,

            "current_bid_quantity":
                current_bid
                if current_bid is not None
                else 0,

            "bid_quantity_diff":
                bid_diff,

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
        f"[DIFFERENCE] "
        f"{DIFFERENCES_FILE} "
        f"records={len(differences)}"
    )


# ============================================================
# Discord message
# ============================================================

def build_discord_message(
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

    volume_diff = number(
        row.get(
            "volume_diff"
        )
    )

    oi_diff = number(
        row.get(
            "open_interest_diff"
        )
    )

    price_diff = number(
        row.get(
            "last_price_diff"
        )
    )

    current_volume = number(
        row.get(
            "current_volume"
        )
    )

    current_oi = number(
        row.get(
            "current_open_interest"
        )
    )

    current_price = number(
        row.get(
            "current_last_price"
        )
    )

    alert_type = row.get(
        "alert_type",
        ""
    )


    # ========================================================
    # Title
    # ========================================================

    if "VOLUME" in alert_type:

        title = "🔴 大口取引"

    elif "OI_INCREASE" in alert_type:

        title = "🟢 建玉増加"

    elif "OI_DECREASE" in alert_type:

        title = "🔵 建玉減少"

    else:

        title = "🟡 オプション価格変化"


    # ========================================================
    # Message
    # ========================================================

    return (
        f"{title}\n"
        f"\n"
        f"📅 限月 : {contract}\n"
        f"📌 種類 : {option_type}\n"
        f"🎯 Strike : {strike}\n"
        f"\n"
        f"📊 Volume : {fmt(volume_diff)}\n"
        f"📦 OI : {fmt(oi_diff)}\n"
        f"💴 Price : {fmt(price_diff)}\n"
        f"\n"
        f"現在Volume : {fmt(current_volume)}\n"
        f"現在OI : {fmt(current_oi)}\n"
        f"現在Price : {fmt(current_price)}\n"
        f"\n"
        f"🚨 {alert_type}"
    )


# ============================================================
# Discord send
# ============================================================

def send_discord_message(
    message
):

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] ERROR: "
            "Webhook URL is NOT configured."
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

        return False


    except Exception as e:

        print(
            f"[DISCORD] ERROR: {e}"
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
            "[DISCORD] Webhook URL is "
            "NOT configured."
        )

        return


    print(
        "[DISCORD] Webhook URL is configured."
    )


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


    # ========================================================
    # Priority
    # ========================================================

    def priority(row):

        alert_type = row.get(
            "alert_type",
            ""
        )

        if "VOLUME" in alert_type:

            return 1

        if "OI_INCREASE" in alert_type:

            return 2

        if "OI_DECREASE" in alert_type:

            return 3

        if "PRICE" in alert_type:

            return 4

        return 99


    alert_records.sort(
        key=priority
    )


    alert_records = alert_records[
        :MAX_DISCORD_ALERTS
    ]


    # ========================================================
    # Send
    # ========================================================

    for index, row in enumerate(
        alert_records,
        start=1,
    ):

        print()

        print(
            f"[ALERT {index}/"
            f"{len(alert_records)}]"
        )


        message = build_discord_message(
            row
        )


        print(
            message
        )


        if not send_discord_message(
            message
        ):

            print(
                "[DISCORD] "
                "Failed to send alert."
            )


        time.sleep(
            DISCORD_INTERVAL
        )


# ============================================================
# Update latest
# ============================================================

def update_latest():

    if not CURRENT_FILE.exists():

        raise RuntimeError(
            "current.csv does not exist."
        )


    # current.csvをlatest.csvへコピー
    with open(
        CURRENT_FILE,
        "r",
        encoding="utf-8-sig",
    ) as src:

        data = src.read()


    with open(
        LATEST_FILE,
        "w",
        encoding="utf-8-sig",
    ) as dst:

        dst.write(data)


    print(
        f"[LATEST] "
        f"{LATEST_FILE} updated."
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
    # 前回
    # ========================================================

    previous_records = load_csv(
        LATEST_FILE
    )


    # ========================================================
    # 今回
    # ========================================================

    current_records = load_csv(
        CURRENT_FILE
    )


    if not current_records:

        raise RuntimeError(
            "current.csv is empty."
        )


    # ========================================================
    # 初回
    # ========================================================

    if not previous_records:

        print()
        print(
            "[FIRST RUN]"
        )

        print(
            "No previous latest.csv."
        )

        print(
            "Difference calculation skipped."
        )


        save_differences([])

        update_latest()

        return


    # ========================================================
    # Difference
    # ========================================================

    differences = calculate_differences(

        previous_records,

        current_records,

    )


    # ========================================================
    # Save difference
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
    # latest update
    #
    # 通知処理が終わってから更新する
    # ========================================================

    update_latest()


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
