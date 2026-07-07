"""Diff logic for detecting newly seen trades.

An insert of a new dedupe_key into the trades table is exactly one signal event.
This module delegates persistence and idempotency to core.db and treats the list
of newly inserted records as the list of events to act on.
"""

from core import db


def detect_new_trades(conn, mapped_records):
    """Insert mapped records and return only the newly inserted ones.

    A record is new when its dedupe_key was not already present in the trades
    table. db.upsert_trades runs INSERT OR IGNORE per record and returns the
    list of records that were actually inserted (one event per new dedupe_key).

    Parameters:
      conn: an open sqlite3 connection (see core.db.connect)
      mapped_records: list of normalized record dicts

    Returns:
      list: the subset of mapped_records that were newly inserted (the events)
    """
    return db.upsert_trades(conn, mapped_records)
