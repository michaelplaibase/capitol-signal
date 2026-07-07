"""Normalization helpers for the Capitol Signal POC.

Leaf module: no project imports. Produces the small primitive values that
mappers assemble into the normalized record shape. All functions tolerate
messy or missing input and never raise on bad data.
"""

from datetime import date


# Side mapping tables per source. Keys are lowercased raw values.
_CAPITOL_SIDE = {
    "buy": "buy",
    "sell": "sell",
    "exchange": "exchange",
}

_KADOA_SIDE = {
    "purchase": "buy",
    "sale (full)": "sell",
    "sale (partial)": "sell",
    "exchange": "exchange",
}


def normalize_side(source, raw_value):
    """Map a source specific transaction type to a canonical side.

    Canonical sides: buy, sell, exchange, other. Matching is
    case-insensitive. Anything unrecognized or None becomes "other".
    """
    if raw_value is None:
        return "other"
    key = str(raw_value).strip().lower()
    if source == "capitol-api":
        return _CAPITOL_SIDE.get(key, "other")
    if source == "kadoa":
        return _KADOA_SIDE.get(key, "other")
    return "other"


def normalize_party(raw):
    """Normalize a party label to a short code.

    Republican -> R, Democratic/Democrat -> D, Independent -> I.
    Existing R/D/I pass through. None or "" -> None. Anything else uses
    the first letter uppercased.
    """
    if raw is None:
        return None
    value = str(raw).strip()
    if value == "":
        return None
    lowered = value.lower()
    if lowered == "republican":
        return "R"
    if lowered in ("democratic", "democrat"):
        return "D"
    if lowered == "independent":
        return "I"
    upper = value.upper()
    if upper in ("R", "D", "I"):
        return upper
    return value[0].upper()


def to_iso_date(raw):
    """Return the first 10 chars if they form a valid yyyy-mm-dd date, else None."""
    if raw is None:
        return None
    text = str(raw)
    if len(text) < 10:
        return None
    candidate = text[:10]
    try:
        date.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def is_future_dated(iso_date, today):
    """True when iso_date parses and lands more than one day past today.

    A date equal to today+1 is not considered future dated; today+2 is.
    """
    if iso_date is None:
        return False
    try:
        parsed = date.fromisoformat(str(iso_date)[:10])
    except ValueError:
        return False
    delta = (parsed - today).days
    return delta > 1


def build_dedupe_key(source, source_record_id):
    """Compose the stable dedupe key f"{source}:{source_record_id}"."""
    return f"{source}:{source_record_id}"


def last_name(full_name):
    """Return the last whitespace token, stripped of trailing punctuation.

    Empty or None input returns "".
    """
    if not full_name:
        return ""
    tokens = str(full_name).split()
    if not tokens:
        return ""
    token = tokens[-1]
    return token.rstrip(".,;:!?)'\"")


def to_int(x):
    """Parse an int, tolerating strings that contain commas, $, and spaces."""
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return int(x)
    text = str(x).strip()
    if text == "":
        return None
    cleaned = text.replace(",", "").replace("$", "").strip()
    if cleaned == "":
        return None
    try:
        return int(cleaned)
    except ValueError:
        try:
            return int(float(cleaned))
        except ValueError:
            return None


def to_float(x):
    """Parse a float, tolerating strings that contain commas, $, and spaces."""
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    text = str(x).strip()
    if text == "":
        return None
    cleaned = text.replace(",", "").replace("$", "").strip()
    if cleaned == "":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None
