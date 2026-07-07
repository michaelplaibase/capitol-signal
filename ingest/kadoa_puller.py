"""Kadoa congress trading monitor puller.

Fetches trade records from the Kadoa public dataset (a JSON file hosted on
GitHub) and maps them to the normalized record shape consumed by
core.db.upsert_trades. Signal-only: this module never places or prepares any
brokerage order.
"""

import json
import sys

import requests

from core.normalize import (
    build_dedupe_key,
    normalize_party,
    normalize_side,
    to_int,
    to_iso_date,
)

SOURCE = "kadoa"
KADOA_URL = (
    "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/"
    "main/public/data/trades.json"
)


def _extract_list(obj):
    """Return the list of records from a parsed JSON payload.

    The payload may be a plain list or an object carrying the records under a
    "trades" or "data" key.
    """
    if isinstance(obj, dict):
        if isinstance(obj.get("trades"), list):
            return obj["trades"]
        if isinstance(obj.get("data"), list):
            return obj["data"]
        return []
    if isinstance(obj, list):
        return obj
    return []


def pull_live(url=KADOA_URL, timeout=30):
    """GET the Kadoa dataset and return the list of raw records.

    Handles a response that is either a list or an object with a "trades" or
    "data" key.
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return _extract_list(resp.json())


def pull_cache(path):
    """Load records from a local JSON cache file."""
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)
    return _extract_list(obj)


def pull(cfg=None):
    """Pull live records, returning [] on any failure.

    On exception print a warning to stderr and return an empty list.
    """
    try:
        return pull_live(KADOA_URL)
    except Exception as exc:
        print(f"warning: kadoa pull_live failed: {exc}", file=sys.stderr)
        return []


def newest_filing_date(records):
    """Return the max mapped filing_date ISO string, or None (gate G2)."""
    dates = []
    for raw in records:
        try:
            mapped = map_record(raw)
        except Exception:
            continue
        fd = mapped.get("filing_date")
        if fd:
            dates.append(fd)
    if not dates:
        return None
    return max(dates)


def map_record(raw):
    """Map a Kadoa raw record to the normalized record shape."""
    sid = raw["id"]
    chamber = raw.get("chamber") or (
        "oge" if raw.get("branch") == "executive" else None
    )
    politician = raw.get("filer_name") or raw.get("owner") or "Unknown"
    return {
        "dedupe_key": build_dedupe_key(SOURCE, sid),
        "source": SOURCE,
        "chamber": chamber,
        "politician": politician,
        "party": normalize_party(raw.get("party")),
        "state": raw.get("state"),
        "ticker": raw.get("ticker"),
        "asset_name": raw.get("asset_name"),
        "asset_type": raw.get("asset_type"),
        "side": normalize_side("kadoa", raw.get("transaction_type")),
        "trade_date": to_iso_date(raw.get("transaction_date")),
        "filing_date": to_iso_date(raw.get("filing_date")),
        "amount_min": to_int(raw.get("amount_range_low")),
        "amount_max": to_int(raw.get("amount_range_high")),
        "price": None,
        "doc_url": raw.get("doc_url"),
        "raw": json.dumps(raw, ensure_ascii=False),
    }
