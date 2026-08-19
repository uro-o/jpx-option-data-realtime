import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta


# ============================================================
# 設定
# ============================================================

BASE_URL = "https://svc.qri.jp"

URLS = {
    "2026-09": "https://svc.qri.jp/jpx/nkopm/",
    "2026-10": "https://svc.qri.jp/jpx/nkopm/1",
    "2026-12": "https://svc.qri.jp/jpx/nkopm/2",
}


# ============================================================
# 日本時間
# ============================================================

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

    "Accept-Encoding": (
        "gzip, deflate, br"
    ),

    "Connection": "keep-alive",

    "Upgrade-Insecure-Requests": "1",
})


# ============================================================
# デバッグ表示
# ============================================================

def print_response_debug(response):

    print()
    print("========================================")
    print("HTTP RESPONSE DEBUG")
    print("========================================")

    print(
        f"Status Code : {response.status_code}"
    )

    print(
        f"URL         : {response.url}"
    )

    print(
        f"Encoding    : {response.encoding}"
    )

    print(
        f"Content-Type: "
        f"{response.headers.get('Content-Type')}"
    )

    print(
        f"Server      : "
        f"{response.headers.get('Server')}"
    )

    print(
        f"Set-Cookie  : "
        f"{response.headers.get('Set-Cookie')}"
    )

    print(
        f"Location    : "
        f"{response.headers.get('Location')}"
    )

    print()
    print("Response Headers:")

    for key, value in response.headers.items():

        print(
            f"  {key}: {value}"
        )

    print()
    print("Response Body (first 3000 chars):")
    print("----------------------------------------")

    print(
        response.text[:3000]
    )

    print("----------------------------------------")
    print()


# ============================================================
# QRIトップページアクセス
# ============================================================

def initialize_session():

    print()
    print("========================================")
    print("INITIAL SESSION")
    print("========================================")

    print(
        f"GET {BASE_URL}"
    )

    try:

        response = session.get(
            BASE_URL,
            timeout=30,
            allow_redirects=True,
        )

        print(
            f"Status: {response.status_code}"
        )

        print(
            f"Final URL: {response.url}"
        )

        print(
            f"Cookies: {session.cookies.get_dict()}"
        )

        print()

        if response.status_code != 200:

            print_response_debug(
                response
            )

        else:

            print(
                "Initial access OK."
            )

    except Exception as e:

        print(
            "[INITIAL ACCESS ERROR]"
        )

        print(
            repr(e)
        )


# ============================================================
# QRIページ取得
# ============================================================

def fetch_page(
    contract,
    url,
):

    print()
    print("========================================")
    print(
        f"FETCH {contract}"
    )
    print("========================================")

    print(
        f"URL: {url}"
    )

    print()
    print("Request Headers:")

    for key, value in session.headers.items():

        print(
            f"  {key}: {value}"
        )

    print()
    print(
        f"Cookies before request:"
    )

    print(
        session.cookies.get_dict()
    )

    try:

        response = session.get(

            url,

            headers={
                "Referer":
                    "https://svc.qri.jp/jpx/",
            },

            timeout=30,

            allow_redirects=True,
        )

    except Exception as e:

        print()
        print(
            "[REQUEST EXCEPTION]"
        )

        print(
            repr(e)
        )

        return None

    print_response_debug(
        response
    )

    print(
        "Cookies after request:"
    )

    print(
        session.cookies.get_dict()
    )

    return response


# ============================================================
# HTML解析テスト
# ============================================================

def test_html(
    response,
):

    if response is None:

        return

    if response.status_code != 200:

        print(
            "HTML parsing skipped "
            "because HTTP status is not 200."
        )

        return

    print()
    print("========================================")
    print("HTML PARSE TEST")
    print("========================================")

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    title = soup.find(
        "title"
    )

    if title:

        print(
            "TITLE:"
        )

        print(
            title.get_text(
                strip=True
            )
        )

    else:

        print(
            "TITLE: NOT FOUND"
        )

    update_time = soup.select_one(
        ".update-time dd"
    )

    if update_time:

        print()
        print(
            "QRI UPDATE TIME:"
        )

        print(
            update_time.get_text(
                " ",
                strip=True,
            )
        )

    else:

        print()
        print(
            "QRI UPDATE TIME: NOT FOUND"
        )

    price_table = soup.select_one(
        "table.price-table"
    )

    if price_table:

        print()
        print(
            "PRICE TABLE: FOUND"
        )

    else:

        print()
        print(
            "PRICE TABLE: NOT FOUND"
        )

    rows = soup.select(
        "tbody.price-info-scroll tr"
    )

    print()
    print(
        f"TABLE ROWS: {len(rows)}"
    )


# ============================================================
# メイン
# ============================================================

def main():

    collected_at = (
        datetime.now(
            timezone.utc
        )
        .astimezone(JST)
        .isoformat(
            timespec="seconds"
        )
    )

    print()
    print("========================================")
    print("JPX OPTION DATA DEBUG")
    print("========================================")

    print(
        f"Collected at: {collected_at}"
    )

    print(
        "========================================"
    )

    # --------------------------------------------------------
    # セッション初期化
    # --------------------------------------------------------

    initialize_session()

    # --------------------------------------------------------
    # 各限月をテスト
    # --------------------------------------------------------

    for contract, url in URLS.items():

        response = fetch_page(
            contract,
            url,
        )

        test_html(
            response
        )

    print()
    print("========================================")
    print("DEBUG COMPLETED")
    print("========================================")


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    main()
