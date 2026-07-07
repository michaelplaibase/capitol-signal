"""Capitol Trades API puller.

Fetches congressional trade records from the local Capitol API service (or a
cached JSON file) and maps them into the normalized record shape consumed by
db.upsert_trades. This is a signal-only ingestion module: it reads data only and
never places, prepares, or simulates any brokerage order.
"""

import json
import sys

import requests

from core.normalize import (
    build_dedupe_key,
    normalize_party,
    normalize_side,
    to_float,
    to_int,
    to_iso_date,
)

SOURCE = "capitol-api"


def status(base_url, timeout=10):
    """GET the API status endpoint and return the parsed JSON object."""
    resp = requests.get(base_url + "/api/status", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def pull_live(base_url, recent=None, timeout=30):
    """GET the trades endpoint and return the list of raw trade records.

    The response may be a bare list or an object with a "trades" key. When
    recent is given, request only the most recent N records via ?recent=N.
    """
    url = base_url + "/api/trades"
    params = {}
    if recent is not None:
        params["recent"] = recent
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return data.get("trades") or []
    return data


def pull_cache(path):
    """Load trades from a cached JSON file (list or object with "trades")."""
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)
    if isinstance(obj, dict):
        return obj.get("trades") or []
    return obj


def pull(cfg):
    """Pull raw records, preferring the live API and falling back to cache.

    On any exception from the live pull, use the configured cache file when set,
    otherwise print a warning to stderr and return an empty list.
    """
    try:
        return pull_live(cfg.capitol_api_url)
    except Exception as exc:
        if cfg.capitol_api_cache:
            try:
                return pull_cache(cfg.capitol_api_cache)
            except Exception as cache_exc:
                print(
                    "warning: capitol-api live pull failed and cache read failed: %s"
                    % cache_exc,
                    file=sys.stderr,
                )
                return []
        print(
            "warning: capitol-api live pull failed and no cache set: %s" % exc,
            file=sys.stderr,
        )
        return []


def map_record(raw):
    """Map a raw Capitol API record into a normalized record dict."""
    sid = raw["id"]
    person = raw.get("person") or {}
    asset = raw.get("asset") or {}
    tx = raw.get("transaction") or {}
    filing = raw.get("filing") or {}

    politician = person.get("name") or (
        person.get("firstName", "") + " " + person.get("lastName", "")
    ).strip()

    return {
        "dedupe_key": build_dedupe_key(SOURCE, sid),
        "source": SOURCE,
        "chamber": "house",
        "politician": politician,
        "party": normalize_party(person.get("party")),
        "state": person.get("state"),
        "ticker": asset.get("ticker"),
        "asset_name": asset.get("name"),
        "asset_type": asset.get("typeDescription") or asset.get("type"),
        "side": normalize_side("capitol-api", tx.get("category")),
        "trade_date": to_iso_date(tx.get("tradeDate")),
        "filing_date": to_iso_date(tx.get("filingDate")),
        "amount_min": to_int(tx.get("amountMin")),
        "amount_max": to_int(tx.get("amountMax")),
        "price": to_float(tx.get("price")),
        "doc_url": filing.get("pdfUrl"),
        "raw": json.dumps(raw, ensure_ascii=False),
    }
