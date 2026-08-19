import csv
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

BASE_URL = "https://svc.qri.jp"

# 日経225オプション
# 2026年8月19日時点
CONTRACTS = {
    "2026-09": "/jpx/nkopm/",
    "2026-10": "/jpx/nkopm/1",
    "2026-12": "/jpx/nkopm/2",
}

DATA_DIR = Path("data")
HISTORY_DIR = DATA_DIR / "history"

DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

LATEST_FILE = DATA_DIR / "latest.csv"

JST = timezone(timedelta(hours=9))


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


# ============================================================
# 共通処理
# ============================================================

def clean_text(text):
    if text is None:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def to_number(text):

    text = clean_text(text)

    if not text:
        return None

    if text in ["-", "--", "－", "―"]:
        return None

    text = text.replace(",", "")
    text = text.replace("%", "")

    try:
        value = float(text)

        if value.is_integer():
            return int(value)

        return value

    except ValueError:
        return None


def parse_price_and_time(text):

    text = clean_text(text)

    if not text:
        return None, None

    parts = text.split()

    if len(parts) >= 2:

        price = to_number(parts[0])
        trade_time = " ".join(parts[1:])

        return price, trade_time

    return to_number(text), None


def parse_quote(text):

    text = clean_text(text)

    if not text or text == "-":
        return None, None, None, None

    pattern = r"(.+?)\s*\((.*?)\)\s*(.+?)\s*\((.*?)\)"

    match = re.match(pattern, text)

    if not match:
        return None, None, None, None

    ask_price = to_number(match.group(1))
    ask_quantity = to_number(match.group(2))

    bid_price = to_number(match.group(3))
    bid_quantity = to_number(match.group(4))

    return (
        ask_price,
        ask_quantity,
        bid_price,
        bid_quantity,
    )


# ============================================================
# QRI HTML取得
# ============================================================

def fetch_html(url):

    print(f"[GET] {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    response.encoding = response.apparent_encoding

    return response.text


# ============================================================
# QRI最終更新時刻
# ============================================================

def get_qri_update_time(soup):

    element = soup.select_one(".update-time dd")

    if not element:
        raise RuntimeError(
            "QRI update time not found."
        )

    return clean_text(
        element.get_text(" ", strip=True)
    )


# ============================================================
# 取引日・最終取引日
# ============================================================

def get_contract_info(soup):

    trading_day = ""
    last_trading_day = ""

    for area in soup.select(".date-table"):

        dt = area.select_one("dt")
        dd = area.select_one("dd")

        if not dt or not dd:
            continue

        label = clean_text(
            dt.get_text(" ", strip=True)
        )

        value = clean_text(
            dd.get_text(" ", strip=True)
        )

        if label == "取引日":
            trading_day = value

        elif label == "取引最終日":
            last_trading_day = value

    return trading_day, last_trading_day


# ============================================================
# オプションテーブル解析
# ============================================================

def parse_option_table(
    soup,
    contract,
    qri_update_time,
    collected_at,
    trading_day,
    last_trading_day,
):

    table = soup.select_one(
        "table.price-table"
    )

    if not table:
        raise RuntimeError(
            f"price-table not found: {contract}"
        )

    tbody = table.select_one(
        "tbody.price-info-scroll"
    )

    if not tbody:
        raise RuntimeError(
            f"price-info-scroll not found: {contract}"
        )

    records = []

    rows = tbody.find_all(
        "tr",
        recursive=False,
    )

    for row in rows:

        # Greek行は除外
        if "greek" in row.get("class", []):
            continue

        cells = row.find_all(
            "td",
            recursive=False,
        )

        # 通常の価格行は17列
        if len(cells) != 17:
            continue

        values = [
            clean_text(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )
            for cell in cells
        ]

        # ====================================================
        # CALL
        # ====================================================

        call_settlement = to_number(values[0])
        call_oi = to_number(values[1])
        call_volume = to_number(values[2])

        call_iv_parts = values[3].split()

        call_ask_iv = (
            to_number(call_iv_parts[0])
            if len(call_iv_parts) >= 1
            else None
        )

        call_bid_iv = (
            to_number(call_iv_parts[1])
            if len(call_iv_parts) >= 2
            else None
        )

        (
            call_ask_price,
            call_ask_quantity,
            call_bid_price,
            call_bid_quantity,
        ) = parse_quote(values[4])

        call_iv = to_number(values[5])

        call_change_parts = values[6].split()

        call_change = (
            to_number(call_change_parts[0])
            if len(call_change_parts) >= 1
            else None
        )

        call_change_percent = (
            to_number(call_change_parts[1])
            if len(call_change_parts) >= 2
            else None
        )

        call_last_price, call_trade_time = (
            parse_price_and_time(values[7])
        )

        # ====================================================
        # 権利行使価格
        # ====================================================

        strike = to_number(values[8])

        # ====================================================
        # PUT
        # ====================================================

        put_last_price, put_trade_time = (
            parse_price_and_time(values[9])
        )

        put_change_parts = values[10].split()

        put_change = (
            to_number(put_change_parts[0])
            if len(put_change_parts) >= 1
            else None
        )

        put_change_percent = (
            to_number(put_change_parts[1])
            if len(put_change_parts) >= 2
            else None
        )

        put_iv = to_number(values[11])

        (
            put_ask_price,
            put_ask_quantity,
            put_bid_price,
            put_bid_quantity,
        ) = parse_quote(values[12])

        put_iv_parts = values[13].split()

        put_ask_iv = (
            to_number(put_iv_parts[0])
            if len(put_iv_parts) >= 1
            else None
        )

        put_bid_iv = (
            to_number(put_iv_parts[1])
            if len(put_iv_parts) >= 2
            else None
        )

        put_volume = to_number(values[14])
        put_oi = to_number(values[15])
        put_settlement = to_number(values[16])

        # ====================================================
        # CALLレコード
        # ====================================================

        records.append({
            "qri_update_time": qri_update_time,
            "collected_at": collected_at,

            "trading_day": trading_day,
            "last_trading_day": last_trading_day,

            "contract": contract,
            "option_type": "CALL",
            "strike": strike,

            "settlement": call_settlement,
            "open_interest": call_oi,
            "volume": call_volume,

            "ask_iv": call_ask_iv,
            "bid_iv": call_bid_iv,

            "ask_price": call_ask_price,
            "ask_quantity": call_ask_quantity,

            "bid_price": call_bid_price,
            "bid_quantity": call_bid_quantity,

            "iv": call_iv,

            "change": call_change,
            "change_percent": call_change_percent,

            "last_price": call_last_price,
            "trade_time": call_trade_time,
        })

        # ====================================================
        # PUTレコード
        # ====================================================

        records.append({
            "qri_update_time": qri_update_time,
            "collected_at": collected_at,

            "trading_day": trading_day,
            "last_trading_day": last_trading_day,

            "contract": contract,
            "option_type": "PUT",
            "strike": strike,

            "settlement": put_settlement,
            "open_interest": put_oi,
            "volume": put_volume,

            "ask_iv": put_ask_iv,
            "bid_iv": put_bid_iv,

            "ask_price": put_ask_price,
            "ask_quantity": put_ask_quantity,

            "bid_price": put_bid_price,
            "bid_quantity": put_bid_quantity,

            "iv": put_iv,

            "change": put_change,
            "change_percent": put_change_percent,

            "last_price": put_last_price,
            "trade_time": put_trade_time,
        })

    return records


# ============================================================
# 1限月取得
# ============================================================

def get_contract_data(
    contract,
    path,
    collected_at,
):

    url = BASE_URL + path

    html = fetch_html(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    qri_update_time = get_qri_update_time(
        soup
    )

    trading_day, last_trading_day = (
        get_contract_info(soup)
    )

    records = parse_option_table(
        soup=soup,
        contract=contract,
        qri_update_time=qri_update_time,
        collected_at=collected_at,
        trading_day=trading_day,
        last_trading_day=last_trading_day,
    )

    print(
        f"[OK] {contract} "
        f"QRI update={qri_update_time} "
        f"records={len(records)}"
    )

    return qri_update_time, records


# ============================================================
# 最新CSV読み込み
# ============================================================

FIELDNAMES = [
    "qri_update_time",
    "collected_at",

    "trading_day",
    "last_trading_day",

    "contract",
    "option_type",
    "strike",

    "settlement",
    "open_interest",
    "volume",

    "ask_iv",
    "bid_iv",

    "ask_price",
    "ask_quantity",

    "bid_price",
    "bid_quantity",

    "iv",

    "change",
    "change_percent",

    "last_price",
    "trade_time",
]


def load_latest():

    if not LATEST_FILE.exists():
        return []

    with open(
        LATEST_FILE,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return list(
            csv.DictReader(f)
        )


# ============================================================
# 最新CSV保存
# ============================================================

def save_latest(records):

    with open(
        LATEST_FILE,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES,
        )

        writer.writeheader()
        writer.writerows(records)


# ============================================================
# QRI更新時刻の判定
# ============================================================

def get_previous_qri_update_time(
    latest_records
):

    if not latest_records:
        return None

    return latest_records[0].get(
        "qri_update_time"
    )


# ============================================================
# 履歴保存
# ============================================================

def save_history(
    records,
    trading_day,
):

    # 取引日からファイル名を作成
    date_match = re.search(
        r"(\d{4})/(\d{2})/(\d{2})",
        trading_day,
    )

    if date_match:

        date_string = (
            f"{date_match.group(1)}-"
            f"{date_match.group(2)}-"
            f"{date_match.group(3)}"
        )

    else:

        date_string = (
            datetime.now(JST)
            .strftime("%Y-%m-%d")
        )

    history_file = (
        HISTORY_DIR /
        f"{date_string}.csv"
    )

    file_exists = history_file.exists()

    with open(
        history_file,
        "a",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDNAMES,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(records)

    print(
        f"[HISTORY] {history_file} "
        f"+{len(records)} records"
    )


# ============================================================
# メイン
# ============================================================

def main():

    # GitHub Actionsで実際に取得した時刻
    collected_at = (
        datetime.now(timezone.utc)
        .astimezone(JST)
        .isoformat(
            timespec="seconds"
        )
    )

    print()
    print("========================================")
    print("JPX OPTION DATA")
    print("========================================")
    print(f"Collected at: {collected_at}")
    print("========================================")

    all_records = []

    qri_update_times = []

    # --------------------------------------------------------
    # 3限月を取得
    # --------------------------------------------------------

    for contract, path in CONTRACTS.items():

        try:

            qri_update_time, records = (
                get_contract_data(
                    contract,
                    path,
                    collected_at,
                )
            )

            qri_update_times.append(
                qri_update_time
            )

            all_records.extend(records)

        except Exception as e:

            print(
                f"[ERROR] {contract}: {e}"
            )

    if not all_records:

        raise RuntimeError(
            "No option data collected."
        )

    # --------------------------------------------------------
    # 前回データ
    # --------------------------------------------------------

    previous_records = load_latest()

    previous_update_time = (
        get_previous_qri_update_time(
            previous_records
        )
    )

    # 今回のQRI更新時刻
    #
    # 3限月とも同じ更新時刻であることを想定。
    # 異なる場合は最新時刻を使用。
    # --------------------------------------------------------

    current_update_time = max(
        qri_update_times
    )

    print()
    print(
        f"Previous QRI update : "
        f"{previous_update_time}"
    )

    print(
        f"Current QRI update  : "
        f"{current_update_time}"
    )

    # --------------------------------------------------------
    # QRI側が更新されていない場合
    # --------------------------------------------------------

    if (
        previous_update_time
        and
        current_update_time
        == previous_update_time
    ):

        print()
        print(
            "[SKIP] "
            "QRI update time has not changed."
        )

        print(
            "latest.csv and history were "
            "not updated."
        )

        return

    # --------------------------------------------------------
    # 新しいQRIデータ
    # --------------------------------------------------------

    print()
    print(
        "[NEW] "
        "QRI update detected."
    )

    # 最新データ更新
    save_latest(
        all_records
    )

    # 履歴保存
    trading_day = (
        all_records[0]["trading_day"]
    )

    save_history(
        all_records,
        trading_day,
    )

    print()
    print("========================================")
    print("Update completed")
    print("========================================")


if __name__ == "__main__":
    main()
