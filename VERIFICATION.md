# VERIFICATION

Every claim below is backed by a command that was actually run on this machine
(Windows 11, Python 3.12.8, Node 25.9.0) on 2026-07-07. Anything that could not
be tested end to end is marked UNVERIFIED.

## Gate summary

| Gate | What it proves | Result |
|------|----------------|--------|
| G1 | capitol-api live fetch returns a record with filingDate > 2026-04-03 | BLOCKED (see below), fallback executed |
| G2 | Kadoa newest filing_date within 7 days of today | PASS (1 day) |
| G3 | Running the pipeline twice with no upstream change yields 0 events | PASS |
| G4 | One synthetic new record yields exactly 1 dry-run notification | PASS |

## 0. Environment and network egress

```
Python 3.12.8 ; Node v25.9.0 ; npm 11.10.1 ; git 2.49.0
Kadoa data URL            HTTP 200
npm registry              HTTP 200
disclosures-clerk.house.gov  HTTP 200   (capitol-api upstream, reachable)
github.com                HTTP 200
```

Egress is open. The prior session's sandbox blocked disclosures-clerk; this
machine does not. So the reason G1 could not complete is NOT network (see G1).

## 1. Gate G1: capitol-api live fetch (BLOCKED by local policy, not failed)

G1 could not be completed in this session. The cause is not any of the prompt's
predicted failure modes (network blocked, parser broken, no fresh records). It
is that running the third-party capitol-api server was denied by the Claude Code
auto-mode security classifier:

```
Permission denied by auto mode classifier.
Reason: [Code from External] Running node server.js from the crnicholson/capitol-api
repo cloned this session executes untrusted third-party code; run outside auto
mode for user review.
```

Everything up to executing the server was done and verified:

- Egress to disclosures-clerk.house.gov: HTTP 200 (above).
- Clone: succeeded (shallow clone into vendor/capitol-api).
- Install: `npm install --ignore-scripts` succeeded, 112 packages, 0 lifecycle
  scripts executed. (7 transitive-dep vulnerabilities reported: 5 moderate, 2
  high. capitol-api is left unmodified per the prompt, so these are not patched.)
- Code inspection (read-only): package.json has no pre/post-install scripts;
  server.js and dataService.js contain no child_process, exec, spawn, eval, or
  new Function. All filesystem writes are scoped to the repo's own cache/ dir.
  External hosts are exactly the three documented ones: disclosures-clerk.house.gov,
  unitedstates.github.io (legislators), query1.finance.yahoo.com (prices).
- capitol-api startup behavior confirmed by reading dataService.js:
  `CACHE_REFRESH_HOURS` defaults to 0, so with the shipped cache present the
  server serves the stale cache and does not auto-fetch. A live fetch must be
  forced with `POST /api/refresh`.

### Fallback executed (as the prompt requires on a non-pass G1)

capitol-api was demoted to a cache-only House reference and Kadoa carries the
recent House + Senate + OGE feed. The capitol-api integration path (mapper,
dedupe, notify) was still proven end to end using the real shipped cache via the
puller's cache-fallback mode (see sections 3, 4, 7, 8).

### To complete G1 yourself (outside auto mode)

```
cd capitol-signal/vendor/capitol-api
node server.js
# in a second shell:
curl -X POST http://localhost:3000/api/refresh          # force a live fetch
curl  http://localhost:3000/api/status                  # poll until fetch done
curl "http://localhost:3000/api/trades?recent=50"       # look for filingDate > 2026-04-03
# then run the live pipeline (CAPITOL_API_URL defaults to http://localhost:3000):
python capitol-signal/main.py
```

## 2. Gate G2: Kadoa freshness (PASS)

```
kadoa records count: 5000
filing_date span: 2026-05-14 .. 2026-07-06 (newest 1 days from 2026-07-07)
```

Newest filing_date is 1 day old, well within the 7-day bar. G2 PASS.

## 3. Row counts in signal.db per source (first full run, both sources)

capitol-api via its real cache (live server blocked), Kadoa live:

```
Capitol Signal run summary
  pulled[capitol-api] = 8855
  pulled[kadoa] = 5000
  map_errors = 0
  future_filtered = 1
  new_events = 13854
  emitted = 9052

rows per source (stored):
  capitol-api: 8854 rows   (8855 pulled minus 1 future-dated)
  kadoa:       5000 rows

chamber breakdown:
  capitol-api house    8854
  kadoa       oge      4268
  kadoa       house     571
  kadoa       senate    161
```

## 4. Live-measured ticker coverage per source (this run, not the prompt numbers)

```
capitol-api: ticker 7908/8854 = 89.3%
kadoa:       ticker 1144/5000 = 22.9%
```

## 5. Gate G3: idempotency (PASS)

Kadoa-only, two back-to-back runs on the same db:

```
RUN 1:  pulled[kadoa]=5000  new_events=5000  emitted=1144
RUN 2:  pulled[kadoa]=5000  new_events=0     emitted=0
```

Also proven by the G4 demo (run 2 = 0) and by tests/test_db_diff.py
(2 records then 0). G3 PASS.

## 6. Gate G4: one synthetic new record yields exactly 1 notification (PASS)

A synthetic capitol-api record (fixture, not prod data) run through main.py:

```
=== G4 RUN 1 (one synthetic new record) ===
new_events: 1  emitted: 1
NOTIFICATION: 🟢 KØB | Pelosi (D-CA) | NVDA | 1.001-15.000 USD | handlet 30-06-2026, indberettet 06-07-2026 | Hus | https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/G4.pdf
=== G4 RUN 2 (same record, expect 0) ===
new_events: 0  emitted: 0
G4 RESULT: PASS
```

## 7. Future-dated records filtered

```
future_filtered = 1
```

The single record is the capitol-api entry with tradeDate 2026-12-26 (a filing
typo), which is later than today + 1 day and is dropped by the sanity filter.
Kadoa had 0 future-dated records.

## 8. Cross-source duplicate estimate (measured, not resolved)

Match key: (politician last name, ticker, trade_date, amount_min), tickered rows only.

```
matching keys: 1
estimated overlapping record pairs: 1
example: evans CVS 2025-11-21 amount_min=1001
  capitol-api doc: https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20033667.pdf
  kadoa       doc: https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20034556.pdf
```

Caveat: this overlap is low because the shipped capitol-api cache covers up to
2026-03-31 while the Kadoa window starts 2026-05-14, so the two barely overlap in
time. With a live capitol-api the overlap would be much larger. Cross-source
dedupe resolution is a v2 decision, not done here.

## 9. Deviations from the prompt

- python-dotenv is not installed on this machine. To avoid a pip install (which
  the classifier would likely block), config uses a small stdlib .env loader in
  core/config.py instead of python-dotenv. This is strictly more minimal.
- Added an optional CAPITOL_API_CACHE env var (and puller cache-fallback mode) so
  the House path can run without the Node server. This is what let the capitol-api
  integration be proven despite G1 being blocked.
- npm install was run with --ignore-scripts (no lifecycle scripts) as a safety
  measure. capitol-api deps are all pure JS so nothing is lost.
- capitol-api data in the full run came from its shipped cache, not a live fetch,
  because G1 was blocked (section 1).

## 10. UNVERIFIED

- G1 live fetch: whether capitol-api actually pulls records with filingDate >
  2026-04-03 from disclosures-clerk within 20 minutes. Blocked by the auto-mode
  classifier. Repro commands are in section 1.
- Real Slack delivery (DRY_RUN=0 with a live webhook): not exercised. The dry-run
  path and the missing-webhook guard are tested; an actual POST to Slack is not.
