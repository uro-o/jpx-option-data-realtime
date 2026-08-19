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

# ------------------------------------------------------------
# 出来高
# ------------------------------------------------------------

VOLUME_THRESHOLD = 100


# ------------------------------------------------------------
# OI
# ------------------------------------------------------------

OI_INCREASE_THRESHOLD = 100

OI_DECREASE_THRESHOLD = 100


# ------------------------------------------------------------
# 価格
# ------------------------------------------------------------

PRICE_CHANGE_THRESHOLD = 100


# ------------------------------------------------------------
# 「OI + 出来高」の複合条件
#
# 例えば
#
# Volume +100以上
# OI +100以上
#
# → 新規建玉候補
# ------------------------------------------------------------

NEW_POSITION_VOLUME_THRESHOLD = 100

NEW_POSITION_OI_THRESHOLD = 100


# ------------------------------------------------------------
# 手仕舞い候補
# ------------------------------------------------------------

CLOSE_POSITION_VOLUME_THRESHOLD = 100

CLOSE_POSITION_OI_THRESHOLD = 100


# ------------------------------------------------------------
# Discord
# ------------------------------------------------------------

MAX_ALERTS = 20

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

        text = str(value)

        text = text.replace(
            ",",
            ""
        )

        text = text.strip()


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
            f"Could not read "
            f"{path}: {e}"
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
# Classify alert
# ============================================================

def classify_alert(

    oi_diff,

    volume_diff,

    price_diff,

    previous_price_exists,

    current_price_exists,

):

    alerts = []


    # ========================================================
    # 1. 新規建玉候補
    #
    # OI増加 + 出来高増加
    # ========================================================

    if (

        oi_diff
        >= NEW_POSITION_OI_THRESHOLD

        and

        volume_diff
        >= NEW_POSITION_VOLUME_THRESHOLD

    ):

        alerts.append(
            "NEW_POSITION"
        )


    # ========================================================
    # 2. 手仕舞い候補
    #
    # OI減少 + 出来高増加
    # ========================================================

    elif (

        oi_diff
        <= -CLOSE_POSITION_OI_THRESHOLD

        and

        volume_diff
        >= CLOSE_POSITION_VOLUME_THRESHOLD

    ):

        alerts.append(
            "CLOSE_POSITION"
        )


    # ========================================================
    # 3. OI単独増加
    # ========================================================

    elif (

        oi_diff
        >= OI_INCREASE_THRESHOLD

    ):

        alerts.append(
            "OI_INCREASE"
        )


    # ========================================================
    # 4. OI単独減少
    # ========================================================

    elif (

        oi_diff
        <= -OI_DECREASE_THRESHOLD

    ):

        alerts.append(
            "OI_DECREASE"
        )


    # ========================================================
    # 5. 出来高急増
    # ========================================================

    if (

        volume_diff
        >= VOLUME_THRESHOLD

    ):

        alerts.append(
            "VOLUME"
        )


    # ========================================================
    # 6. 価格急変
    # ========================================================

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


    return ",".join(
        alerts
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

        key = build_key(row)

        previous_map[key] = row


    differences = []


    # ========================================================
    # Compare
    # ========================================================

    for current in current_records:

        key = build_key(current)


        previous = previous_map.get(
            key
        )


        # ----------------------------------------------------
        # 新規登場銘柄は比較しない
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


        oi_diff = (

            current_oi

            -

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

            current_volume

            -

            previous_volume

        )


        # ====================================================
        # Price
        # ====================================================

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


        if (

            previous_price_exists

            and

            current_price_exists

        ):

            price_diff = (

                current_price

                -

                previous_price

            )

        else:

            price_diff = 0.0


        # ====================================================
        # Ask
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

            current_ask_qty

            -

            previous_ask_qty

        )


        # ====================================================
        # Bid
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

            current_bid_qty

            -

            previous_bid_qty

        )


        # ====================================================
        # Alert classification
        # ====================================================

        alert_type = classify_alert(

            oi_diff=oi_diff,

            volume_diff=volume_diff,

            price_diff=price_diff,

            previous_price_exists=
                previous_price_exists,

            current_price_exists=
                current_price_exists,

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
# Discord configuration
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
# Send Discord message
# ============================================================

def send_discord_message(

    message

):

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] "
            "ERROR: "
            "DISCORD_WEBHOOK_URL "
            "is not set."
        )

        return False


    try:

        response = requests.post(

            DISCORD_WEBHOOK_URL,

            json={

                "content":
                    message

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

            f"HTTP "
            f"{response.status_code}: "

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
# Alert label
# ============================================================

def get_alert_label(
    alert_type
):

    types = set(

        alert_type.split(",")

    )


    if "NEW_POSITION" in types:

        return (
            "🟢 新規建玉候補"
        )


    if "CLOSE_POSITION" in types:

        return (
            "🔵 手仕舞い候補"
        )


    if "VOLUME" in types:

        return (
            "🟡 出来高急増"
        )


    if "OI_INCREASE" in types:

        return (
            "🟢 OI増加"
        )


    if "OI_DECREASE" in types:

        return (
            "🔵 OI減少"
        )


    if "PRICE" in types:

        return (
            "🟠 価格急変"
        )


    return (
        "📊 OPTION ALERT"
    )


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


    # ========================================================
    # Alert label
    # ========================================================

    label = get_alert_label(
        alert_type
    )


    # ========================================================
    # Price direction
    # ========================================================

    if price_diff > 0:

        price_icon = "📈"

    elif price_diff < 0:

        price_icon = "📉"

    else:

        price_icon = "➡️"


    # ========================================================
    # Interpretation
    # ========================================================

    interpretation = ""


    if (
        "NEW_POSITION"
        in alert_type
    ):

        interpretation = (

            "\n"
            "💡 **OI増加＋出来高増加**\n"
            "→ 新規ポジション形成の可能性"

        )


    elif (
        "CLOSE_POSITION"
        in alert_type
    ):

        interpretation = (

            "\n"
            "💡 **OI減少＋出来高増加**\n"
            "→ 手仕舞い・反対売買の可能性"

        )


    elif (
        "VOLUME"
        in alert_type
    ):

        interpretation = (

            "\n"
            "💡 出来高が大きく増加"

        )


    # ========================================================
    # Message
    # ========================================================

    message = (

        "🚨 **JPX OPTION ALERT**\n"

        "\n"

        f"{label}\n"

        "\n"

        f"**{contract} "
        f"{option_type} "
        f"{fmt(strike)}**\n"

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
        f"{price_icon} "
        f"**{fmt(price_diff)}**\n"

        f"現在価格: "
        f"{fmt(current_price)}\n"

        f"{interpretation}"

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


    # ========================================================
    # Candidates
    # ========================================================

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


    # ========================================================
    # Priority
    #
    # NEW_POSITION
    # CLOSE_POSITION
    # VOLUME
    # OI
    # PRICE
    # ========================================================

    def priority(row):

        alert_type = row.get(
            "alert_type",
            ""
        )


        if (
            "NEW_POSITION"
            in alert_type
        ):

            return 1


        if (
            "CLOSE_POSITION"
            in alert_type
        ):

            return 2


        if (
            "VOLUME"
            in alert_type
        ):

            return 3


        if (
            "OI_INCREASE"
            in alert_type
            or
            "OI_DECREASE"
            in alert_type
        ):

            return 4


        if (
            "PRICE"
            in alert_type
        ):

            return 5


        return 99


    alert_records.sort(
        key=priority
    )


    # ========================================================
    # Limit
    # ========================================================

    if len(alert_records) > MAX_ALERTS:

        print(

            f"[DISCORD] "
            f"Limiting alerts to "
            f"{MAX_ALERTS}."

        )


        alert_records = (

            alert_records[
                :MAX_ALERTS
            ]

        )


    # ========================================================
    # Send
    # ========================================================

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

    if not current_records:

        print(
            "[WARNING] "
            "No records to save."
        )

        return


    with open(

        PREVIOUS_FILE,

        "w",

        encoding="utf-8-sig",

        newline="",

    ) as f:


        fieldnames = list(

            current_records[
                0
            ].keys()

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
        f"records="
        f"{len(current_records)}"

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
    # Current
    # ========================================================

    current_records = load_csv(
        CURRENT_FILE
    )


    if not current_records:

        raise RuntimeError(
            "latest.csv is empty."
        )


    # ========================================================
    # Previous
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
    # Difference
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


    new_position_count = sum(

        1

        for row in differences

        if (
            "NEW_POSITION"
            in row.get(
                "alert_type",
                ""
            )
        )

    )


    close_position_count = sum(

        1

        for row in differences

        if (
            "CLOSE_POSITION"
            in row.get(
                "alert_type",
                ""
            )
        )

    )


    volume_count = sum(

        1

        for row in differences

        if (
            "VOLUME"
            in row.get(
                "alert_type",
                ""
            )
        )

    )


    print(
        f"Alert candidates: "
        f"{alert_count}"
    )


    print(
        f"New position candidates: "
        f"{new_position_count}"
    )


    print(
        f"Close position candidates: "
        f"{close_position_count}"
    )


    print(
        f"Volume alerts: "
        f"{volume_count}"
    )


    print(
        "========================================"
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
