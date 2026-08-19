import csv
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# Settings
# ============================================================

BASE_URL = "https://svc.qri.jp"

CONTRACTS = {
    "2026-09": "/jpx/nkopm/",
    "2026-10": "/jpx/nkopm/1",
    "2026-12": "/jpx/nkopm/2",
}

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "latest.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


# ============================================================
# Utility
# ============================================================

def clean_text(text):
    if text is None:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def to_number(text):
    """
    Convert:
        1,234      -> 1234
        35.58%     -> 35.58
        -          -> None
    """

    text = clean_text(text)

    if not text or text in ["-", "--", "－", "―"]:
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
    """
    Example:

        1 08/18 22:07

    returns:

        price = 1
        trade_time = 08/18 22:07
    """

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
    """
    Example:

        1 (77) - (-)

    returns:

        ask_price
        ask_quantity
        bid_price
        bid_quantity
    """

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
# HTTP
# ============================================================

def fetch_html(url):

    print(f"Downloading: {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    # QRI page is UTF-8
    response.encoding = response.apparent_encoding

    return response.text


# ============================================================
# Page information
# ============================================================

def get_update_time(soup):

    element = soup.select_one(".update-time dd")

    if element:
        return clean_text(
            element.get_text(" ", strip=True)
        )

    return ""


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
# Option table
# ============================================================

def parse_option_table(
    soup,
    contract,
    update_time,
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

        # Skip Greek rows
        if "greek" in row.get("class", []):
            continue

        cells = row.find_all(
            "td",
            recursive=False,
        )

        # Normal option row has 17 cells
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

        # ----------------------------------------------------
        # CALL
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Strike
        # ----------------------------------------------------

        strike = to_number(values[8])

        # ----------------------------------------------------
        # PUT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CALL record
        # ----------------------------------------------------

        records.append({
            "update_time": update_time,
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

        # ----------------------------------------------------
        # PUT record
        # ----------------------------------------------------

        records.append({
            "update_time": update_time,
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
# Get one contract
# ============================================================

def get_contract_data(contract, path):

    url = BASE_URL + path

    html = fetch_html(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    update_time = get_update_time(soup)

    trading_day, last_trading_day = (
        get_contract_info(soup)
    )

    records = parse_option_table(
        soup=soup,
        contract=contract,
        update_time=update_time,
        trading_day=trading_day,
        last_trading_day=last_trading_day,
    )

    print(
        f"{contract}: "
        f"{len(records)} records"
    )

    return records


# ============================================================
# Save CSV
# ============================================================

def save_csv(records):

    if not records:
        raise RuntimeError(
            "No option data was collected."
        )

    fieldnames = [
        "update_time",
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

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(records)

    print()
    print("========================================")
    print("QRI option data saved")
    print("========================================")
    print(f"File: {OUTPUT_FILE}")
    print(f"Records: {len(records)}")
    print("========================================")


# ============================================================
# Main
# ============================================================

def main():

    all_records = []

    for contract, path in CONTRACTS.items():

        try:

            records = get_contract_data(
                contract,
                path,
            )

            all_records.extend(records)

        except Exception as e:

            print(
                f"[ERROR] {contract}: {e}"
            )

    if not all_records:
        raise RuntimeError(
            "Failed to collect any option data."
        )

    save_csv(all_records)


if __name__ == "__main__":
    main()
