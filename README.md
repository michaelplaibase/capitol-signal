# Capitol Signal (POC)

A local, signal-only feed of disclosed US politician stock trades. It ingests
public disclosures, stores them in SQLite, detects newly seen trades on each run,
and emits Danish-language notifications (dry-run by default, optional Slack
webhook).

## Signal only

This system shows trades. It never places, prepares, or simulates a brokerage
order. Auto-execution is a regulated activity (MiFID II portfolio management) and
is explicitly out of scope. There is no trade-execution code in this repository,
and there never should be.

Disclosures are not real time. Under the STOCK Act politicians may file weeks
after trading, so this feed reflects filings, not live positions.

## Architecture

```
capitol-api (Node, localhost:3000)        Kadoa trades.json (raw.githubusercontent)
  House PTR, live fetch                     House + Senate + OGE, recent window
        |                                             |
  ingest/capitol_api_puller.py              ingest/kadoa_puller.py
        |                                             |
        +----------------------+----------------------+
                               v
                     core/normalize.py  (shared field mapping)
                               v
                     core/db.py     (SQLite signal.db, INSERT OR IGNORE)
                               v
                     core/diff.py   (new dedupe_key = one event)
                               v
                     notify/slack.py  (Danish messages, DRY_RUN default)
                               ^
                         main.py orchestrates
```

## Setup

Requirements: Python 3.11+, the `requests` library (already present), stdlib
sqlite3. No framework. `python-dotenv` is not required (a stdlib .env loader is
used).

```
cp .env.example .env      # optional, sensible defaults apply without it
python main.py
```

## Configuration (.env)

| Key | Default | Meaning |
|-----|---------|---------|
| SLACK_WEBHOOK_URL | (empty) | Slack incoming webhook. Empty keeps dry-run. |
| DRY_RUN | 1 | 1 = print only. 0 = POST to Slack. |
| MIN_AMOUNT | 0 | Only notify when amount_min (USD) is at least this. |
| REQUIRE_TICKER | 1 | 1 = only notify trades with a resolved ticker. |
| WATCHLIST | (empty) | Comma-separated last names. Empty = all. |
| CAPITOL_API_URL | http://localhost:3000 | Base URL of the local capitol-api. |
| CAPITOL_API_CACHE | (empty) | Optional cache json path for offline House data. |

Secrets live only in `.env`, which is git-ignored. Commit `.env.example` only.

## Notification format

```
🟢 KØB | Pelosi (D-CA) | NVDA | 1.001-15.000 USD | handlet 30-06-2026, indberettet 06-07-2026 | Hus | <filing link>
```

Green circle = KØB (buy), red = SALG (sell), 🔁 = BYT (exchange). Chamber labels
are Hus, Senat, OGE. Amounts use the Danish thousands separator.

## Data sources

- Source A: crnicholson/capitol-api. Self-hosted Node service, House PTR only,
  live fetch from disclosures-clerk.house.gov. NO license (see Risks). Vendored
  unmodified under vendor/ (git-ignored), consumed as a black box over localhost.
- Source B: kadoa-org/congress-trading-monitor trades.json (MIT). House + Senate
  + OGE, recent rolling window, refreshed multiple times per day.

## Tests

```
python -m pytest tests/ -q
```

17 tests: field normalization, both mappers, db idempotency (backs G3), Danish
notification formatting and filters (backs G4), and two regression tests for the
adversarial-review findings (missing-webhook guard, cache-read failure).

## Verification and gate status

See VERIFICATION.md for full evidence. Summary: G2, G3, G4 PASS. G1 (capitol-api
live fetch) is BLOCKED by the local auto-mode security policy, not by network or
code. VERIFICATION.md section 1 has the commands to complete G1 yourself.

## Risks

- capitol-api has NO license despite the README calling it open source. POC and
  internal use only. Before any commercial use: open an upstream issue or write
  an own parser against disclosures-clerk.house.gov.
- capitol-api transitive npm deps report 7 vulnerabilities (5 moderate, 2 high).
  The vendored copy is intentionally unmodified.
- Kadoa is a commercial vendor. Free-repo continuity is not guaranteed.
- Reporting lag is inherent to STOCK Act data. This is a disclosure feed, not a
  real-time trade feed. Never present it otherwise.
- Signal only. No brokerage integration, ever, in this codebase.
