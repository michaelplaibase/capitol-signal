"""Capitol Signal POC orchestrator.

Pulls congressional trade records from the configured sources, maps them to the
normalized record shape, filters out future dated trades, detects newly seen
trades against the local SQLite store, and emits Danish notifications for them.

Signal-only system: this orchestrator reads data and sends notifications only.
It never places, prepares, or simulates any brokerage order.
"""

import os
import sys
from datetime import date


# Windows consoles default to the cp1252 code page, which cannot encode the
# emoji used in the Danish notifications. Reconfigure stdout and stderr to
# UTF-8 so printing never crashes. errors="replace" keeps output flowing even
# on limited code pages or redirected streams.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


# Insert the repo root on sys.path so "from core..." style imports resolve
# regardless of the current working directory when main.py is invoked.
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.config import load_config
from core.db import connect, init_db
from core.diff import detect_new_trades
from core.normalize import is_future_dated
from ingest import capitol_api_puller
from ingest import kadoa_puller
from notify.slack import notify


DEFAULT_DB = os.path.join(ROOT, "signal.db")

# Map a source name to the puller module that handles it.
_PULLERS = {
    "capitol-api": capitol_api_puller,
    "kadoa": kadoa_puller,
}


def run(cfg=None, db_path=DEFAULT_DB, sources=("capitol-api", "kadoa"), today=None):
    """Run one full ingest, dedupe, and notify cycle.

    Steps:
      1. Load config and open the database (creating the schema if needed).
      2. For each source, pull raw records and map them to normalized records,
         counting per-source pull sizes and mapping errors.
      3. Drop future dated trades (based on trade_date and today).
      4. Detect newly inserted trades and emit notifications for them.
      5. Print a summary block and return a stats dict.
    """
    if cfg is None:
        cfg = load_config()
    conn = connect(db_path)
    init_db(conn)
    if today is None:
        today = date.today()

    pulled = {}
    mapped = []
    map_errors = 0

    for source in sources:
        puller = _PULLERS.get(source)
        if puller is None:
            pulled[source] = 0
            continue
        raw_list = puller.pull(cfg)
        pulled[source] = len(raw_list)
        for raw in raw_list:
            try:
                mapped.append(puller.map_record(raw))
            except Exception:
                map_errors += 1

    # Flag future dated records without doing list membership checks on large
    # lists. kept preserves order and excludes anything flagged as future.
    kept = []
    future_count = 0
    for record in mapped:
        if is_future_dated(record.get("trade_date"), today):
            future_count += 1
        else:
            kept.append(record)

    new_events = detect_new_trades(conn, kept)
    emitted = notify(new_events, cfg)

    print("Capitol Signal run summary")
    for source in sources:
        print(f"  pulled[{source}] = {pulled.get(source, 0)}")
    print(f"  map_errors = {map_errors}")
    print(f"  future_filtered = {future_count}")
    print(f"  new_events = {len(new_events)}")
    print(f"  emitted = {len(emitted)}")

    return dict(
        pulled=pulled,
        mapped=len(mapped),
        map_errors=map_errors,
        future_filtered=future_count,
        new_events=len(new_events),
        emitted=len(emitted),
    )


if __name__ == "__main__":
    run()
