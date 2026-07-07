"""Regression tests for two adversarial-review findings.

1. notify() must not crash when DRY_RUN=0 and no webhook is configured; it
   should skip the send and never call requests with a None URL.
2. capitol_api_puller.pull() must return [] (not crash) when the live pull
   fails and the configured cache is missing or malformed.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.config import Config
from notify import slack
from ingest import capitol_api_puller


def _event(**over):
    base = dict(
        dedupe_key="kadoa:x1", source="kadoa", chamber="house",
        politician="Nancy Pelosi", party="D", state="CA", ticker="NVDA",
        asset_name="NVIDIA", asset_type="Stock", side="buy",
        trade_date="2026-06-30", filing_date="2026-07-06",
        amount_min=1001, amount_max=15000, price=None,
        doc_url="https://example.test/doc", raw="{}",
    )
    base.update(over)
    return base


def _cfg(**over):
    base = dict(
        slack_webhook_url=None, dry_run=True, min_amount=0, require_ticker=True,
        watchlist=[], capitol_api_url="http://localhost:3000", capitol_api_cache=None,
    )
    base.update(over)
    return Config(**base)


def _raise(*args, **kwargs):
    raise RuntimeError("live down")


def test_notify_no_webhook_does_not_crash():
    # DRY_RUN=0 but no webhook: must skip send, not call send_slack, not crash.
    called = {"n": 0}

    def guard(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("send_slack must not be called without a webhook")

    original = slack.send_slack
    slack.send_slack = guard
    try:
        emitted = slack.notify([_event()], _cfg(dry_run=False, slack_webhook_url=None))
    finally:
        slack.send_slack = original
    assert emitted == [slack.format_message(_event())]
    assert called["n"] == 0


def test_capitol_pull_bad_cache_returns_empty():
    original = capitol_api_puller.pull_live
    capitol_api_puller.pull_live = _raise
    try:
        out = capitol_api_puller.pull(
            _cfg(capitol_api_cache="C:/nonexistent/does_not_exist.json")
        )
    finally:
        capitol_api_puller.pull_live = original
    assert out == []


def test_capitol_pull_no_cache_returns_empty():
    original = capitol_api_puller.pull_live
    capitol_api_puller.pull_live = _raise
    try:
        out = capitol_api_puller.pull(_cfg(capitol_api_cache=None))
    finally:
        capitol_api_puller.pull_live = original
    assert out == []


if __name__ == "__main__":
    test_notify_no_webhook_does_not_crash()
    test_capitol_pull_bad_cache_returns_empty()
    test_capitol_pull_no_cache_returns_empty()
    print("regression tests passed")
