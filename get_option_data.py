import csv
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# Configuration
# ============================================================

CONTRACTS = {
    "2026-09": "https://svc.qri.jp/jpx/nkopm/",
    "2026-10": "https://svc.qri.jp/jpx/nkopm/1",
    "2026-12": "https://svc.qri.jp/jpx/nkopm/2",
}

DATA_DIR = Path("data")
HISTORY_DIR = DATA_DIR / "history"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

HISTORY_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LATEST_FILE = DATA_DIR / "latest.csv"

JST = timezone(
    timedelta(hours=9)
)


# ============================================================
# CSV columns
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
# HTTP Session
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 "
        "Safari/537.36"
    ),

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,"
        "image/apng,*/*;q=0.8"
    ),

    "Accept-Language": (
        "ja-JP,ja;q=0.9,"
        "en-US;q=0.8,en;q=0.7"
    ),

    "Accept-Encoding": (
        "gzip, deflate, br"
    ),

    "Connection": "keep-alive",

    "Upgrade-Insecure-Requests": "1",
})


# ============================================================
# Text cleanup
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    text = text.replace(
        "\xa0",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# Number conversion
# ============================================================

def to_number(text):

    text = clean_text(text)

    if not text:
        return None

    if text in (
        "-",
        "--",
        "－",
        "―",
    ):
        return None

    text = text.replace(
        ",",
        ""
    )

    text = text.replace(
        "%",
        ""
    )

    try:

        value = float(text)

        if value.is_integer():

            return int(value)

        return value

    except ValueError:

        return None


# ============================================================
# Extract first numeric value from text
# ============================================================

def extract_number(text):

    text = clean_text(text)

    if not text:
        return None

    match = re.search(
        r"-?[\d,]+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    return to_number(
        match.group(0)
    )


# ============================================================
# Price + time
#
# Example:
#
# 1
# 08/18 22:07
#
# ============================================================

def parse_price_and_time(
    cell
):

    if cell is None:

        return (
            None,
            None,
        )

    text = clean_text(
        cell.get_text(
            " ",
            strip=True,
        )
    )

    if not text:

        return (
            None,
            None,
        )

    lines = [
        clean_text(x)
        for x in cell.stripped_strings
    ]

    lines = [
        x for x in lines
        if x
    ]

    # --------------------------------------------------------
    # Price
    # --------------------------------------------------------

    price = None

    if lines:

        price = extract_number(
            lines[0]
        )

    # --------------------------------------------------------
    # Trade time
    # --------------------------------------------------------

    trade_time = None

    for line in lines[1:]:

        if re.search(
            r"\d{1,2}/\d{1,2}",
            line,
        ):

            trade_time = line

            break

    return (
        price,
        trade_time,
    )


# ============================================================
# Two values
#
# Example:
#
# 38.20% -
#
# ============================================================

def parse_two_values(
    cell
):

    if cell is None:

        return (
            None,
            None,
        )

    lines = [
        clean_text(x)
        for x in cell.stripped_strings
    ]

    lines = [
        x for x in lines
        if x
    ]

    first = (
        extract_number(lines[0])
        if len(lines) >= 1
        else None
    )

    second = (
        extract_number(lines[1])
        if len(lines) >= 2
        else None
    )

    return (
        first,
        second,
    )


# ============================================================
# Quote parser
#
# Example:
#
# 1 (77)
# -
#
# or:
#
# 1 (77)
# - (-)
#
# ============================================================

def parse_quote(
    cell
):

    if cell is None:

        return (
            None,
            None,
            None,
            None,
        )

    lines = [
        clean_text(x)
        for x in cell.stripped_strings
    ]

    lines = [
        x for x in lines
        if x
    ]

    ask_price = None
    ask_quantity = None

    bid_price = None
    bid_quantity = None

    if len(lines) >= 1:

        match = re.search(
            r"(.+?)\s*\((.*?)\)",
            lines[0],
        )

        if match:

            ask_price = extract_number(
                match.group(1)
            )

            ask_quantity = extract_number(
                match.group(2)
            )

        else:

            ask_price = extract_number(
                lines[0]
            )

    if len(lines) >= 2:

        match = re.search(
            r"(.+?)\s*\((.*?)\)",
            lines[1],
        )

        if match:

            bid_price = extract_number(
                match.group(1)
            )

            bid_quantity = extract_number(
                match.group(2)
            )

        else:

            bid_price = extract_number(
                lines[1]
            )

    return (
        ask_price,
        ask_quantity,
        bid_price,
        bid_quantity,
    )


# ============================================================
# Fetch QRI HTML
#
# IMPORTANT:
# Do NOT access https://svc.qri.jp/
# Directly access option pages.
# ============================================================

def fetch_html(
    url
):

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
            # Success
            # ------------------------------------------------

            if response.status_code == 200:

                response.encoding = "utf-8"

                return response.text

            # ------------------------------------------------
            # Retryable errors
            # ------------------------------------------------

            if response.status_code in (
                429,
                500,
                502,
                503,
                504,
            ):

                last_error = (
                    f"HTTP "
                    f"{response.status_code}"
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
                        f"{wait_seconds} "
                        f"seconds"
                    )

                    time.sleep(
                        wait_seconds
                    )

                    continue

                break

            # ------------------------------------------------
            # Other HTTP errors
            # ------------------------------------------------

            response.raise_for_status()

        except requests.RequestException as e:

            last_error = e

            print(
                f"[ERROR] "
                f"attempt={attempt}: "
                f"{e}"
            )

            if attempt < 3:

                wait_seconds = (
                    attempt * 3
                )

                print(
                    f"[WAIT] "
                    f"{wait_seconds} "
                    f"seconds"
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
# QRI update time
# ============================================================

def get_qri_update_time(
    soup
):

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
# Trading day / Last trading day
# ============================================================

def get_contract_info(
    soup
):

    trading_day = ""
    last_trading_day = ""

    areas = soup.select(
        ".date-table"
    )

    for area in areas:

        dt = area.select_one(
            "dt"
        )

        dd = area.select_one(
            "dd"
        )

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
# Parse option table
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

        # ----------------------------------------------------
        # Greek rows
        # ----------------------------------------------------

        if "greek" in classes:

            continue

        cells = row.find_all(
            "td",
            recursive=False,
        )

        # ----------------------------------------------------
        # Normal option rows
        #
        # QRI currently has 17 cells.
        # Accept 17 or more for robustness.
        # ----------------------------------------------------

        if len(cells) < 17:

            continue

        # ====================================================
        # CALL
        # ====================================================

        # ----------------------------------------------------
        # 0 Settlement
        # ----------------------------------------------------

        call_settlement = extract_number(
            cells[0].get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # 1 Open Interest
        # ----------------------------------------------------

        call_oi = extract_number(
            cells[1].get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # 2 Volume
        # ----------------------------------------------------

        call_volume = extract_number(
            cells[2].get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # 3 Ask IV / Bid IV
        # ----------------------------------------------------

        (
            call_ask_iv,
            call_bid_iv,
        ) = parse_two_values(
            cells[3]
        )

        # ----------------------------------------------------
        # 4 Ask/Bid quote
        # ----------------------------------------------------

        (
            call_ask_price,
            call_ask_quantity,
            call_bid_price,
            call_bid_quantity,
        ) = parse_quote(
            cells[4]
        )

        # ----------------------------------------------------
        # 5 IV
        # ----------------------------------------------------

        call_iv = extract_number(
            cells[5].get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # 6 Change
        #
        # Example:
        #
        # 0
        # 0.00%
        # ----------------------------------------------------

        (
            call_change,
            call_change_percent,
        ) = parse_two_values(
            cells[6]
        )

        # ----------------------------------------------------
        # 7 Last price
        # ----------------------------------------------------

        (
            call_last_price,
            call_trade_time,
        ) = parse_price_and_time(
            cells[7]
        )

        # ====================================================
        # STRIKE
        #
        # Important:
        #
        # QRI HTML:
        #
        # <td class="price">
        #     90,000
        #     <button>
        #         リスク指標
        #     </button>
        # </td>
        #
        # Therefore do NOT simply convert the entire cell.
        # Extract the first number only.
        # ====================================================

        strike_text = clean_text(
            cells[8].get_text(
                " ",
                strip=True,
            )
        )

        strike_match = re.search(
            r"[\d,]+(?:\.\d+)?",
            strike_text,
        )

        if not strike_match:

            continue

        strike = to_number(
            strike_match.group(0)
        )

        if strike is None:

            continue

        # ====================================================
        # PUT
        # ====================================================

        # ----------------------------------------------------
        # 9 Last price
        # ----------------------------------------------------

        (
            put_last_price,
            put_trade_time,
        ) = parse_price_and_time(
            cells[9]
        )

        # ----------------------------------------------------
        # 10 Change
        # ----------------------------------------------------

        (
            put_change,
            put_change_percent,
        ) = parse_two_values(
            cells[10]
        )

        # ----------------------------------------------------
        # 11 IV
        # ----------------------------------------------------

        put_iv = extract_number(
            cells[11].get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # 12 Ask/Bid quote
        # ----------------------------------------------------

        (
            put_ask_price,
            put_ask_quantity,
            put_bid_price,
            put_bid_quantity,
        ) = parse_quote(
            cells[12]
        )

        # ----------------------------------------------------
        # 13 Ask IV / Bid IV
        # ----------------------------------------------------

        (
            put_ask_iv,
            put_bid_iv,
        ) = parse_two_values(
            cells[13]
        )

        # ----------------------------------------------------
        # 14 Volume
        # ----------------------------------------------------

        put_volume = extract_number(
            cells[14].get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # 15 Open Interest
        # ----------------------------------------------------

        put_oi = extract_number(
            cells[15].get_text(
                " ",
                strip=True,
            )
        )

        # ----------------------------------------------------
        # 16 Settlement
        # ----------------------------------------------------

        put_settlement = extract_number(
            cells[16].get_text(
                " ",
                strip=True,
            )
        )

        # ====================================================
        # CALL record
        # ====================================================

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

        # ====================================================
        # PUT record
        # ====================================================

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
# Get one contract
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
    # Title
    # --------------------------------------------------------

    title = clean_text(
        soup.title.get_text()
        if soup.title
        else ""
    )

    print(
        f"[TITLE] {title}"
    )

    # --------------------------------------------------------
    # QRI update time
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
    # Trading day
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
    # Option data
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
# Load latest.csv
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
# Save latest.csv
# ============================================================

def save_latest(
    records
):

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
# Get previous update times
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
# History file
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
# Save history
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

    existing_keys = set()

    # --------------------------------------------------------
    # Read existing history
    # --------------------------------------------------------

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
    # Remove duplicates
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
# Main
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
    # Load previous latest data
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
    # Get all contracts
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
    # No data
    # ========================================================

    if not all_records:

        raise RuntimeError(
            "No option data collected."
        )

    # ========================================================
    # Check QRI update times
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
            f"[CHECK] {contract}"
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
        # New QRI data
        # ----------------------------------------------------

        if (
            current_time
            and
            current_time != previous_time
        ):

            print(
                f"[NEW] {contract}"
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
    # Save latest
    # ========================================================

    save_latest(
        all_records
    )

    # ========================================================
    # Save history
    # ========================================================

    if new_records:

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
    # Summary
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
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
