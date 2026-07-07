"""Tests for the source specific map_record functions.

Feeds one inline capitol-api record and one inline kadoa record through the
mappers and asserts the normalized fields. No network.

Runnable via: python -m pytest tests/ and python tests/test_mappers.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ingest import capitol_api_puller
from ingest import kadoa_puller


CAPITOL_RAW = {
    "id": "abc123",
    "person": {
        "name": "Nancy Pelosi",
        "party": "Democratic",
        "state": "CA",
    },
    "asset": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "typeDescription": "Stock",
    },
    "transaction": {
        "category": "buy",
        "tradeDate": "2026-06-30",
        "filingDate": "2026-07-06",
        "amountMin": "1,001",
        "amountMax": "15,000",
        "price": "123.45",
    },
    "filing": {
        "pdfUrl": "https://example.gov/filing/abc123.pdf",
    },
}


KADOA_RAW = {
    "id": "kad-42",
    "chamber": "senate",
    "filer_name": "Tommy Tuberville",
    "party": "Republican",
    "state": "AL",
    "ticker": "AAPL",
    "asset_name": "Apple Inc.",
    "asset_type": "Stock",
    "transaction_type": "Sale (Partial)",
    "transaction_date": "2026-05-01",
    "filing_date": "2026-05-20",
    "amount_range_low": "50000",
    "amount_range_high": "100000",
    "doc_url": "https://example.gov/kadoa/kad-42.pdf",
}


def test_map_record_capitol_api():
    rec = capitol_api_puller.map_record(CAPITOL_RAW)
    assert rec["source"] == "capitol-api"
    assert rec["chamber"] == "house"
    assert rec["politician"] == "Nancy Pelosi"
    assert rec["party"] == "D"
    assert rec["side"] == "buy"
    assert rec["ticker"] == "NVDA"
    assert rec["amount_min"] == 1001
    assert rec["amount_max"] == 15000
    assert rec["price"] == 123.45
    assert rec["doc_url"] == "https://example.gov/filing/abc123.pdf"
    assert rec["dedupe_key"] == "capitol-api:abc123"


def test_map_record_kadoa():
    rec = kadoa_puller.map_record(KADOA_RAW)
    assert rec["source"] == "kadoa"
    assert rec["chamber"] == "senate"
    assert rec["politician"] == "Tommy Tuberville"
    assert rec["party"] == "R"
    assert rec["side"] == "sell"
    assert rec["ticker"] == "AAPL"
    assert rec["amount_min"] == 50000
    assert rec["doc_url"] == "https://example.gov/kadoa/kad-42.pdf"
    assert rec["dedupe_key"] == "kadoa:kad-42"


def _run():
    test_map_record_capitol_api()
    test_map_record_kadoa()
    print("test_mappers: all tests passed")


if __name__ == "__main__":
    _run()
