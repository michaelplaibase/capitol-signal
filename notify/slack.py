"""Slack notification formatting and delivery for Capitol Signal.

Signal-only module: it formats trade events into Danish notification strings
and posts them to Slack. It never places, prepares, or simulates any order.
"""

import sys

import requests

from core.normalize import last_name


def side_label(side):
    """Return (emoji, danish_label) for a normalized side value.

    Uses the actual emoji characters, not their shortcode names.
    """
    if side == "buy":
        return ("🟢", "KØB")
    if side == "sell":
        return ("🔴", "SALG")
    if side == "exchange":
        return ("🔁", "BYT")
    return ("⚪", "ANDET")


def chamber_label(chamber):
    """Return the Danish chamber label for a normalized chamber value."""
    if chamber == "house":
        return "Hus"
    if chamber == "senate":
        return "Senat"
    if chamber == "oge":
        return "OGE"
    return "Ukendt"


def format_amount(amin, amax):
    """Format an amount range using a Danish thousands separator.

    Both bounds present: "1.001-15.000 USD" (comma grouping then replaced by dot).
    Otherwise: "ukendt beloeb" with correct oe letter.
    """
    if amin is not None and amax is not None:
        text = f"{amin:,}-{amax:,} USD"
        return text.replace(",", ".")
    return "ukendt beløb"


def format_date_dk(iso):
    """Convert an ISO yyyy-mm-dd date to Danish dd-mm-yyyy.

    None or invalid input returns "?".
    """
    if not iso or not isinstance(iso, str):
        return "?"
    parts = iso[:10].split("-")
    if len(parts) != 3:
        return "?"
    year, month, day = parts
    if len(year) != 4 or len(month) != 2 or len(day) != 2:
        return "?"
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return "?"
    return f"{day}-{month}-{year}"


def format_message(event):
    """Build the exact single-line, pipe separated notification string.

    Template:
      "{emoji} {SIDE_DK} | {LastName} ({PARTY}-{STATE}) | {TICKER} | {AMOUNT} |
       handlet {TRADE}, indberettet {FILING} | {CHAMBER} | {DOCURL}"
    """
    emoji, side_dk = side_label(event.get("side"))
    politician = event.get("politician") or ""
    name = last_name(politician) or politician
    party = event.get("party") or "?"
    state = event.get("state") or "?"
    ticker = event.get("ticker") or event.get("asset_name") or "?"
    amount = format_amount(event.get("amount_min"), event.get("amount_max"))
    trade = format_date_dk(event.get("trade_date"))
    filing = format_date_dk(event.get("filing_date"))
    chamber = chamber_label(event.get("chamber"))
    doc_url = event.get("doc_url") or "ingen link"
    return (
        f"{emoji} {side_dk} | {name} ({party}-{state}) | {ticker} | {amount} | "
        f"handlet {trade}, indberettet {filing} | {chamber} | {doc_url}"
    )


def passes_filters(event, cfg):
    """Return True when the event should be emitted given the config filters."""
    if cfg.require_ticker and not event.get("ticker"):
        return False
    if (event.get("amount_min") or 0) < cfg.min_amount:
        return False
    if cfg.watchlist and last_name(event.get("politician", "")).lower() not in cfg.watchlist:
        return False
    return True


def send_slack(webhook_url, text, timeout=10):
    """POST a Slack message payload and return the HTTP status code."""
    response = requests.post(webhook_url, json={"text": text}, timeout=timeout)
    return response.status_code


def notify(events, cfg):
    """Emit notifications for events passing the filters.

    In dry_run mode each message is printed; otherwise it is sent to Slack.
    Returns the list of emitted message strings.
    """
    emitted = []
    for event in events:
        if not passes_filters(event, cfg):
            continue
        msg = format_message(event)
        if cfg.dry_run:
            print(msg)
        elif cfg.slack_webhook_url:
            send_slack(cfg.slack_webhook_url, msg)
        else:
            print(
                "warning: DRY_RUN=0 but SLACK_WEBHOOK_URL is not set; skipping send",
                file=sys.stderr,
            )
        emitted.append(msg)
    return emitted
