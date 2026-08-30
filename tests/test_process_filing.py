"""Detection-to-alert behaviour.

Every case here previously produced a late alert, a lost alert, or a poll
loop stuck retrying one filing forever.
"""
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

HTML = "<html><body><p>MSTR 8-K</p></body></html>"


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setattr(bot, 'groq_keys', [])
    monkeypatch.setattr(bot, 'FETCH_RETRY_DELAY', 0.0)
    monkeypatch.setattr(bot, 'build_reserve_context', lambda d, h: None)
    monkeypatch.setattr(bot, 'save_to_database',
                        lambda *a, **k: None)
    monkeypatch.setattr(bot, 'store_usd_reserve', lambda *a, **k: None)
    before = set(threading.enumerate())
    yield
    # process_filing deliberately hands the rest of the work to daemon
    # threads. Let them finish before monkeypatch tears the stubs out from
    # under them, or they raise against half-restored module state.
    for t in set(threading.enumerate()) - before:
        t.join(timeout=5)


def _today():
    return bot.now_et().strftime("%Y-%m-%d")


def test_fetch_is_retried_before_giving_up(monkeypatch):
    """EDGAR lists an accession before the Archives serve its document.

    A single 404 used to abort the filing and defer the retry to the next
    poll interval — 2s inside the fast window, a full minute outside it.
    """
    attempts = []

    def flaky(url):
        attempts.append(url)
        return HTML if len(attempts) >= 3 else ""

    monkeypatch.setattr(bot, 'fetch_html', flaky)
    monkeypatch.setattr(bot, 'send_telegram_alert', lambda *a, **k: 42)

    assert bot.process_filing("0001193125-26-320011", _today(), "8-K",
                              "https://x/y.htm") is True
    assert len(attempts) == 3


def test_a_failed_telegram_send_is_reported_as_failure(monkeypatch):
    """send_telegram_alert returning None used to be ignored: the filing was
    marked processed and the alert was lost for good."""
    monkeypatch.setattr(bot, 'fetch_html', lambda url: HTML)
    monkeypatch.setattr(bot, 'send_telegram_alert', lambda *a, **k: None)

    assert bot.process_filing("0001193125-26-320011", _today(), "8-K",
                              "https://x/y.htm") is False


def test_a_parse_failure_still_produces_an_alert(monkeypatch):
    """A deterministic parse error made process_filing raise every time, so
    the loop retried the same filing forever and never alerted at all."""
    monkeypatch.setattr(bot, 'fetch_html', lambda url: HTML)

    def boom(html):
        raise ValueError("malformed table")

    monkeypatch.setattr(bot, 'extract_filing_tables', boom)
    sent = []
    monkeypatch.setattr(bot, 'send_telegram_alert',
                        lambda text, **k: sent.append(text) or 7)

    assert bot.process_filing("0001193125-26-320011", _today(), "8-K",
                              "https://x/y.htm") is True
    assert len(sent) == 1
    assert "8-K" in sent[0]


def test_a_stale_filing_does_not_block_the_poll_thread(monkeypatch):
    """should_alert=False used to suppress only the send: the fetch and both
    HTML parses still ran inline, blocking the poll loop for nothing. The
    history row is still recorded, just off the poll thread."""
    recorded = []
    monkeypatch.setattr(bot, '_record_without_alert',
                        lambda *a: recorded.append(a[0]))
    monkeypatch.setattr(bot, 'fetch_html',
                        lambda url: pytest.fail("should not fetch inline"))
    monkeypatch.setattr(bot, 'send_telegram_alert',
                        lambda *a, **k: pytest.fail("should not alert"))

    assert bot.process_filing("0001193125-26-320011", "2020-01-01", "8-K",
                              "https://x/y.htm") is True
    assert recorded == ["0001193125-26-320011"]


def test_nothing_parses_the_document_before_the_send(monkeypatch):
    """clean_html is a full second parse of the document that exists only to
    feed the background Groq thread. It used to run ahead of the send in two
    of the three branches, and it holds the GIL while it does."""
    monkeypatch.setattr(bot, 'fetch_html', lambda url: HTML)
    order = []
    monkeypatch.setattr(bot, 'clean_html',
                        lambda h: order.append("clean_html") or "text")
    monkeypatch.setattr(bot, 'send_telegram_alert',
                        lambda *a, **k: order.append("send") or 9)

    bot.process_filing("0001193125-26-320011", _today(), "8-K", "https://x/y.htm")
    assert order and order[0] == "send"
