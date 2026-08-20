import csv
import json
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

ALERT_HISTORY_FILE = DATA_DIR / "alert_history.json"


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

# 大きな出来高増加
VOLUME_THRESHOLD = 100

# 建玉増加
OI_INCREASE_THRESHOLD = 100

# 建玉減少
OI_DECREASE_THRESHOLD = 100

# 大きな価格変化
PRICE_CHANGE_THRESHOLD = 100

# 1回の実行で送信する最大通知数
MAX_ALERTS = 10

# 同じオプションの再通知を抑制する時間
ALERT_COOLDOWN_MINUTES = 15


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

    "estimated_trade_value",

    "alert_type",
]


# ============================================================
# Utility
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
            .strip()
        )

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
# Format signed number
# ============================================================

def fmt_signed(value):

    try:

        value = float(value)

        if value > 0:

            if value.is_integer():

                return f"+{int(value):,}"

            return f"+{value:,.2f}"

        if value < 0:

            if value.is_integer():

                return f"{int(value):,}"

            return f"{value:,.2f}"

        return "0"

    except Exception:

        return "-"


# ============================================================
# Format money
# ============================================================

def fmt_money(value):

    try:

        value = float(value)

        abs_value = abs(value)

        if abs_value >= 100_000_000:

            return f"{value / 100_000_000:,.2f}億円"

        if abs_value >= 10_000:

            return f"{value / 10_000:,.1f}万円"

        return f"{value:,.0f}円"

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
            f"[LOAD] {path} "
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
# Save differences
# ============================================================

def save_differences(differences):

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
# Calculate estimated trade value
#
# Volume × Last Price × contract multiplier
#
# Nikkei 225 option:
# 1 index point = 1,000 yen
# ============================================================

def calculate_estimated_trade_value(
    volume_diff,
    price,
):

    if volume_diff <= 0:
        return 0

    if price <= 0:
        return 0

    multiplier = 1000

    return (
        volume_diff *
        price *
        multiplier
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

    # --------------------------------------------------------
    # Previous data map
    # --------------------------------------------------------

    previous_map = {}

    for row in previous_records:

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

        previous_map[key] = row

    differences = []

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    for current in current_records:

        key = (
            current.get(
                "contract",
                ""
            ),

            current.get(
                "option_type",
                ""
            ),

            current.get(
                "strike",
                ""
            ),
        )

        previous = previous_map.get(
            key
        )

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
        # Estimated trade value
        # ----------------------------------------------------

        estimated_trade_value = (
            calculate_estimated_trade_value(
                volume_diff,
                current_price,
            )
        )

        # ----------------------------------------------------
        # Alert type
        # ----------------------------------------------------

        alerts = []

        if (
            volume_diff >=
            VOLUME_THRESHOLD
        ):

            alerts.append(
                "VOLUME"
            )

        if (
            oi_diff >=
            OI_INCREASE_THRESHOLD
        ):

            alerts.append(
                "OI_INCREASE"
            )

        if (
            oi_diff <=
            -OI_DECREASE_THRESHOLD
        ):

            alerts.append(
                "OI_DECREASE"
            )

        if (
            abs(price_diff) >=
            PRICE_CHANGE_THRESHOLD
        ):

            alerts.append(
                "PRICE"
            )

        alert_type = ",".join(
            alerts
        )

        # ----------------------------------------------------
        # Save
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

            "estimated_trade_value":
                estimated_trade_value,

            "alert_type":
                alert_type,
        })

    print(
        f"[RESULT] "
        f"records={len(differences)}"
    )

    return differences


# ============================================================
# Alert history
# ============================================================

def load_alert_history():

    if not ALERT_HISTORY_FILE.exists():

        return {}

    try:

        with open(
            ALERT_HISTORY_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if isinstance(
            data,
            dict
        ):

            return data

        return {}

    except Exception as e:

        print(
            f"[WARNING] "
            f"Could not load alert history: {e}"
        )

        return {}


def save_alert_history(history):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        ALERT_HISTORY_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# Alert key
# ============================================================

def get_alert_key(
    difference
):

    return (
        f"{difference.get('contract', '')}_"
        f"{difference.get('option_type', '')}_"
        f"{difference.get('strike', '')}"
    )


# ============================================================
# Cooldown
# ============================================================

def is_in_cooldown(
    key,
    history,
):

    last_time = history.get(
        key
    )

    if not last_time:
        return False

    try:

        last_timestamp = float(
            last_time
        )

    except Exception:

        return False

    elapsed = (
        time.time() -
        last_timestamp
    )

    return (
        elapsed <
        ALERT_COOLDOWN_MINUTES * 60
    )


# ============================================================
# Option explanation
# ============================================================

def option_explanation(
    option_type
):

    if option_type == "CALL":

        return (
            "CALL：日経平均が上昇すると"
            "価値が上がりやすいタイプ"
        )

    if option_type == "PUT":

        return (
            "PUT：日経平均が下落すると"
            "価値が上がりやすいタイプ"
        )

    return ""


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

    current_price = number(
        difference.get(
            "current_last_price"
        )
    )

    estimated_value = number(
        difference.get(
            "estimated_trade_value"
        )
    )

    alert_type = difference.get(
        "alert_type",
        ""
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if "OI_INCREASE" in alert_type:

        title = (
            "🔥 大きな建玉増加を検知"
        )

    elif "OI_DECREASE" in alert_type:

        title = (
            "⚠️ 大きな建玉減少を検知"
        )

    elif "VOLUME" in alert_type:

        title = (
            "📈 大きな取引を検知"
        )

    elif "PRICE" in alert_type:

        title = (
            "💹 オプション価格が大きく変化"
        )

    else:

        title = (
            "🔔 オプション変化を検知"
        )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if price_diff > 0:

        price_direction = "上昇"

    elif price_diff < 0:

        price_direction = "下落"

    else:

        price_direction = "変化なし"

    # --------------------------------------------------------
    # Message
    # --------------------------------------------------------

    message = []

    message.append(
        f"**{title}**"
    )

    message.append("")

    message.append(
        f"【{contract}限 {option_type}】"
    )

    message.append(
        f"権利行使価格：**{fmt(strike)}円**"
    )

    message.append("")

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    if volume_diff > 0:

        message.append(
            f"📦 取引量："
            f"**{fmt_signed(volume_diff)}枚**"
        )

        if estimated_value > 0:

            message.append(
                f"💰 概算取引金額："
                f"**約{fmt_money(estimated_value)}**"
            )

        message.append(
            "→ 前回取得時点から増えた取引量"
        )

    else:

        message.append(
            "📦 取引量：大きな増加なし"
        )

    message.append("")

    # --------------------------------------------------------
    # OI
    # --------------------------------------------------------

    if oi_diff > 0:

        message.append(
            f"📊 建玉："
            f"**{fmt_signed(oi_diff)}枚**"
        )

        message.append(
            "→ 未決済ポジションが増加"
        )

    elif oi_diff < 0:

        message.append(
            f"📊 建玉："
            f"**{fmt_signed(oi_diff)}枚**"
        )

        message.append(
            "→ 未決済ポジションが減少"
        )

    else:

        message.append(
            "📊 建玉：変化なし"
        )

    message.append("")

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    message.append(
        f"💴 現在価格："
        f"**{fmt(current_price)}円**"
    )

    if price_diff != 0:

        message.append(
            f"前回比："
            f"**{fmt_signed(price_diff)}円**"
            f"（{price_direction}）"
        )

    else:

        message.append(
            "前回比：変化なし"
        )

    message.append("")

    # --------------------------------------------------------
    # Simple explanation
    # --------------------------------------------------------

    explanation = option_explanation(
        option_type
    )

    if explanation:

        message.append(
            f"ℹ️ {explanation}"
        )

        message.append("")

    # --------------------------------------------------------
    # Alert reason
    # --------------------------------------------------------

    reasons = []

    if "OI_INCREASE" in alert_type:

        reasons.append(
            "建玉が大きく増加"
        )

    if "OI_DECREASE" in alert_type:

        reasons.append(
            "建玉が大きく減少"
        )

    if "VOLUME" in alert_type:

        reasons.append(
            "取引量が大きく増加"
        )

    if "PRICE" in alert_type:

        reasons.append(
            "価格が大きく変化"
        )

    if reasons:

        message.append(
            "🚨 **通知理由**"
        )

        for reason in reasons:

            message.append(
                f"・{reason}"
            )

        message.append("")

    # --------------------------------------------------------
    # Disclaimer
    # --------------------------------------------------------

    message.append(
        "⚠️ 建玉や出来高だけでは、"
        "買い・売りを断定できません。"
    )

    message.append(
        "他の価格帯・価格変化と合わせて確認してください。"
    )

    return "\n".join(
        message
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

        print(
            response.text
        )

        return False

    except Exception as e:

        print(
            f"[DISCORD] ERROR: {e}"
        )

        return False


# ============================================================
# Alert candidates
# ============================================================

def get_alert_candidates(
    differences
):

    candidates = []

    for row in differences:

        alert_type = row.get(
            "alert_type",
            ""
        )

        if not alert_type:
            continue

        candidates.append(
            row
        )

    # --------------------------------------------------------
    # Priority
    #
    # OI増減 > Volume > Price
    # --------------------------------------------------------

    def priority(row):

        alert_type = row.get(
            "alert_type",
            ""
        )

        score = 0

        if "OI_INCREASE" in alert_type:

            score += 1000

        if "OI_DECREASE" in alert_type:

            score += 900

        if "VOLUME" in alert_type:

            score += 500

        if "PRICE" in alert_type:

            score += 100

        score += abs(
            number(
                row.get(
                    "open_interest_diff"
                )
            )
        )

        score += abs(
            number(
                row.get(
                    "volume_diff"
                )
            )
        )

        return score

    candidates.sort(
        key=priority,
        reverse=True
    )

    return candidates


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
            "[DISCORD] "
            "Webhook URL is NOT configured."
        )

        return 0

    print(
        "[DISCORD] "
        "Webhook URL is configured."
    )

    candidates = get_alert_candidates(
        differences
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

        return 0

    history = load_alert_history()

    sent_count = 0

    for difference in candidates:

        if sent_count >= MAX_ALERTS:

            print(
                f"[DISCORD] "
                f"Maximum alerts reached: "
                f"{MAX_ALERTS}"
            )

            break

        key = get_alert_key(
            difference
        )

        if is_in_cooldown(
            key,
            history
        ):

            print(
                f"[SKIP] "
                f"{key} "
                f"is in cooldown."
            )

            continue

        message = build_discord_message(
            difference
        )

        print()

        print(
            f"[ALERT "
            f"{sent_count + 1}/"
            f"{MAX_ALERTS}]"
        )

        print(
            f"{difference.get('contract', '')} "
            f"{difference.get('option_type', '')} "
            f"{difference.get('strike', '')}"
        )

        print(
            "OI diff: "
            + fmt_signed(
                difference.get(
                    "open_interest_diff"
                )
            )
        )

        print(
            "Volume diff: "
            + fmt_signed(
                difference.get(
                    "volume_diff"
                )
            )
        )

        print(
            "Price diff: "
            + fmt_signed(
                difference.get(
                    "last_price_diff"
                )
            )
        )

        print(
            "Estimated value: "
            + fmt_money(
                difference.get(
                    "estimated_trade_value"
                )
            )
        )

        print(
            "Alert type: "
            + difference.get(
                "alert_type",
                ""
            )
        )

        success = send_discord_message(
            message
        )

        if success:

            sent_count += 1

            history[key] = time.time()

            save_alert_history(
                history
            )

        else:

            print(
                "[DISCORD] "
                "Failed to send alert."
            )

        time.sleep(
            0.5
        )

    return sent_count


# ============================================================
# Save previous
# ============================================================

def save_previous(
    current_records
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not current_records:

        print(
            "[WARNING] "
            "No records to save to previous.csv."
        )

        return

    with open(
        PREVIOUS_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

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

    # --------------------------------------------------------
    # Load current
    # --------------------------------------------------------

    current_records = load_csv(
        CURRENT_FILE
    )

    if not current_records:

        raise RuntimeError(
            "latest.csv is empty."
        )

    # --------------------------------------------------------
    # Load previous
    # --------------------------------------------------------

    previous_records = load_csv(
        PREVIOUS_FILE
    )

    # --------------------------------------------------------
    # First run
    # --------------------------------------------------------

    if not previous_records:

        print()

        print(
            "[INFO] "
            "previous.csv is empty or does not exist."
        )

        print(
            "[INFO] "
            "Creating previous.csv."
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
            "FIRST RUN COMPLETE"
        )

        print(
            "========================================"
        )

        return

    # --------------------------------------------------------
    # Calculate
    # --------------------------------------------------------

    differences = calculate_differences(

        current_records,

        previous_records,
    )

    # --------------------------------------------------------
    # Save differences
    # --------------------------------------------------------

    save_differences(
        differences
    )

    # --------------------------------------------------------
    # Discord
    # --------------------------------------------------------

    alert_count = send_alerts(
        differences
    )

    # --------------------------------------------------------
    # Update previous
    # --------------------------------------------------------

    save_previous(
        current_records
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

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
        f"Alert candidates: "
        f"{len(get_alert_candidates(differences))}"
    )

    print(
        f"Alerts sent: "
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
