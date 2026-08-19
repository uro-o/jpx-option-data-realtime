import csv
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# 設定
# ============================================================

CONTRACTS = {
    "2026-09": "https://svc.qri.jp/jpx/nkopm/",
    "2026-10": "https://svc.qri.jp/jpx/nkopm/1",
    "2026-12": "https://svc.qri.jp/jpx/nkopm/2",
}

DATA_DIR = Path("data")
HISTORY_DIR = DATA_DIR / "history"

DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

LATEST_FILE = DATA_DIR / "latest.csv"

JST = timezone(timedelta(hours=9))


# ============================================================
# HTTP Session
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),
    "Accept-Language": (
        "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})


# ============================================================
# CSV項目
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


# ============================================================
# 文字列処理
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# 数値変換
# ============================================================

def to_number(text):

    text = clean_text(text)

    if not text:
        return None

    if text in [
        "-",
        "--",
        "－",
        "―",
    ]:
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


# ============================================================
# 現在値 + 時刻
# ============================================================

def parse_price_and_time(text):

    text = clean_text(text)

    if not text:
        return None, None

    parts = text.split()

    if len(parts) >= 2:

        price = to_number(parts[0])

        trade_time = " ".join(
            parts[1:]
        )

        return price, trade_time

    return to_number(text), None


# ============================================================
# 気配値解析
#
# 例:
#
# 1 (77) - (-)
#
# ask_price       = 1
# ask_quantity    = 77
# bid_price       = -
# bid_quantity    = -
# ============================================================

def parse_quote(text):

    text = clean_text(text)

    if not text or text == "-":
        return (
            None,
            None,
            None,
            None,
        )

    pattern = (
        r"(.+?)\s*\((.*?)\)\s*"
        r"(.+?)\s*\((.*?)\)"
    )

    match = re.match(
        pattern,
        text,
    )

    if not match:

        return (
            None,
            None,
            None,
            None,
        )

    ask_price = to_number(
        match.group(1)
    )

    ask_quantity = to_number(
        match.group(2)
    )

    bid_price = to_number(
        match.group(3)
    )

    bid_quantity = to_number(
        match.group(4)
    )

    return (
        ask_price,
        ask_quantity,
        bid_price,
        bid_quantity,
    )


# ============================================================
# 2つの値を解析
#
# 例:
# 38.20% -
# ============================================================

def parse_two_values(text):

    parts = clean_text(
        text
    ).split()

    first = (
        to_number(parts[0])
        if len(parts) >= 1
        else None
    )

    second = (
        to_number(parts[1])
        if len(parts) >= 2
        else None
    )

    return first, second


# ============================================================
# QRI HTML取得
#
# ルートURLにはアクセスしない
# 各限月ページへ直接アクセス
#
# 503 / 502 / 500 / 504 / 429 はリトライ
# ============================================================

def fetch_html(url):

    print()
    print(
        f"[GET] {url}"
    )

    last_error = None

    for attempt in range(1, 4):

        try:

            response = session.get(
                url,
                headers={
                    "Referer":
                        "https://svc.qri.jp/jpx/nkopm/",
                },
                timeout=30,
                allow_redirects=True,
            )

            print(
                f"[HTTP] "
                f"attempt={attempt} "
                f"status={response.status_code} "
                f"url={response.url}"
            )

            # ------------------------------------------------
            # 成功
            # ------------------------------------------------

            if response.status_code == 200:

                # QRIはUTF-8
                response.encoding = "utf-8"

                return response.text

            # ------------------------------------------------
            # 一時的なエラー
            # ------------------------------------------------

            if response.status_code in (
                429,
                500,
                502,
                503,
                504,
            ):

                last_error = (
                    f"HTTP {response.status_code}"
                )

                print(
                    f"[RETRY] "
                    f"{last_error}"
                )

                if attempt < 3:

                    wait_seconds = (
                        attempt * 3
                    )

                    print(
                        f"[WAIT] "
                        f"{wait_seconds} seconds"
                    )

                    time.sleep(
                        wait_seconds
                    )

                    continue

                break

            # ------------------------------------------------
            # その他
            # ------------------------------------------------

            response.raise_for_status()

        except requests.RequestException as e:

            last_error = e

            print(
                f"[ERROR] "
                f"attempt={attempt}: {e}"
            )

            if attempt < 3:

                wait_seconds = (
                    attempt * 3
                )

                print(
                    f"[WAIT] "
                    f"{wait_seconds} seconds"
                )

                time.sleep(
                    wait_seconds
                )

    raise RuntimeError(
        f"Failed to fetch QRI page "
        f"after 3 attempts: "
        f"{url} / {last_error}"
    )


# ============================================================
# QRI更新時刻
# ============================================================

def get_qri_update_time(soup):

    element = soup.select_one(
        ".update-time dd"
    )

    if not element:

        raise RuntimeError(
            "QRI update time not found."
        )

    return clean_text(
        element.get_text(
            " ",
            strip=True,
        )
    )


# ============================================================
# 取引日・取引最終日
# ============================================================

def get_contract_info(soup):

    trading_day = ""
    last_trading_day = ""

    areas = soup.select(
        ".date-table"
    )

    for area in areas:

        dt = area.select_one("dt")
        dd = area.select_one("dd")

        if not dt or not dd:
            continue

        label = clean_text(
            dt.get_text(
                " ",
                strip=True,
            )
        )

        value = clean_text(
            dd.get_text(
                " ",
                strip=True,
            )
        )

        if label == "取引日":

            trading_day = value

        elif label == "取引最終日":

            last_trading_day = value

    return (
        trading_day,
        last_trading_day,
    )


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
            f"price-table not found: "
            f"{contract}"
        )

    print(
        f"[TABLE] "
        f"{contract}: "
        f"PRICE TABLE FOUND"
    )

    tbody = table.select_one(
        "tbody.price-info-scroll"
    )

    if not tbody:

        raise RuntimeError(
            f"price-info-scroll not found: "
            f"{contract}"
        )

    rows = tbody.find_all(
        "tr",
        recursive=False,
    )

    print(
        f"[TABLE] "
        f"{contract}: "
        f"{len(rows)} rows"
    )

    records = []

    for row in rows:

        classes = row.get(
            "class",
            [],
        )

        # -----------------------------------------------
        # Greek行を除外
        # -----------------------------------------------

        if "greek" in classes:
            continue

        cells = row.find_all(
            "td",
            recursive=False,
        )

        # -----------------------------------------------
        # 通常の価格行は17列
        # -----------------------------------------------

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

        # =================================================
        # CALL
        # =================================================

        call_settlement = to_number(
            values[0]
        )

        call_oi = to_number(
            values[1]
        )

        call_volume = to_number(
            values[2]
        )

        call_ask_iv, call_bid_iv = (
            parse_two_values(
                values[3]
            )
        )

        (
            call_ask_price,
            call_ask_quantity,
            call_bid_price,
            call_bid_quantity,
        ) = parse_quote(
            values[4]
        )

        call_iv = to_number(
            values[5]
        )

        call_change_parts = (
            values[6].split()
        )

        call_change = (
            to_number(
                call_change_parts[0]
            )
            if len(call_change_parts) >= 1
            else None
        )

        call_change_percent = (
            to_number(
                call_change_parts[1]
            )
            if len(call_change_parts) >= 2
            else None
        )

        (
            call_last_price,
            call_trade_time,
        ) = parse_price_and_time(
            values[7]
        )

        # =================================================
        # Strike
        # =================================================

        strike = to_number(
            values[8]
        )

        if strike is None:
            continue

        # =================================================
        # PUT
        # =================================================

        (
            put_last_price,
            put_trade_time,
        ) = parse_price_and_time(
            values[9]
        )

        put_change_parts = (
            values[10].split()
        )

        put_change = (
            to_number(
                put_change_parts[0]
            )
            if len(put_change_parts) >= 1
            else None
        )

        put_change_percent = (
            to_number(
                put_change_parts[1]
            )
            if len(put_change_parts) >= 2
            else None
        )

        put_iv = to_number(
            values[11]
        )

        (
            put_ask_price,
            put_ask_quantity,
            put_bid_price,
            put_bid_quantity,
        ) = parse_quote(
            values[12]
        )

        put_ask_iv, put_bid_iv = (
            parse_two_values(
                values[13]
            )
        )

        put_volume = to_number(
            values[14]
        )

        put_oi = to_number(
            values[15]
        )

        put_settlement = to_number(
            values[16]
        )

        # =================================================
        # CALLレコード
        # =================================================

        call_record = {

            "qri_update_time":
                qri_update_time,

            "collected_at":
                collected_at,

            "trading_day":
                trading_day,

            "last_trading_day":
                last_trading_day,

            "contract":
                contract,

            "option_type":
                "CALL",

            "strike":
                strike,

            "settlement":
                call_settlement,

            "open_interest":
                call_oi,

            "volume":
                call_volume,

            "ask_iv":
                call_ask_iv,

            "bid_iv":
                call_bid_iv,

            "ask_price":
                call_ask_price,

            "ask_quantity":
                call_ask_quantity,

            "bid_price":
                call_bid_price,

            "bid_quantity":
                call_bid_quantity,

            "iv":
                call_iv,

            "change":
                call_change,

            "change_percent":
                call_change_percent,

            "last_price":
                call_last_price,

            "trade_time":
                call_trade_time,
        }

        records.append(
            call_record
        )

        # =================================================
        # PUTレコード
        # =================================================

        put_record = {

            "qri_update_time":
                qri_update_time,

            "collected_at":
                collected_at,

            "trading_day":
                trading_day,

            "last_trading_day":
                last_trading_day,

            "contract":
                contract,

            "option_type":
                "PUT",

            "strike":
                strike,

            "settlement":
                put_settlement,

            "open_interest":
                put_oi,

            "volume":
                put_volume,

            "ask_iv":
                put_ask_iv,

            "bid_iv":
                put_bid_iv,

            "ask_price":
                put_ask_price,

            "ask_quantity":
                put_ask_quantity,

            "bid_price":
                put_bid_price,

            "bid_quantity":
                put_bid_quantity,

            "iv":
                put_iv,

            "change":
                put_change,

            "change_percent":
                put_change_percent,

            "last_price":
                put_last_price,

            "trade_time":
                put_trade_time,
        }

        records.append(
            put_record
        )

    return records


# ============================================================
# 1限月取得
# ============================================================

def get_contract_data(
    contract,
    url,
    collected_at,
):

    html = fetch_html(
        url
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # --------------------------------------------------------
    # TITLE確認
    # --------------------------------------------------------

    title = clean_text(
        soup.title.get_text()
        if soup.title
        else ""
    )

    print(
        f"[TITLE] "
        f"{title}"
    )

    # --------------------------------------------------------
    # QRI更新時刻
    # --------------------------------------------------------

    qri_update_time = (
        get_qri_update_time(
            soup
        )
    )

    print(
        f"[QRI UPDATE] "
        f"{qri_update_time}"
    )

    # --------------------------------------------------------
    # 取引日
    # --------------------------------------------------------

    (
        trading_day,
        last_trading_day,
    ) = get_contract_info(
        soup
    )

    print(
        f"[TRADING DAY] "
        f"{trading_day}"
    )

    print(
        f"[LAST TRADING DAY] "
        f"{last_trading_day}"
    )

    # --------------------------------------------------------
    # オプションデータ
    # --------------------------------------------------------

    records = parse_option_table(
        soup=soup,
        contract=contract,
        qri_update_time=qri_update_time,
        collected_at=collected_at,
        trading_day=trading_day,
        last_trading_day=last_trading_day,
    )

    print(
        f"[OK] "
        f"{contract} "
        f"records={len(records)}"
    )

    return (
        qri_update_time,
        records,
    )


# ============================================================
# latest.csv読み込み
# ============================================================

def load_latest():

    if not LATEST_FILE.exists():

        return []

    try:

        with open(
            LATEST_FILE,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:

            return list(
                csv.DictReader(f)
            )

    except Exception as e:

        print(
            f"[WARNING] "
            f"Could not read latest.csv: "
            f"{e}"
        )

        return []


# ============================================================
# latest.csv保存
# ============================================================

def save_latest(records):

    if not records:

        raise RuntimeError(
            "Cannot save empty latest.csv"
        )

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

        writer.writerows(
            records
        )

    print(
        f"[LATEST] "
        f"{LATEST_FILE} "
        f"records={len(records)}"
    )


# ============================================================
# 前回のQRI更新時刻
# ============================================================

def get_previous_update_times(
    records
):

    result = {}

    for row in records:

        contract = row.get(
            "contract"
        )

        update_time = row.get(
            "qri_update_time"
        )

        if contract and update_time:

            result[
                contract
            ] = update_time

    return result


# ============================================================
# 履歴ファイル
# ============================================================

def get_history_file(
    trading_day
):

    match = re.search(
        r"(\d{4})/(\d{2})/(\d{2})",
        trading_day,
    )

    if match:

        date_string = (
            f"{match.group(1)}-"
            f"{match.group(2)}-"
            f"{match.group(3)}"
        )

    else:

        date_string = (
            datetime.now(
                JST
            ).strftime(
                "%Y-%m-%d"
            )
        )

    return (
        HISTORY_DIR /
        f"{date_string}.csv"
    )


# ============================================================
# 履歴保存
# ============================================================

def save_history(
    records,
    trading_day,
):

    if not records:

        return

    history_file = (
        get_history_file(
            trading_day
        )
    )

    # --------------------------------------------------------
    # 既存ファイルから重複チェック
    # --------------------------------------------------------

    existing_keys = set()

    if history_file.exists():

        try:

            with open(
                history_file,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as f:

                reader = csv.DictReader(
                    f
                )

                for row in reader:

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
                        row.get(
                            "qri_update_time",
                            ""
                        ),
                    )

                    existing_keys.add(
                        key
                    )

        except Exception as e:

            print(
                f"[WARNING] "
                f"Could not read history: "
                f"{e}"
            )

    # --------------------------------------------------------
    # 新規レコードのみ
    # --------------------------------------------------------

    new_records = []

    for record in records:

        key = (
            record[
                "contract"
            ],
            record[
                "option_type"
            ],
            str(
                record[
                    "strike"
                ]
            ),
            record[
                "qri_update_time"
            ],
        )

        if key not in existing_keys:

            new_records.append(
                record
            )

    if not new_records:

        print(
            "[HISTORY] "
            "No new records."
        )

        return

    # --------------------------------------------------------
    # Append
    # --------------------------------------------------------

    file_exists = (
        history_file.exists()
    )

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

        writer.writerows(
            new_records
        )

    print(
        f"[HISTORY] "
        f"{history_file} "
        f"+{len(new_records)} records"
    )


# ============================================================
# メイン
# ============================================================

def main():

    collected_at = (
        datetime.now(
            timezone.utc
        )
        .astimezone(
            JST
        )
        .isoformat(
            timespec="seconds"
        )
    )

    print()
    print(
        "========================================"
    )
    print(
        "JPX OPTION DATA"
    )
    print(
        "========================================"
    )
    print(
        f"Collected at: "
        f"{collected_at}"
    )
    print(
        "========================================"
    )

    # ========================================================
    # 前回データ
    # ========================================================

    previous_records = (
        load_latest()
    )

    previous_update_times = (
        get_previous_update_times(
            previous_records
        )
    )

    # ========================================================
    # 全限月取得
    # ========================================================

    all_records = []

    contract_update_times = {}

    for contract, url in (
        CONTRACTS.items()
    ):

        try:

            (
                qri_update_time,
                records,
            ) = get_contract_data(
                contract,
                url,
                collected_at,
            )

            contract_update_times[
                contract
            ] = qri_update_time

            all_records.extend(
                records
            )

        except Exception as e:

            print(
                f"[ERROR] "
                f"{contract}: "
                f"{e}"
            )

    # ========================================================
    # データ取得失敗
    # ========================================================

    if not all_records:

        raise RuntimeError(
            "No option data collected."
        )

    # ========================================================
    # 更新確認
    # ========================================================

    new_records = []

    for contract in (
        CONTRACTS.keys()
    ):

        current_time = (
            contract_update_times.get(
                contract
            )
        )

        previous_time = (
            previous_update_times.get(
                contract
            )
        )

        print()
        print(
            "----------------------------------------"
        )

        print(
            f"[CHECK] "
            f"{contract}"
        )

        print(
            f"Previous: "
            f"{previous_time}"
        )

        print(
            f"Current : "
            f"{current_time}"
        )

        # ----------------------------------------------------
        # 初回または更新
        # ----------------------------------------------------

        if (
            current_time
            and
            current_time != previous_time
        ):

            print(
                f"[NEW] "
                f"{contract}"
            )

            for record in all_records:

                if (
                    record[
                        "contract"
                    ]
                    == contract
                ):

                    new_records.append(
                        record
                    )

        else:

            print(
                f"[NO CHANGE] "
                f"{contract}"
            )

    # ========================================================
    # latest.csv
    #
    # 常に最新状態を保存
    # ========================================================

    save_latest(
        all_records
    )

    # ========================================================
    # history
    #
    # QRI更新時刻が変わった場合だけ保存
    # ========================================================

    if new_records:

        # ----------------------------------------------------
        # 取引日
        # ----------------------------------------------------

        trading_day = (
            new_records[0].get(
                "trading_day",
                ""
            )
        )

        save_history(
            new_records,
            trading_day,
        )

        print()
        print(
            "========================================"
        )

        print(
            f"NEW DATA SAVED: "
            f"{len(new_records)} records"
        )

        print(
            "========================================"
        )

    else:

        print()
        print(
            "========================================"
        )

        print(
            "NO NEW QRI DATA"
        )

        print(
            "========================================"
        )

    # ========================================================
    # サマリー
    # ========================================================

    print()
    print(
        "========================================"
    )
    print(
        "SUMMARY"
    )
    print(
        "========================================"
    )

    print(
        f"Total records: "
        f"{len(all_records)}"
    )

    print(
        f"New records: "
        f"{len(new_records)}"
    )

    print(
        f"Latest file: "
        f"{LATEST_FILE}"
    )

    print(
        "========================================"
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    main()
