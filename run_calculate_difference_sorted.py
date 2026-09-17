from datetime import datetime

import calculate_difference as calc


# ============================================================
# Sort Discord notifications by actual trade time
# ============================================================
#
# calculate_difference.py originally prioritizes alert importance
# inside get_alert_candidates().
# This wrapper keeps that detection logic unchanged, but replaces
# the final notification order with trade_time ascending.
#
# Records without a trade_time are sent after records with one.
# ============================================================


def trade_time_key(value):
    if not value:
        return (1, datetime.max)

    text = str(value).strip()

    for fmt in (
        "%m/%d %H:%M:%S",
        "%m/%d %H:%M",
    ):
        try:
            return (0, datetime.strptime(text, fmt))
        except ValueError:
            pass

    return (1, datetime.max)


_original_get_alert_candidates = calc.get_alert_candidates


def get_alert_candidates_sorted(differences):
    candidates = _original_get_alert_candidates(differences)

    candidates.sort(
        key=lambda row: trade_time_key(
            row.get("trade_time", "")
        )
    )

    print()
    print("========================================")
    print("FINAL DISCORD ALERT ORDER")
    print("========================================")

    for index, row in enumerate(candidates, start=1):
        print(
            f"[ORDER {index}] "
            f"{row.get('trade_time', '')} "
            f"{row.get('contract', '')} "
            f"{row.get('option_type', '')} "
            f"{row.get('strike', '')}"
        )

    return candidates


# Replace only the candidate-ordering function.
# The existing detection, channel selection, message creation,
# Discord sending, duplicate handling, and thresholds remain unchanged.
calc.get_alert_candidates = get_alert_candidates_sorted


if __name__ == "__main__":
    calc.main()
