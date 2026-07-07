"""Tests for the db upsert plus diff idempotency (gate G3).

Uses an in-memory SQLite database. Inserting two fresh records yields two
events; inserting the same two again yields zero. No network.

Runnable via: python -m pytest tests/ and python tests/test_db_diff.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import db
from core.diff import detect_new_trades


def _make_record(dedupe_key, politician, side):
    """Build a minimal but valid normalized record for persistence tests."""
    return {
        "dedupe_key": dedupe_key,
        "source": "capitol-api",
        "chamber": "house",
        "politician": politician,
        "party": "D",
        "state": "CA",
        "ticker": "NVDA",
        "asset_name": "NVIDIA Corporation",
        "asset_type": "Stock",
        "side": side,
        "trade_date": "2026-06-30",
        "filing_date": "2026-07-06",
        "amount_min": 1001,
        "amount_max": 15000,
        "price": 123.45,
        "doc_url": "https://example.gov/filing.pdf",
        "raw": "{}",
    }


def test_detect_new_trades_idempotent():
    conn = db.connect(":memory:")
    db.init_db(conn)

    records = [
        _make_record("capitol-api:1", "Nancy Pelosi", "buy"),
        _make_record("capitol-api:2", "Tommy Tuberville", "sell"),
    ]

    # First pass: both records are new, so two events.
    first = detect_new_trades(conn, records)
    assert len(first) == 2
    assert db.count_rows(conn) == 2

    # Second pass with the same two records: no new events (idempotency).
    second = detect_new_trades(conn, records)
    assert len(second) == 0
    assert db.count_rows(conn) == 2

    conn.close()


def _run():
    test_detect_new_trades_idempotent()
    print("test_db_diff: all tests passed")


if __name__ == "__main__":
    _run()
