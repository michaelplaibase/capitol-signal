"""Tests for notify.slack formatting, filtering, and dry-run emission (gate G4).

Builds synthetic events, checks the exact Danish message template, verifies the
filter predicates, and confirms notify() in dry_run mode returns exactly one
message for exactly one passing event. No network.

Runnable via: python -m pytest tests/ and python tests/test_notify.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.config import Config
from notify.slack import format_message, notify, passes_filters


def _make_cfg(dry_run=True, min_amount=0, require_ticker=True, watchlist=None):
    """Build a Config carrying only the fields the notify path reads."""
    return Config(
        slack_webhook_url=None,
        dry_run=dry_run,
        min_amount=min_amount,
        require_ticker=require_ticker,
        watchlist=watchlist if watchlist is not None else [],
        capitol_api_url="http://localhost:3000",
        capitol_api_cache=None,
    )


def _buy_event():
    """A synthetic buy event with a ticker mirroring the reference example."""
    return {
        "side": "buy",
        "politician": "Nancy Pelosi",
        "party": "D",
        "state": "CA",
        "ticker": "NVDA",
        "amount_min": 1001,
        "amount_max": 15000,
        "trade_date": "2026-06-30",
        "filing_date": "2026-07-06",
        "chamber": "house",
        "doc_url": "https://example.gov/filing.pdf",
    }


def test_format_message():
    msg = format_message(_buy_event())
    # Starts with the green circle emoji and the Danish buy label.
    assert msg.startswith("🟢 KØB")
    # Danish chamber label for the house.
    assert "Hus" in msg
    # Danish date formatting dd-mm-yyyy for both trade and filing dates.
    assert "30-06-2026" in msg
    assert "06-07-2026" in msg
    # Amount range with Danish thousands separator.
    assert "1.001-15.000 USD" in msg


def test_passes_filters_require_ticker():
    cfg = _make_cfg(require_ticker=True)
    with_ticker = _buy_event()
    without_ticker = dict(with_ticker)
    without_ticker["ticker"] = None
    assert passes_filters(with_ticker, cfg) is True
    assert passes_filters(without_ticker, cfg) is False


def test_passes_filters_min_amount():
    event = _buy_event()  # amount_min == 1001
    # A threshold above the event amount drops it.
    assert passes_filters(event, _make_cfg(min_amount=5000)) is False
    # A threshold at or below the event amount keeps it.
    assert passes_filters(event, _make_cfg(min_amount=1000)) is True


def test_passes_filters_watchlist():
    event = _buy_event()  # last name "Pelosi"
    # Watchlist containing the last name keeps the event.
    assert passes_filters(event, _make_cfg(watchlist=["pelosi"])) is True
    # Watchlist that excludes the last name drops the event.
    assert passes_filters(event, _make_cfg(watchlist=["tuberville"])) is False


def test_notify_dry_run_single_event():
    cfg = _make_cfg(dry_run=True)
    emitted = notify([_buy_event()], cfg)
    # Exactly one passing event yields exactly one emitted message (gate G4).
    assert len(emitted) == 1
    assert emitted[0].startswith("🟢 KØB")


def _run():
    test_format_message()
    test_passes_filters_require_ticker()
    test_passes_filters_min_amount()
    test_passes_filters_watchlist()
    test_notify_dry_run_single_event()
    print("test_notify: all tests passed")


if __name__ == "__main__":
    _run()
