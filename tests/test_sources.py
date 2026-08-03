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
    monkeypatch.setattr(bot, '_atom_shape_logged', True)
    # Source staggering timers must not leak between tests
    monkeypatch.setattr(bot, '_last_efts_time', 0.0)
    monkeypatch.setattr(bot, '_last_submissions_time', 0.0)


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


# --- Atom feed: the fastest new-filing signal --------------------------------

ATOM_BODY = """<?xml version="1.0" encoding="ISO-8859-1"?>
<feed xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <category label="form type" scheme="https://www.sec.gov/" term="8-K"/>
  <content type="text/xml">
   <accession-number>0001193125-26-320011</accession-number>
   <filing-date>2026-08-03</filing-date>
   <filing-href>https://www.sec.gov/Archives/edgar/data/1050446/000119312526320011/0001193125-26-320011-index.htm</filing-href>
   <filing-type>8-K</filing-type>
  </content>
  <title>8-K - Current report</title>
 </entry>
 <entry>
  <content type="text/xml">
   <accession-number>0001193125-26-295586</accession-number>
   <filing-date>2026-07-06</filing-date>
   <filing-type>8-K</filing-type>
  </content>
 </entry>
 <entry>
  <content type="text/xml">
   <accession-number>0001193125-26-100000</accession-number>
   <filing-date>2026-07-01</filing-date>
   <filing-type>424B5</filing-type>
  </content>
 </entry>
</feed>"""


class TextResp:
    def __init__(self, status_code, text='', payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        return self._payload


def test_atom_feed_parses_8k_entries(monkeypatch):
    monkeypatch.setattr(bot, '_atom_shape_logged', True)
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: TextResp(200, ATOM_BODY))

    results = bot.fetch_mstr_filings_atom()
    # Only 8-K entries, newest first, URLs resolved lazily (empty here)
    assert [r["accession"] for r in results] == ['0001193125-26-320011',
                                                 '0001193125-26-295586']
    assert results[0]["date"] == '2026-08-03'
    assert results[0]["url"] == ''


def test_atom_feed_failure_is_silent(monkeypatch):
    monkeypatch.setattr(bot, '_atom_shape_logged', True)
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: TextResp(403))
    assert bot.fetch_mstr_filings_atom() == []
    # 403 registers a backoff on its own source only — submissions stays free
    assert bot._sec_blocked('atom') is True
    assert bot._sec_blocked('submissions') is False


def test_resolve_primary_document_picks_filing_body(monkeypatch):
    payload = {"directory": {"item": [
        {"name": "0001193125-26-320011-index.htm"},
        {"name": "mstr-20260803.htm"},
        {"name": "d12345dex991.htm"},
        {"name": "logo.jpg"},
    ]}}
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: TextResp(200, payload=payload))
    url = bot._resolve_primary_document('0001193125-26-320011')
    assert url == ('https://www.sec.gov/Archives/edgar/data/1050446/'
                   '000119312526320011/mstr-20260803.htm')


def test_submissions_uneven_arrays_do_not_abort_the_scan(monkeypatch):
    # EDGAR can serve momentarily uneven parallel arrays while indexing a new
    # filing — an IndexError here used to kill the whole poll cycle.
    data = {"filings": {"recent": {
        "form": ["8-K", "8-K", "10-Q"],
        "accessionNumber": ["0001-26-1", "0001-26-2", "0001-26-3"],
        "filingDate": ["2026-08-03", "2026-07-27", "2026-05-05"],
        "primaryDocument": ["mstr-20260803.htm"],     # short by two
    }}}
    monkeypatch.setattr(bot, '_processed_cache', set())
    monkeypatch.setattr(bot, '_processed_cache_time', bot.time.time())
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False:
                            (data, None) if return_state else data)
    monkeypatch.setattr(bot, 'fetch_mstr_filings_efts', lambda: [])
    monkeypatch.setattr(bot, 'fetch_mstr_filings_atom', lambda: [])
    seen = []
    monkeypatch.setattr(bot, 'process_filing',
                        lambda acc, date, form, url: seen.append(acc) or True)

    found = bot.check_for_new_filings()
    assert found == 1
    assert seen == ['0001-26-1']


def test_atom_detection_beats_submissions_and_dedupes(monkeypatch):
    monkeypatch.setattr(bot, '_processed_cache', set())
    monkeypatch.setattr(bot, '_processed_cache_time', bot.time.time())
    # Submissions index has not caught up yet
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False:
                            (None, None) if return_state else None)
    monkeypatch.setattr(bot, 'fetch_mstr_filings_efts', lambda: [])
    monkeypatch.setattr(bot, 'fetch_mstr_filings_atom',
                        lambda: [{"accession": "0001-26-9", "date": "2026-08-03", "url": ""}])
    monkeypatch.setattr(bot, '_resolve_primary_document',
                        lambda acc: 'https://www.sec.gov/Archives/x/mstr.htm')
    calls = []
    monkeypatch.setattr(bot, 'process_filing',
                        lambda acc, date, form, url: calls.append((acc, url)) or True)

    assert bot.check_for_new_filings() == 1
    assert calls == [('0001-26-9', 'https://www.sec.gov/Archives/x/mstr.htm')]

    # Already processed on the next tick → no duplicate alert
    calls.clear()
    assert bot.check_for_new_filings() == 0
    assert calls == []
