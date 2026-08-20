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
# Discord settings
# ============================================================

# 0 = 無制限
MAX_ALERTS = 0

# Discordの1メッセージ最大文字数を安全側に設定
DISCORD_MAX_LENGTH = 1900

# Discord送信失敗時の最大リトライ回数
DISCORD_RETRY_COUNT = 3

# リトライ間隔
DISCORD_RETRY_WAIT = 2

# 複数メッセージを送る場合の間隔
DISCORD_MESSAGE_INTERVAL = 1.0


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

        previous = previous_map.get(key)

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

        if volume_diff >= VOLUME_THRESHOLD:
            alerts.append("VOLUME")

        if oi_diff >= OI_INCREASE_THRESHOLD:
            alerts.append("OI_INCREASE")

        if oi_diff <= -OI_DECREASE_THRESHOLD:
            alerts.append("OI_DECREASE")

        if abs(price_diff) >= PRICE_CHANGE_THRESHOLD:
            alerts.append("PRICE")

        alert_type = ",".join(alerts)

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
# Volume gradient
# ============================================================

def volume_gradient(volume):

    volume = abs(number(volume))

    if volume >= 500:
        return "🔴 非常に大きい"

    if volume >= 200:
        return "🟠 大きい"

    if volume >= 100:
        return "🟡 大きい"

    if volume >= 50:
        return "🟢 やや大きい"

    if volume > 0:
        return "⚪ 小さい"

    return "⚪ 変化なし"


# ============================================================
# Estimated transaction amount
#
# 日経225オプション
# 1ポイント × 1,000円
# ============================================================

def estimated_transaction_amount(
    difference
):

    current_price = number(
        difference.get(
            "current_last_price"
        )
    )

    volume_diff = abs(
        number(
            difference.get(
                "volume_diff"
            )
        )
    )

    amount = (
        current_price *
        volume_diff *
        1000
    )

    return amount


# ============================================================
# Format transaction amount
# ============================================================

def fmt_money(amount):

    amount = float(amount)

    if amount <= 0:
        return "-"

    if amount >= 100000000:

        oku = amount / 100000000

        if oku >= 10:
            return f"約{oku:.0f}億円"

        return f"約{oku:.1f}億円"

    if amount >= 10000:

        man = amount / 10000

        if man >= 1000:
            return f"約{man:,.0f}万円"

        return f"約{man:0.0f}万円"

    return f"約{amount:,.0f}円"


# ============================================================
# Determine judgment
# ============================================================

def determine_judgment(
    volume_diff,
    oi_diff
):

    volume_diff = number(volume_diff)
    oi_diff = number(oi_diff)

    if volume_diff > 0 and oi_diff >= OI_INCREASE_THRESHOLD:

        return (
            "出来高増加 ＋ 建玉増加",
            "→ 新規ポジション形成の可能性：高"
        )

    if volume_diff > 0 and oi_diff <= -OI_DECREASE_THRESHOLD:

        return (
            "出来高増加 ＋ 建玉減少",
            "→ ポジション決済・整理の可能性：高"
        )

    if volume_diff > 0 and oi_diff > 0:

        return (
            "出来高増加 ＋ 建玉増加",
            "→ 新規ポジション形成の可能性：あり"
        )

    if volume_diff > 0 and oi_diff < 0:

        return (
            "出来高増加 ＋ 建玉減少",
            "→ ポジション決済・整理の可能性：あり"
        )

    if volume_diff > 0:

        return (
            "出来高増加",
            "→ 取引が活発化"
        )

    if oi_diff >= OI_INCREASE_THRESHOLD:

        return (
            "建玉増加",
            "→ 新規ポジション形成の可能性"
        )

    if oi_diff <= -OI_DECREASE_THRESHOLD:

        return (
            "建玉減少",
            "→ ポジション決済・整理の可能性"
        )

    if oi_diff > 0:

        return (
            "建玉増加",
            "→ 建玉が増加"
        )

    if oi_diff < 0:

        return (
            "建玉減少",
            "→ 建玉が減少"
        )

    return (
        "価格変化",
        "→ オプション価格が変化"
    )


# ============================================================
# Build alert message
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

    # --------------------------------------------------------
    # Alert title
    # --------------------------------------------------------

    if "OI_INCREASE" in difference.get(
        "alert_type",
        ""
    ):

        title = "🔥 大きな取引を検知"

    elif "OI_DECREASE" in difference.get(
        "alert_type",
        ""
    ):

        title = "🔥 大きな取引を検知"

    elif "VOLUME" in difference.get(
        "alert_type",
        ""
    ):

        title = "🔥 大きな取引を検知"

    else:

        title = "💹 オプション価格が大きく変化"

    # --------------------------------------------------------
    # Volume gradient
    # --------------------------------------------------------

    gradient = volume_gradient(
        volume_diff
    )

    # --------------------------------------------------------
    # Estimated transaction amount
    # --------------------------------------------------------

    estimated_amount = (
        estimated_transaction_amount(
            difference
        )
    )

    # --------------------------------------------------------
    # Judgment
    # --------------------------------------------------------

    judgment_main, judgment_sub = (
        determine_judgment(
            volume_diff,
            oi_diff
        )
    )

    # --------------------------------------------------------
    # Price direction
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
        "━━━━━━━━━━━━━━━━━━"
    )

    message.append(
        f"🔥 **{title.replace('🔥 ', '')}**"
    )

    message.append(
        f"【{contract}限 {option_type}】"
    )

    message.append(
        f"権利行使価格：**{fmt(strike)}円**"
    )

    message.append(
        f"変化時刻：**{qri_update_time}**"
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
    # Estimated transaction amount
    # --------------------------------------------------------

    if estimated_amount > 0:

        message.append(
            f"💰 概算取引金額：**{fmt_money(estimated_amount)}**"
        )

    else:

        message.append(
            "💰 概算取引金額：算出できません"
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

    if price_diff != 0:

        message.append(
            f"💴 価格：**{fmt_signed(price_diff)}円**"
        )

        message.append(
            f"→ 前回比で{price_direction}"
        )

    else:

        message.append(
            f"💴 価格：**{fmt(current_price)}円**"
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

    message.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    return "\n".join(
        message
    )


# ============================================================
# Build grouped Discord message
# ============================================================

def build_grouped_message(
    differences
):

    if not differences:
        return ""

    messages = []

    messages.append(
        "📡 **オプション変化通知**"
    )

    messages.append(
        f"検知件数：**{len(differences)}件**"
    )

    messages.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    for index, difference in enumerate(
        differences,
        start=1
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

        current_price = number(
            difference.get(
                "current_last_price"
            )
        )

        gradient = volume_gradient(
            volume_diff
        )

        amount = (
            estimated_transaction_amount(
                difference
            )
        )

        judgment_main, judgment_sub = (
            determine_judgment(
                volume_diff,
                oi_diff
            )
        )

        if price_diff > 0:
            price_text = (
                f"+{fmt(price_diff)}円 ↑"
            )

        elif price_diff < 0:
            price_text = (
                f"{fmt(price_diff)}円 ↓"
            )

        else:
            price_text = "変化なし"

        block = []

        block.append(
            f"**{index}. {contract}限 "
            f"{option_type} "
            f"{fmt(strike)}円**"
        )

        block.append(
            f"🕐 {qri_update_time}"
        )

        block.append(
            f"📦 取引量：**{fmt_signed(volume_diff)}枚** "
            f"{gradient}"
        )

        if amount > 0:

            block.append(
                f"💰 概算取引金額：**{fmt_money(amount)}**"
            )

        else:

            block.append(
                "💰 概算取引金額：算出できません"
            )

        block.append(
            f"📊 建玉：**{fmt_signed(oi_diff)}枚**"
        )

        block.append(
            f"💴 価格：**{price_text}**"
        )

        block.append(
            f"🔎 **{judgment_main}**"
        )

        block.append(
            judgment_sub
        )

        block.append(
            "──────────────────"
        )

        messages.extend(
            block
        )

    return "\n".join(
        messages
    )


# ============================================================
# Split Discord message
# ============================================================

def split_message(
    message,
    max_length=DISCORD_MAX_LENGTH
):

    if len(message) <= max_length:
        return [message]

    lines = message.split("\n")

    chunks = []
    current = ""

    for line in lines:

        candidate = (
            current +
            "\n" +
            line
        ).strip()

        if len(candidate) <= max_length:

            current = candidate

        else:

            if current:
                chunks.append(
                    current
                )

            current = line

    if current:
        chunks.append(
            current
        )

    return chunks


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
        DISCORD_RETRY_COUNT + 1
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

        if attempt < DISCORD_RETRY_COUNT:

            print(
                f"[DISCORD] "
                f"Retrying in "
                f"{DISCORD_RETRY_WAIT} seconds..."
            )

            time.sleep(
                DISCORD_RETRY_WAIT
            )

    print(
        "[DISCORD] "
        "All retry attempts failed."
    )

    return False


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

        if isinstance(
            data,
            list
        ):

            print(
                f"[PENDING] "
                f"Loaded {len(data)} pending alerts."
            )

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
        f"[PENDING] "
        f"Saved {len(alerts)} pending alerts."
    )


# ============================================================
# Clear pending alerts
# ============================================================

def clear_pending_alerts():

    if PENDING_ALERTS_FILE.exists():

        try:

            PENDING_ALERTS_FILE.unlink()

            print(
                "[PENDING] "
                "Pending alerts cleared."
            )

        except Exception as e:

            print(
                f"[WARNING] "
                f"Could not delete pending alerts: {e}"
            )


# ============================================================
# Alert candidate priority
# ============================================================

def alert_priority(row):

    alert_type = row.get(
        "alert_type",
        ""
    )

    score = 0

    if "OI_INCREASE" in alert_type:
        score += 100000

    if "OI_DECREASE" in alert_type:
        score += 90000

    if "VOLUME" in alert_type:
        score += 50000

    if "PRICE" in alert_type:
        score += 10000

    score += (
        abs(
            number(
                row.get(
                    "open_interest_diff"
                )
            )
        ) *
        10
    )

    score += abs(
        number(
            row.get(
                "volume_diff"
            )
        )
    )

    score += (
        abs(
            number(
                row.get(
                    "last_price_diff"
                )
            )
        )
    )

    return score


# ============================================================
# Get alert candidates
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

    candidates.sort(
        key=alert_priority,
        reverse=True
    )

    # --------------------------------------------------------
    # MAX_ALERTS
    #
    # 0 = 無制限
    # --------------------------------------------------------

    if MAX_ALERTS > 0:

        return candidates[
            :MAX_ALERTS
        ]

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
    # Load pending alerts first
    # --------------------------------------------------------

    pending_alerts = (
        load_pending_alerts()
    )

    pending_sent = 0

    if pending_alerts:

        print(
            f"[PENDING] "
            f"Retrying {len(pending_alerts)} "
            f"pending alerts."
        )

        pending_message = (
            build_grouped_message(
                pending_alerts
            )
        )

        pending_chunks = split_message(
            pending_message
        )

        pending_failed = False

        for chunk_index, chunk in enumerate(
            pending_chunks,
            start=1
        ):

            print(
                f"[PENDING] "
                f"Sending chunk "
                f"{chunk_index}/"
                f"{len(pending_chunks)}"
            )

            success = send_discord_message(
                chunk
            )

            if success:

                pending_sent += 1

                time.sleep(
                    DISCORD_MESSAGE_INTERVAL
                )

            else:

                pending_failed = True

                break

        if not pending_failed:

            clear_pending_alerts()

        else:

            print(
                "[PENDING] "
                "Pending alerts remain."
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

    if not candidates:

        print(
            "[DISCORD] "
            "No alert candidates."
        )

        return 0

    # --------------------------------------------------------
    # Build grouped message
    # --------------------------------------------------------

    grouped_message = (
        build_grouped_message(
            candidates
        )
    )

    chunks = split_message(
        grouped_message
    )

    print(
        f"[DISCORD] "
        f"Sending {len(candidates)} "
        f"alerts in {len(chunks)} message(s)."
    )

    # --------------------------------------------------------
    # Send chunks
    # --------------------------------------------------------

    sent_alerts = 0

    for chunk_index, chunk in enumerate(
        chunks,
        start=1
    ):

        print()
        print(
            f"[DISCORD] "
            f"Message "
            f"{chunk_index}/"
            f"{len(chunks)}"
        )

        success = send_discord_message(
            chunk
        )

        if success:

            # このchunkに含まれる候補数を概算
            # 1件目以降の番号を数える
            chunk_alert_count = (
                chunk.count(
                    "円**"
                )
            )

            sent_alerts += (
                chunk_alert_count
            )

        else:

            print(
                "[DISCORD] "
                "Message failed."
            )

            # ------------------------------------------------
            # 失敗した場合は候補全体を保留
            # ------------------------------------------------

            save_pending_alerts(
                candidates
            )

            print(
                "[DISCORD] "
                "Current alerts saved "
                "for retry."
            )

            break

        time.sleep(
            DISCORD_MESSAGE_INTERVAL
        )

    # --------------------------------------------------------
    # 送信成功した場合
    # --------------------------------------------------------

    if sent_alerts > 0:

        print(
            f"[DISCORD] "
            f"Alert messages sent successfully."
        )

    return len(candidates)


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
    #
    # Discord処理後に更新
    # --------------------------------------------------------

    save_previous(
        current_records
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    candidates_count = len(
        get_alert_candidates(
            differences
        )
    )

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
        f"{candidates_count}"
    )

    print(
        f"Alerts processed: "
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
