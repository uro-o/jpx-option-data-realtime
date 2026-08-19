import csv
import time
import os
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

DATA_DIR = Path("data")

LATEST_FILE = DATA_DIR / "latest.csv"
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
# Volume
# ------------------------------------------------------------

# 1回の更新で取引高が100枚以上増加
VOLUME_THRESHOLD = 100


# ------------------------------------------------------------
# Open Interest
# ------------------------------------------------------------

# 建玉残が100枚以上増加
OI_INCREASE_THRESHOLD = 100

# 建玉残が100枚以上減少
OI_DECREASE_THRESHOLD = 100


# ------------------------------------------------------------
# Price
# ------------------------------------------------------------

# 価格変化
PRICE_CHANGE_THRESHOLD = 100


# ------------------------------------------------------------
# Discord
# ------------------------------------------------------------

# 1回の実行で最大20件
MAX_DISCORD_ALERTS = 20

# 通知間隔
DISCORD_INTERVAL = 0.5


# ============================================================
# Difference CSV columns
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
            f"[WARNING] File not found: {path}"
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
# Number conversion
# ============================================================

def number(value):

    """
    数値変換。

    None / 空欄 / "-" は None を返す。
    """

    if value is None:
        return None

    if isinstance(value, str):

        value = value.strip()

        if value == "":
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


    # ========================================================
    # Previous data map
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
    # Difference
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
        # 前回データが存在しない場合
        # ----------------------------------------------------

        if previous is None:

            continue


        # ====================================================
        # Open Interest
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
        # 前回または今回の価格が存在しない場合、
        # 「価格差」は0とする。
        #
        # これにより
        #
        # 空欄 → 3110
        #
        # を
        #
        # +3110
        #
        # と誤認しない。
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


        if (
            previous_ask_qty is not None
            and
            current_ask_qty is not None
        ):

            ask_qty_diff = (
                current_ask_qty
                -
                previous_ask_qty
            )

        else:

            ask_qty_diff = 0


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


        if (
            previous_bid_qty is not None
            and
            current_bid_qty is not None
        ):

            bid_qty_diff = (
                current_bid_qty
                -
                previous_bid_qty
            )

        else:

            bid_qty_diff = 0


        # ====================================================
        # Alert detection
        # ====================================================

        alerts = []


        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

        if (
            volume_diff
            >=
            VOLUME_THRESHOLD
        ):

            alerts.append(
                "VOLUME"
            )


        # ----------------------------------------------------
        # OI increase
        # ----------------------------------------------------

        if (
            oi_diff
            >=
            OI_INCREASE_THRESHOLD
        ):

            alerts.append(
                "OI_INCREASE"
            )


        # ----------------------------------------------------
        # OI decrease
        # ----------------------------------------------------

        if (
            oi_diff
            <=
            -OI_DECREASE_THRESHOLD
        ):

            alerts.append(
                "OI_DECREASE"
            )


        # ----------------------------------------------------
        # Price
        #
        # 前回・今回の両方に価格が存在する場合のみ。
        # ----------------------------------------------------

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
        # Difference record
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
                previous_ask_qty
                if previous_ask_qty is not None
                else 0,

            "current_ask_quantity":
                current_ask_qty
                if current_ask_qty is not None
                else 0,

            "ask_quantity_diff":
                ask_qty_diff,

            "previous_bid_quantity":
                previous_bid_qty
                if previous_bid_qty is not None
                else 0,

            "current_bid_quantity":
                current_bid_qty
                if current_bid_qty is not None
                else 0,

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
    difference
):

    contract = difference.get(
        "contract",
        "",
    )

    option_type = difference.get(
        "option_type",
        "",
    )

    strike = fmt(
        difference.get(
            "strike"
        )
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
        "",
    )


    # ========================================================
    # Header
    # ========================================================

    if "VOLUME" in alert_type:

        title = "🔴 大口取引"

    elif "OI_INCREASE" in alert_type:

        title = "🟢 建玉増加"

    elif "OI_DECREASE" in alert_type:

        title = "🔵 建玉減少"

    elif "PRICE" in alert_type:

        title = "🟡 価格変化"

    else:

        title = "⚪ OPTION ALERT"


    # ========================================================
    # Message
    # ========================================================

    lines = [

        title,

        "",

        f"📅 限月 : {contract}",

        f"📌 種類 : {option_type}",

        f"🎯 Strike : {strike}",

        "",

        f"📊 Volume : {fmt(volume_diff)}",

        f"📦 OI : {fmt(oi_diff)}",

        f"💴 Price : {fmt(price_diff)}",

        "",

        f"現在Volume : {fmt(current_volume)}",

        f"現在OI : {fmt(current_oi)}",

        f"現在Price : {fmt(current_price)}",

        "",

        f"🚨 {alert_type}",

    ]


    return "\n".join(
        lines
    )


# ============================================================
# Send Discord
# ============================================================

def send_discord_message(
    message
):

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] ERROR: "
            "DISCORD_WEBHOOK_URL is not configured."
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


    # ========================================================
    # Webhook check
    # ========================================================

    if not DISCORD_WEBHOOK_URL:

        print(
            "[DISCORD] Webhook URL is NOT configured."
        )

        return


    print(
        "[DISCORD] Webhook URL is configured."
    )


    # ========================================================
    # Alert candidates
    # ========================================================

    alert_records = [

        row

        for row in differences

        if row.get(
            "alert_type",
            "",
        )

    ]


    print(
        f"Alert candidates: "
        f"{len(alert_records)}"
    )


    if not alert_records:

        print(
            "[DISCORD] "
            "No large trades detected."
        )

        return


    # ========================================================
    # Sort priority
    #
    # VOLUME / OIをPRICEより優先
    # ========================================================

    def alert_priority(row):

        alert_type = row.get(
            "alert_type",
            "",
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
        key=alert_priority
    )


    # ========================================================
    # Maximum alerts
    # ========================================================

    alert_records = alert_records[
        :MAX_DISCORD_ALERTS
    ]


    # ========================================================
    # Send
    # ========================================================

    for index, difference in enumerate(
        alert_records,
        start=1,
    ):

        message = build_discord_message(
            difference
        )


        print()

        print(
            f"[ALERT "
            f"{index}/"
            f"{len(alert_records)}]"
        )

        print(
            message
        )


        success = send_discord_message(
            message
        )


        if not success:

            print(
                "[DISCORD] "
                "Failed to send alert."
            )


        time.sleep(
            DISCORD_INTERVAL
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
    # Load
    # ========================================================

    current_records = load_csv(
        LATEST_FILE
    )


    # --------------------------------------------------------
    # previous.csvではなく
    # historyから直近データを取得する場合にも対応
    #
    # 現在の構成では latest.csv を前回データとして使用
    # --------------------------------------------------------

    previous_records = load_csv(
        LATEST_FILE
    )


    # ========================================================
    # 注意
    #
    # このスクリプトを
    #
    # get_option_data.py
    # ↓
    # calculate_difference.py
    #
    # の順番で実行している場合、
    #
    # latest.csv は既に新しいデータになっています。
    #
    # その場合、latest.csvだけでは前回データと
    # 比較できません。
    #
    # そのため環境変数
    # PREVIOUS_FILE
    # が指定されている場合はそれを優先します。
    # ========================================================

    previous_file = os.environ.get(
        "PREVIOUS_FILE",
        "",
    )


    if previous_file:

        previous_records = load_csv(
            Path(previous_file)
        )


    # ========================================================
    # Difference
    # ========================================================

    differences = calculate_differences(
        previous_records,
        current_records,
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
        "========================================"


    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
