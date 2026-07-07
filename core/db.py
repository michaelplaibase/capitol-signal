"""SQLite persistence layer for normalized trade records.

Provides connection setup, schema init, idempotent upserts, and read helpers.
"""

import sqlite3
import json  # noqa: F401  (kept available for callers/parity with contract)


SCHEMA = """
    CREATE TABLE IF NOT EXISTS trades (
      dedupe_key TEXT PRIMARY KEY, source TEXT NOT NULL, chamber TEXT, politician TEXT NOT NULL,
      party TEXT, state TEXT, ticker TEXT, asset_name TEXT, asset_type TEXT, side TEXT NOT NULL,
      trade_date TEXT, filing_date TEXT, amount_min INTEGER, amount_max INTEGER, price REAL,
      doc_url TEXT, raw TEXT, first_seen_at TEXT DEFAULT (datetime('now')) );
    CREATE INDEX IF NOT EXISTS idx_trades_filing ON trades(filing_date);
    CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
"""


# The 17 columns written on insert (everything except first_seen_at), in order.
_COLUMNS = (
    "dedupe_key", "source", "chamber", "politician", "party", "state", "ticker",
    "asset_name", "asset_type", "side", "trade_date", "filing_date", "amount_min",
    "amount_max", "price", "doc_url", "raw",
)

_INSERT_SQL = (
    "INSERT OR IGNORE INTO trades ("
    + ", ".join(_COLUMNS)
    + ") VALUES ("
    + ", ".join(":" + c for c in _COLUMNS)
    + ")"
)


def connect(db_path):
    """Open a connection with dict-like row access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn):
    """Create tables and indexes if they do not already exist."""
    conn.executescript(SCHEMA)


def upsert_trades(conn, records):
    """Insert records idempotently, returning only the newly inserted ones.

    A record is considered new when its INSERT affected exactly one row
    (cursor.rowcount == 1), which means its dedupe_key was not present.
    Commits once at the end.
    """
    new_records = []
    cursor = conn.cursor()
    for record in records:
        params = {col: record.get(col) for col in _COLUMNS}
        cursor.execute(_INSERT_SQL, params)
        if cursor.rowcount == 1:
            new_records.append(record)
    conn.commit()
    return new_records


def count_rows(conn, source=None):
    """Count rows, optionally filtered by source."""
    if source is None:
        row = conn.execute("SELECT COUNT(*) FROM trades").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE source = ?", (source,)
        ).fetchone()
    return row[0]


def ticker_coverage(conn, source):
    """Return (count with non-empty ticker, total) for the given source."""
    row = conn.execute(
        "SELECT SUM(CASE WHEN ticker IS NOT NULL AND ticker != '' THEN 1 ELSE 0 END), "
        "COUNT(*) FROM trades WHERE source = ?",
        (source,),
    ).fetchone()
    with_ticker = row[0] or 0
    total = row[1] or 0
    return (with_ticker, total)


def fetch_all(conn):
    """Return all rows ordered by filing_date DESC with nulls last."""
    return conn.execute(
        "SELECT * FROM trades ORDER BY filing_date IS NULL, filing_date DESC"
    ).fetchall()
