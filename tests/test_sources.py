import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


class FakeResp:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def reset_source_state(monkeypatch):
    monkeypatch.setattr(bot, '_sec_backoff', {})
    monkeypatch.setattr(bot, '_submissions_etag', None)
    monkeypatch.setattr(bot, '_submissions_last_modified', None)
    monkeypatch.setattr(bot, '_efts_shape_logged', True)


def test_efts_parses_real_response_shape(monkeypatch):
    payload = {"hits": {"hits": [{
        "_id": "0001193125-26-295586:mstr-20260706.htm",
        "_source": {"ciks": ["0001050446"], "file_date": "2026-07-06"},
    }]}}
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: FakeResp(200, payload))

    results = bot.fetch_mstr_filings_efts()
    assert results == [{
        "accession": "0001193125-26-295586",
        "date": "2026-07-06",
        "url": "https://www.sec.gov/Archives/edgar/data/1050446/000119312526295586/mstr-20260706.htm",
    }]


def test_efts_accepts_legacy_shape(monkeypatch):
    payload = {"hits": {"hits": [{
        "_id": "something-else",
        "_source": {"file_url": "https://www.sec.gov/x.htm",
                    "adsh": "0001193125-26-295586",
                    "file_date": "2026-07-06"},
    }]}}
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: FakeResp(200, payload))

    results = bot.fetch_mstr_filings_efts()
    assert results[0]['accession'] == '0001193125-26-295586'
    assert results[0]['url'] == 'https://www.sec.gov/x.htm'


def test_efts_backs_off_after_throttle(monkeypatch):
    calls = []

    def fake_get(url, timeout=None, headers=None):
        calls.append(url)
        return FakeResp(429)

    monkeypatch.setattr(bot.http_session, 'get', fake_get)

    assert bot.fetch_mstr_filings_efts() == []
    assert len(calls) == 1
    # Backoff active: the next poll must not hit the network at all
    assert bot.fetch_mstr_filings_efts() == []
    assert len(calls) == 1


def test_submissions_conditional_get_commits_after_consume(monkeypatch):
    seen_headers = []

    def fake_get(url, timeout=None, headers=None):
        seen_headers.append(headers or {})
        if len(seen_headers) == 1:
            return FakeResp(200, {"filings": {"recent": {}}}, {'ETag': '"abc"'})
        return FakeResp(304)

    monkeypatch.setattr(bot.http_session, 'get', fake_get)

    data, state = bot.fetch_mstr_filings(return_state=True)
    assert data is not None
    assert seen_headers[0].get('If-None-Match') is None
    # The fetch itself must NOT store the validators...
    assert bot._submissions_etag is None
    # ...only an explicit commit after the payload has been consumed does
    bot._commit_submissions_state(state)
    assert bot._submissions_etag == '"abc"'

    # Next poll sends the stored ETag and treats 304 as "nothing new"
    data2, state2 = bot.fetch_mstr_filings(return_state=True)
    assert data2 is None and state2 is None
    assert seen_headers[1]['If-None-Match'] == '"abc"'


def test_submissions_dropped_payload_does_not_poison_etag(monkeypatch):
    """Regression for the confirmed review finding: a poll that abandons a
    slow fetch must not leave the new ETag behind, or every later poll would
    304 past the filing carried by the dropped payload."""
    seen_headers = []

    def fake_get(url, timeout=None, headers=None):
        seen_headers.append(headers or {})
        return FakeResp(200, {"filings": {"recent": {}}}, {'ETag': '"new"'})

    monkeypatch.setattr(bot.http_session, 'get', fake_get)

    # check_for_new_filings timed out: the state tuple is never committed
    bot.fetch_mstr_filings(return_state=True)
    assert bot._submissions_etag is None

    # The next poll therefore re-fetches unconditionally and gets a full 200
    data, _ = bot.fetch_mstr_filings(return_state=True)
    assert data is not None
    assert 'If-None-Match' not in seen_headers[1]


def test_submissions_unconditional_skips_etag(monkeypatch):
    monkeypatch.setattr(bot, '_submissions_etag', '"abc"')
    seen_headers = []

    def fake_get(url, timeout=None, headers=None):
        seen_headers.append(headers or {})
        return FakeResp(200, {"filings": {"recent": {}}}, {})

    monkeypatch.setattr(bot.http_session, 'get', fake_get)
    assert bot.fetch_mstr_filings(use_conditional=False) is not None
    assert 'If-None-Match' not in seen_headers[0]
