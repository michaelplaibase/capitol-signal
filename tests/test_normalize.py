"""Tests for core.normalize helpers.

No network. Runnable via: python -m pytest tests/ and python tests/test_normalize.py
"""

import os
import sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.normalize import (
    is_future_dated,
    last_name,
    normalize_party,
    normalize_side,
    to_iso_date,
)


def test_normalize_side_capitol_api():
    assert normalize_side("capitol-api", "buy") == "buy"
    assert normalize_side("capitol-api", "sell") == "sell"
    assert normalize_side("capitol-api", "exchange") == "exchange"
    # Case-insensitive matching.
    assert normalize_side("capitol-api", "BUY") == "buy"
    # Unrecognized value falls back to other.
    assert normalize_side("capitol-api", "whatever") == "other"


def test_normalize_side_kadoa():
    assert normalize_side("kadoa", "Purchase") == "buy"
    assert normalize_side("kadoa", "Sale (Full)") == "sell"
    assert normalize_side("kadoa", "Sale (Partial)") == "sell"
    assert normalize_side("kadoa", "Exchange") == "exchange"
    # Case-insensitive matching.
    assert normalize_side("kadoa", "sale (partial)") == "sell"
    # Unrecognized and None fall back to other.
    assert normalize_side("kadoa", "gift") == "other"
    assert normalize_side("kadoa", None) == "other"


def test_normalize_party():
    assert normalize_party("Republican") == "R"
    assert normalize_party("Democratic") == "D"
    assert normalize_party("Democrat") == "D"
    assert normalize_party("Independent") == "I"
    # Existing short codes pass through.
    assert normalize_party("R") == "R"
    assert normalize_party("D") == "D"
    assert normalize_party("I") == "I"
    # None and empty string map to None.
    assert normalize_party(None) is None
    assert normalize_party("") is None


def test_to_iso_date_good_and_bad():
    # Good values keep only the first ten characters.
    assert to_iso_date("2026-06-30") == "2026-06-30"
    assert to_iso_date("2026-06-30T12:34:56Z") == "2026-06-30"
    # Bad values return None.
    assert to_iso_date(None) is None
    assert to_iso_date("not-a-date") is None
    assert to_iso_date("2026-13-01") is None
    assert to_iso_date("2026-06") is None


def test_is_future_dated_boundary():
    today = date(2026, 7, 7)
    tomorrow = (today + timedelta(days=1)).isoformat()
    day_after = (today + timedelta(days=2)).isoformat()
    # today+1 is not considered future dated.
    assert is_future_dated(tomorrow, today) is False
    # today+2 is future dated.
    assert is_future_dated(day_after, today) is True
    # today itself is not future dated.
    assert is_future_dated(today.isoformat(), today) is False
    # None and invalid input are not future dated.
    assert is_future_dated(None, today) is False
    assert is_future_dated("bad-date", today) is False


def test_last_name():
    assert last_name("Robert B. Aderholt") == "Aderholt"
    assert last_name("Pelosi") == "Pelosi"
    assert last_name("") == ""
    assert last_name(None) == ""


def _run():
    test_normalize_side_capitol_api()
    test_normalize_side_kadoa()
    test_normalize_party()
    test_to_iso_date_good_and_bad()
    test_is_future_dated_boundary()
    test_last_name()
    print("test_normalize: all tests passed")


if __name__ == "__main__":
    _run()
