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

# 通知履歴
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

# ------------------------------------------------------------
# 通知対象となる最低出来高
#
# +20枚以上なら通知候補
# ------------------------------------------------------------

VOLUME_ALERT_THRESHOLD = 20


# ------------------------------------------------------------
# 大きな出来高
# ------------------------------------------------------------

VOLUME_LARGE_THRESHOLD = 50


# ------------------------------------------------------------
# 非常に大きな出来高
# ------------------------------------------------------------

VOLUME_VERY_LARGE_THRESHOLD = 100


# ------------------------------------------------------------
# 特大出来高
# ------------------------------------------------------------

VOLUME_HUGE_THRESHOLD = 200


# ------------------------------------------------------------
# 建玉増加
# ------------------------------------------------------------

OI_INCREASE_THRESHOLD = 100


# ------------------------------------------------------------
# 建玉減少
# ------------------------------------------------------------

OI_DECREASE_THRESHOLD = 100


# ------------------------------------------------------------
# 大きな価格変化
# ------------------------------------------------------------

PRICE_CHANGE_THRESHOLD = 100


# ------------------------------------------------------------
# 1回の実行で送信する最大通知数
# ------------------------------------------------------------

MAX_ALERTS = 10


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
# Volume gradient
# ============================================================

def volume_gradient(volume_diff):

    volume = number(volume_diff)

    if volume >= VOLUME_HUGE_THRESHOLD:

        return "🔴 特大"

    elif volume >= VOLUME_VERY_LARGE_THRESHOLD:

        return "🟠 非常に大きい"

    elif volume >= VOLUME_LARGE_THRESHOLD:

        return "🟡 大きい"

    elif volume >= VOLUME_ALERT_THRESHOLD:

        return "🟢 やや大きい"

    else:

        return "⚪ 小さい"


# ============================================================
# Approximate transaction value
# ============================================================

def calculate_transaction_value(
    volume_diff,
    price
):

    volume = number(volume_diff)
    price = number(price)

    # 日経225オプション
    #
    # 1ポイント = 1,000円
    #
    # 概算金額
    # = 出来高 × プレミアム × 1,000円
    #

    value = (
        abs(volume)
        * abs(price)
        * 1000
    )

    return value


# ============================================================
# Format transaction value
# ============================================================

def format_transaction_value(value):

    value = number(value)

    if value <= 0:
        return "-"

    if value >= 100_000_000:

        oku = value / 100_000_000

        return f"約{oku:.2f}億円"

    elif value >= 10_000_000:

        man = value / 10_000

        return f"約{man:,.0f}万円"

    elif value >= 10_000:

        man = value / 10_000

        return f"約{man:,.1f}万円"

    else:

        return f"約{value:,.0f}円"


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
        # Alert type
        # ----------------------------------------------------

        alerts = []


        # 出来高
        if (
            volume_diff
            >= VOLUME_ALERT_THRESHOLD
        ):

            alerts.append(
                "VOLUME"
            )


        # OI increase
        if (
            oi_diff
            >= OI_INCREASE_THRESHOLD
        ):

            alerts.append(
                "OI_INCREASE"
            )


        # OI decrease
        if (
            oi_diff
            <= -OI_DECREASE_THRESHOLD
        ):

            alerts.append(
                "OI_DECREASE"
            )


        # Price
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
        # Save difference
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
        f"[RESULT] "
        f"records={len(differences)}"
    )

    return differences


# ============================================================
# Load alert history
#
# 15分クールダウンは使用しない
#
# 前回通知時の出来高増加量を保存し、
# それを上回る大きな変化が発生した場合に再通知する
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


# ============================================================
# Save alert history
# ============================================================

def save_alert_history(
    history
):

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
# Determine whether alert should be sent
# ============================================================

def should_send_alert(
    difference,
    history
):

    key = get_alert_key(
        difference
    )


    volume_diff = number(
        difference.get(
            "volume_diff"
        )
    )


    oi_diff = number(
        difference.get(
            "open_interest_diff"
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


    if not alert_type:
        return False


    # --------------------------------------------------------
    # 前回通知履歴
    # --------------------------------------------------------

    previous_alert = history.get(
        key
    )


    # 初回
    if not previous_alert:

        return True


    # --------------------------------------------------------
    # 以前のデータが古い形式でも対応
    # --------------------------------------------------------

    if isinstance(
        previous_alert,
        (int, float)
    ):

        previous_volume = 0

    else:

        previous_volume = number(
            previous_alert.get(
                "volume_diff",
                0
            )
        )


    # --------------------------------------------------------
    # 新しい出来高増加が前回より大きい
    #
    # 例：
    #
    # 前回 +121
    # 今回 +30
    # → 通知しない
    #
    # 前回 +121
    # 今回 +250
    # → 再通知
    # --------------------------------------------------------

    if (
        volume_diff
        > previous_volume
    ):

        return True


    # --------------------------------------------------------
    # 出来高がなくても、
    # OIが非常に大きく変化した場合
    # --------------------------------------------------------

    if (
        abs(oi_diff)
        >= OI_INCREASE_THRESHOLD
    ):

        return True


    if (
        abs(price_diff)
        >= PRICE_CHANGE_THRESHOLD
        and
        abs(volume_diff)
        >= VOLUME_ALERT_THRESHOLD
    ):

        return True


    return False


# ============================================================
# Save alert record
# ============================================================

def save_alert_record(
    history,
    difference
):

    key = get_alert_key(
        difference
    )


    history[key] = {

        "timestamp":
            time.time(),

        "volume_diff":
            number(
                difference.get(
                    "volume_diff"
                )
            ),

        "oi_diff":
            number(
                difference.get(
                    "open_interest_diff"
                )
            ),

        "price_diff":
            number(
                difference.get(
                    "last_price_diff"
                )
            ),
    }


    save_alert_history(
        history
    )


# ============================================================
# Determine judgment
# ============================================================

def determine_judgment(
    volume_diff,
    oi_diff
):

    volume_positive = (
        volume_diff >=
        VOLUME_ALERT_THRESHOLD
    )

    oi_positive = (
        oi_diff >=
        OI_INCREASE_THRESHOLD
    )

    oi_negative = (
        oi_diff <=
        -OI_DECREASE_THRESHOLD
    )


    # --------------------------------------------------------
    # 出来高増加 + OI増加
    # --------------------------------------------------------

    if (
        volume_positive
        and
        oi_positive
    ):

        return (
            "出来高増加 ＋ 建玉増加",
            "→ 新規ポジション形成の可能性：高"
        )


    # --------------------------------------------------------
    # 出来高増加 + OI減少
    # --------------------------------------------------------

    if (
        volume_positive
        and
        oi_negative
    ):

        return (
            "出来高増加 ＋ 建玉減少",
            "→ ポジション決済の可能性：高"
        )


    # --------------------------------------------------------
    # 出来高増加のみ
    # --------------------------------------------------------

    if volume_positive:

        return (
            "出来高増加",
            "→ 取引活発化。新規・決済の判別は困難"
        )


    # --------------------------------------------------------
    # OI増加のみ
    # --------------------------------------------------------

    if oi_positive:

        return (
            "建玉増加",
            "→ 未決済ポジションが増加"
        )


    # --------------------------------------------------------
    # OI減少のみ
    # --------------------------------------------------------

    if oi_negative:

        return (
            "建玉減少",
            "→ ポジション解消の可能性"
        )


    # --------------------------------------------------------
    # Price only
    # --------------------------------------------------------

    return (
        "価格変化",
        "→ オプション価格が大きく変化"
    )


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


    qri_update_time = (
        difference.get(
            "qri_update_time",
            ""
        )
    )


    # --------------------------------------------------------
    # Volume gradient
    # --------------------------------------------------------

    gradient = volume_gradient(
        volume_diff
    )


    # --------------------------------------------------------
    # Transaction value
    # --------------------------------------------------------

    transaction_value = (
        calculate_transaction_value(
            volume_diff,
            current_price
        )
    )


    transaction_value_text = (
        format_transaction_value(
            transaction_value
        )
    )


    # --------------------------------------------------------
    # Judgment
    # --------------------------------------------------------

    judgment_main, judgment_detail = (
        determine_judgment(
            volume_diff,
            oi_diff
        )
    )


    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if (
        volume_diff
        >= VOLUME_HUGE_THRESHOLD
    ):

        title = (
            "🔥 特大の取引を検知"
        )

    elif (
        volume_diff
        >= VOLUME_VERY_LARGE_THRESHOLD
    ):

        title = (
            "🟠 非常に大きな取引を検知"
        )

    elif (
        volume_diff
        >= VOLUME_LARGE_THRESHOLD
    ):

        title = (
            "🟡 大きな取引を検知"
        )

    elif (
        "OI_INCREASE"
        in difference.get(
            "alert_type",
            ""
        )
    ):

        title = (
            "📊 建玉の大きな増加を検知"
        )

    elif (
        "OI_DECREASE"
        in difference.get(
            "alert_type",
            ""
        )
    ):

        title = (
            "📉 建玉の大きな減少を検知"
        )

    else:

        title = (
            "🔔 オプション変化を検知"
        )


    # --------------------------------------------------------
    # Message
    # --------------------------------------------------------

    message = []


    message.append(
        "━━━━━━━━━━━━━━━━━━"
    )


    message.append(
        f"**{title}**"
    )


    message.append(
        f"【{contract}限 {option_type}】"
    )


    message.append(
        f"権利行使価格：**{fmt(strike)}円**"
    )


    # --------------------------------------------------------
    # Change time
    # --------------------------------------------------------

    if qri_update_time:

        message.append(
            f"変化時刻：**{qri_update_time}**"
        )

    else:

        message.append(
            "変化時刻：-"
        )


    message.append("")


    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    message.append(
        f"📦 取引量：**{fmt_signed(volume_diff)}枚** "
        f"{gradient}"
    )


    message.append("")


    # --------------------------------------------------------
    # Transaction value
    # --------------------------------------------------------

    message.append(
        f"💰 概算取引金額：**{transaction_value_text}**"
    )


    message.append("")


    # --------------------------------------------------------
    # OI
    # --------------------------------------------------------

    message.append(
        f"📊 建玉：**{fmt_signed(oi_diff)}枚**"
    )


    message.append("")


    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    message.append(
        f"💴 価格：**{fmt_signed(price_diff)}円**"
    )


    message.append("")


    # --------------------------------------------------------
    # Judgment
    # --------------------------------------------------------

    message.append(
        "🔎 **判定**"
    )


    message.append(
        judgment_main
    )


    message.append(
        judgment_detail
    )


    message.append("")


    message.append(
        "━━━━━━━━━━━━━━━━━━"
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
# Select alert candidates
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
    # --------------------------------------------------------

    def priority(row):

        alert_type = row.get(
            "alert_type",
            ""
        )


        volume = number(
            row.get(
                "volume_diff"
            )
        )


        oi = abs(
            number(
                row.get(
                    "open_interest_diff"
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


        score = 0


        # 出来高
        score += (
            volume * 10
        )


        # OI
        score += (
            oi * 5
        )


        # Price
        score += (
            price
        )


        # OI増加
        if (
            "OI_INCREASE"
            in alert_type
        ):

            score += 5000


        # OI減少
        if (
            "OI_DECREASE"
            in alert_type
        ):

            score += 4000


        # Volume
        if (
            "VOLUME"
            in alert_type
        ):

            score += 3000


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


    # --------------------------------------------------------
    # Candidates
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # History
    # --------------------------------------------------------

    history = load_alert_history()


    sent_count = 0


    # --------------------------------------------------------
    # Send
    # --------------------------------------------------------

    for difference in candidates:

        if sent_count >= MAX_ALERTS:

            print(
                f"[DISCORD] "
                f"Maximum alerts reached: "
                f"{MAX_ALERTS}"
            )

            break


        # ----------------------------------------------------
        # New notification logic
        #
        # 15分クールダウンはなし
        # ----------------------------------------------------

        if not should_send_alert(
            difference,
            history
        ):

            print(
                f"[SKIP] "
                f"{get_alert_key(difference)} "
                f"did not exceed previous alert level."
            )

            continue


        # ----------------------------------------------------
        # Build message
        # ----------------------------------------------------

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
            f"QRI update time: "
            f"{difference.get('qri_update_time', '')}"
        )


        print(
            f"OI diff: "
            f"{fmt_signed(difference.get('open_interest_diff'))}"
        )


        print(
            f"Volume diff: "
            f"{fmt_signed(difference.get('volume_diff'))}"
        )


        print(
            f"Price diff: "
            f"{fmt_signed(difference.get('last_price_diff'))}"
        )


        print(
            f"Alert type: "
            f"{difference.get('alert_type', '')}"
        )


        # ----------------------------------------------------
        # Send
        # ----------------------------------------------------

        success = send_discord_message(
            message
        )


        if success:

            sent_count += 1


            save_alert_record(
                history,
                difference
            )


        else:

            print(
                "[DISCORD] "
                "Failed to send alert."
            )


        # ----------------------------------------------------
        # Delay
        # ----------------------------------------------------

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
            "No current records to save."
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
