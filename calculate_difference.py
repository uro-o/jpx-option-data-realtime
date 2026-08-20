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

# Discord送信に失敗した通知を保存
PENDING_ALERTS_FILE = DATA_DIR / "pending_alerts.json"


# ============================================================
# Discord
# ============================================================

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    ""
)

# Discord 1メッセージの安全な文字数
DISCORD_MAX_LENGTH = 1900

# Discord送信リトライ回数
DISCORD_MAX_RETRIES = 3

# リトライ間隔
DISCORD_RETRY_DELAY = 2


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
# Format money
# ============================================================

def fmt_money(value):

    try:

        value = float(value)

        if value >= 100_000_000:

            oku = value / 100_000_000

            if oku >= 10:

                return f"約{oku:,.0f}億円"

            return f"約{oku:,.2f}億円"

        if value >= 10_000:

            man = value / 10_000

            if man >= 100:

                return f"約{man:,.0f}万円"

            return f"約{man:,.1f}万円"

        return f"約{value:,.0f}円"

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
# Calculate differences
# ============================================================

def calculate_differences(
    current_records,
    previous_records,
):

    print()
    print("========================================")
    print("CALCULATING DIFFERENCE")
    print("========================================")

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

        key = (
            row.get("contract", ""),
            row.get("option_type", ""),
            row.get("strike", ""),
        )

        previous_map[key] = row

    differences = []

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    for current in current_records:

        key = (
            current.get("contract", ""),
            current.get("option_type", ""),
            current.get("strike", ""),
        )

        previous = previous_map.get(key)

        if previous is None:

            continue

        # ----------------------------------------------------
        # OI
        # ----------------------------------------------------

        previous_oi = number(
            previous.get("open_interest")
        )

        current_oi = number(
            current.get("open_interest")
        )

        oi_diff = (
            current_oi -
            previous_oi
        )

        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

        previous_volume = number(
            previous.get("volume")
        )

        current_volume = number(
            current.get("volume")
        )

        volume_diff = (
            current_volume -
            previous_volume
        )

        # ----------------------------------------------------
        # Last price
        # ----------------------------------------------------

        previous_price = number(
            previous.get("last_price")
        )

        current_price = number(
            current.get("last_price")
        )

        price_diff = (
            current_price -
            previous_price
        )

        # ----------------------------------------------------
        # Ask quantity
        # ----------------------------------------------------

        previous_ask_qty = number(
            previous.get("ask_quantity")
        )

        current_ask_qty = number(
            current.get("ask_quantity")
        )

        ask_qty_diff = (
            current_ask_qty -
            previous_ask_qty
        )

        # ----------------------------------------------------
        # Bid quantity
        # ----------------------------------------------------

        previous_bid_qty = number(
            previous.get("bid_quantity")
        )

        current_bid_qty = number(
            current.get("bid_quantity")
        )

        bid_qty_diff = (
            current_bid_qty -
            previous_bid_qty
        )

        # ----------------------------------------------------
        # Alert type
        # ----------------------------------------------------

        alerts = []

        if volume_diff >= VOLUME_THRESHOLD:

            alerts.append("VOLUME")

        if oi_diff >= OI_INCREASE_THRESHOLD:

            alerts.append("OI_INCREASE")

        if oi_diff <= -OI_DECREASE_THRESHOLD:

            alerts.append("OI_DECREASE")

        if abs(price_diff) >= PRICE_CHANGE_THRESHOLD:

            alerts.append("PRICE")

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
        f"[RESULT] records={len(differences)}"
    )

    return differences


# ============================================================
# Volume gradient
# ============================================================

def get_volume_gradient(volume):

    volume = abs(number(volume))

    if volume >= 500:

        return "🔴 非常に大きい"

    if volume >= 300:

        return "🟠 大きい"

    if volume >= 100:

        return "🟡 やや大きい"

    if volume >= 50:

        return "🟢 中程度"

    return "⚪ 小さい"


# ============================================================
# Estimated transaction amount
#
# 日経225オプション
# 1ポイント = 1,000円
#
# 概算取引金額
# = 現在価格 × 出来高増加枚数 × 1,000円
# ============================================================

def calculate_transaction_amount(
    current_price,
    volume_diff,
):

    price = abs(
        number(current_price)
    )

    volume = abs(
        number(volume_diff)
    )

    return (
        price *
        volume *
        1000
    )


# ============================================================
# Determine judgment
# ============================================================

def determine_judgment(
    volume_diff,
    oi_diff,
    price_diff,
):

    volume_up = (
        volume_diff >= VOLUME_THRESHOLD
    )

    oi_up = (
        oi_diff >= OI_INCREASE_THRESHOLD
    )

    oi_down = (
        oi_diff <= -OI_DECREASE_THRESHOLD
    )

    price_up = (
        price_diff > 0
    )

    price_down = (
        price_diff < 0
    )

    # --------------------------------------------------------
    # 出来高増加 ＋ 建玉増加
    # --------------------------------------------------------

    if volume_up and oi_up:

        if price_up:

            return (
                "出来高増加 ＋ 建玉増加 ＋ 価格上昇",
                "→ 上昇方向の新規ポジション形成の可能性：高"
            )

        if price_down:

            return (
                "出来高増加 ＋ 建玉増加 ＋ 価格下落",
                "→ 下落方向の新規ポジション形成の可能性：高"
            )

        return (
            "出来高増加 ＋ 建玉増加",
            "→ 新規ポジション形成の可能性：高"
        )

    # --------------------------------------------------------
    # 出来高増加 ＋ 建玉減少
    # --------------------------------------------------------

    if volume_up and oi_down:

        if price_up:

            return (
                "出来高増加 ＋ 建玉減少 ＋ 価格上昇",
                "→ 売りポジションの解消が進んでいる可能性：高"
            )

        if price_down:

            return (
                "出来高増加 ＋ 建玉減少 ＋ 価格下落",
                "→ 買いポジションの解消が進んでいる可能性：高"
            )

        return (
            "出来高増加 ＋ 建玉減少",
            "→ ポジション解消の可能性：高"
        )

    # --------------------------------------------------------
    # 出来高増加 ＋ OIほぼ変化なし
    # --------------------------------------------------------

    if volume_up:

        if price_up:

            return (
                "出来高増加 ＋ 建玉ほぼ変化なし ＋ 価格上昇",
                "→ 売買が活発化し、価格が上昇"
            )

        if price_down:

            return (
                "出来高増加 ＋ 建玉ほぼ変化なし ＋ 価格下落",
                "→ 売買が活発化し、価格が下落"
            )

        return (
            "出来高増加 ＋ 建玉ほぼ変化なし",
            "→ 取引が活発化"
        )

    # --------------------------------------------------------
    # 建玉増加
    # --------------------------------------------------------

    if oi_up:

        if price_up:

            return (
                "建玉増加 ＋ 価格上昇",
                "→ 上昇方向のポジション形成が進んでいる可能性"
            )

        if price_down:

            return (
                "建玉増加 ＋ 価格下落",
                "→ 下落方向のポジション形成が進んでいる可能性"
            )

        return (
            "建玉増加",
            "→ ポジション形成が進んでいる可能性"
        )

    # --------------------------------------------------------
    # 建玉減少
    # --------------------------------------------------------

    if oi_down:

        if price_up:

            return (
                "建玉減少 ＋ 価格上昇",
                "→ 売りポジションの解消が進んでいる可能性"
            )

        if price_down:

            return (
                "建玉減少 ＋ 価格下落",
                "→ 買いポジションの解消が進んでいる可能性"
            )

        return (
            "建玉減少",
            "→ ポジション解消が進んでいる可能性"
        )

    # --------------------------------------------------------
    # 価格のみ
    # --------------------------------------------------------

    if abs(price_diff) >= PRICE_CHANGE_THRESHOLD:

        if price_up:

            return (
                "価格上昇",
                "→ オプション価格が大きく上昇"
            )

        if price_down:

            return (
                "価格下落",
                "→ オプション価格が大きく下落"
            )

    # --------------------------------------------------------
    # その他
    # --------------------------------------------------------

    return (
        "大きな変化なし",
        "→ 現時点では目立ったポジション変化なし"
    )


# ============================================================
# Build single alert
# ============================================================

def build_discord_alert(
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

    qri_update_time = difference.get(
        "qri_update_time",
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

    current_price = number(
        difference.get(
            "current_last_price"
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
    # Title
    # --------------------------------------------------------

    if "OI_INCREASE" in alert_type:

        title = "🔥 大きな取引を検知"

    elif "VOLUME" in alert_type:

        title = "🔥 大きな取引を検知"

    elif "OI_DECREASE" in alert_type:

        title = "⚠️ ポジション変化を検知"

    elif "PRICE" in alert_type:

        title = "💹 オプション価格が大きく変化"

    else:

        title = "🔔 オプション変化を検知"

    # --------------------------------------------------------
    # Volume gradient
    # --------------------------------------------------------

    gradient = get_volume_gradient(
        volume_diff
    )

    # --------------------------------------------------------
    # Transaction amount
    # --------------------------------------------------------

    transaction_amount = calculate_transaction_amount(
        current_price,
        volume_diff,
    )

    # --------------------------------------------------------
    # Judgment
    # --------------------------------------------------------

    judgment_main, judgment_sub = determine_judgment(
        volume_diff,
        oi_diff,
        price_diff,
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

    message.append(
        f"変化時刻：{qri_update_time}"
    )

    message.append("")

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    message.append(
        f"📦 取引量：**{fmt_signed(volume_diff)}枚** {gradient}"
    )

    message.append(
        f"📦 取引量に応じたグラデーション判定"
    )

    message.append(
        f"→ {gradient}"
    )

    message.append("")

    # --------------------------------------------------------
    # Money
    # --------------------------------------------------------

    message.append(
        f"💰 概算取引金額：**{fmt_money(transaction_amount)}**"
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
        judgment_sub
    )

    message.append("")

    message.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    return "\n".join(
        message
    )


# ============================================================
# Load pending alerts
# ============================================================

def load_pending_alerts():

    if not PENDING_ALERTS_FILE.exists():

        return []

    try:

        with open(
            PENDING_ALERTS_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        if isinstance(data, list):

            return data

        return []

    except Exception as e:

        print(
            f"[WARNING] "
            f"Could not load pending alerts: {e}"
        )

        return []


# ============================================================
# Save pending alerts
# ============================================================

def save_pending_alerts(
    alerts
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        PENDING_ALERTS_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            alerts,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"[SAVE] "
        f"{PENDING_ALERTS_FILE} "
        f"alerts={len(alerts)}"
    )


# ============================================================
# Split Discord message
# ============================================================

def split_discord_message(
    message
):

    if len(message) <= DISCORD_MAX_LENGTH:

        return [message]

    parts = []

    current = ""

    lines = message.split("\n")

    for line in lines:

        # 追加すると上限を超える場合
        if (
            len(current) +
            len(line) +
            1
            > DISCORD_MAX_LENGTH
        ):

            if current:

                parts.append(
                    current
                )

                current = ""

        current += line + "\n"

    if current:

        parts.append(
            current.rstrip()
        )

    return parts


# ============================================================
# Send Discord single message
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

    for attempt in range(
        1,
        DISCORD_MAX_RETRIES + 1,
    ):

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
                    f"[DISCORD] "
                    f"Notification sent. "
                    f"attempt={attempt}"
                )

                return True

            print(
                f"[DISCORD] ERROR: "
                f"HTTP {response.status_code} "
                f"attempt={attempt}"
            )

            print(
                response.text
            )

        except Exception as e:

            print(
                f"[DISCORD] ERROR: "
                f"{e} "
                f"attempt={attempt}"
            )

        if attempt < DISCORD_MAX_RETRIES:

            time.sleep(
                DISCORD_RETRY_DELAY
            )

    return False


# ============================================================
# Send Discord message with splitting
# ============================================================

def send_discord_message_parts(
    message
):

    parts = split_discord_message(
        message
    )

    print(
        f"[DISCORD] "
        f"Message parts={len(parts)}"
    )

    for index, part in enumerate(
        parts,
        start=1
    ):

        print(
            f"[DISCORD] "
            f"Sending part "
            f"{index}/{len(parts)}"
        )

        success = send_discord_message(
            part
        )

        if not success:

            return False

        if index < len(parts):

            time.sleep(
                0.5
            )

    return True


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
    # Important alerts first
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
    print("========================================")
    print("DISCORD ALERT")
    print("========================================")

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
    # Load pending
    # --------------------------------------------------------

    pending_alerts = load_pending_alerts()

    if pending_alerts:

        print(
            f"[DISCORD] "
            f"Pending alerts: "
            f"{len(pending_alerts)}"
        )

    # --------------------------------------------------------
    # Current candidates
    # --------------------------------------------------------

    candidates = get_alert_candidates(
        differences
    )

    print(
        f"Alert candidates: "
        f"{len(candidates)}"
    )

    # --------------------------------------------------------
    # Nothing to send
    # --------------------------------------------------------

    if not candidates and not pending_alerts:

        print(
            "[DISCORD] "
            "No alert candidates."
        )

        return 0

    sent_count = 0

    # --------------------------------------------------------
    # First send pending alerts
    # --------------------------------------------------------

    if pending_alerts:

        print()
        print(
            "----------------------------------------"
        )

        print(
            "RESENDING PENDING ALERTS"
        )

        print(
            "----------------------------------------"
        )

        remaining_pending = []

        for pending in pending_alerts:

            message = pending.get(
                "message",
                ""
            )

            if not message:

                continue

            success = send_discord_message_parts(
                message
            )

            if success:

                sent_count += 1

            else:

                remaining_pending.append(
                    pending
                )

        save_pending_alerts(
            remaining_pending
        )

    # --------------------------------------------------------
    # Current alerts
    # --------------------------------------------------------

    if candidates:

        print()
        print(
            "----------------------------------------"
        )

        print(
            "CURRENT ALERTS"
        )

        print(
            "----------------------------------------"
        )

    for index, difference in enumerate(
        candidates,
        start=1
    ):

        print()
        print(
            f"[ALERT {index}/{len(candidates)}]"
        )

        print(
            f"{difference.get('contract', '')} "
            f"{difference.get('option_type', '')} "
            f"{difference.get('strike', '')}"
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

        message = build_discord_alert(
            difference
        )

        success = send_discord_message_parts(
            message
        )

        if success:

            sent_count += 1

        else:

            print(
                "[DISCORD] "
                "Failed to send alert."
            )

            # ------------------------------------------------
            # Save failed notification
            # ------------------------------------------------

            pending_alerts = load_pending_alerts()

            pending_alerts.append({

                "created_at":
                    time.time(),

                "contract":
                    difference.get(
                        "contract",
                        ""
                    ),

                "option_type":
                    difference.get(
                        "option_type",
                        ""
                    ),

                "strike":
                    difference.get(
                        "strike",
                        ""
                    ),

                "message":
                    message,
            })

            save_pending_alerts(
                pending_alerts
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

    fieldnames = list(
        current_records[0].keys()
    )

    with open(
        PREVIOUS_FILE,
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
    print("========================================")
    print("CALCULATE DIFFERENCES")
    print("========================================")

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
        print("========================================")
        print("FIRST RUN COMPLETE")
        print("========================================")

        return

    # --------------------------------------------------------
    # Calculate differences
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
    #
    # Discord処理後に更新する
    # --------------------------------------------------------

    save_previous(
        current_records
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    candidates = get_alert_candidates(
        differences
    )

    print()
    print("========================================")
    print("DIFFERENCE COMPLETE")

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
        f"{len(candidates)}"
    )

    print(
        f"Alerts sent: "
        f"{alert_count}"
    )

    print("========================================")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
