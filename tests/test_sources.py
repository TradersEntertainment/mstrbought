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
    # Source staggering timers must not leak between tests. Submissions no
    # longer has one: it is the only endpoint with a published sub-second
    # SLA and it carries primaryDocument inline, so it runs every tick.
    monkeypatch.setattr(bot, '_last_efts_time', 0.0)
    monkeypatch.setattr(bot, '_last_atom_time', 0.0)
    monkeypatch.setattr(bot, '_inflight', {"submissions": False, "atom": False, "efts": False})
    monkeypatch.setattr(bot, '_pending', {"submissions": None, "atom": [], "efts": []})
    # _mark_processed writes to the real DB; the scan tests only care that
    # the accession stops being re-offered.
    monkeypatch.setattr(bot, '_mark_processed',
                        lambda acc, date, form, url: bot._processed_cache.add(acc))


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
                        lambda: [{"accession": "0001193125-26-000009",
                                  "date": "2026-08-03", "url": ""}])
    monkeypatch.setattr(bot, '_resolve_primary_document',
                        lambda acc: 'https://www.sec.gov/Archives/x/mstr.htm')
    calls = []
    monkeypatch.setattr(bot, 'process_filing',
                        lambda acc, date, form, url: calls.append((acc, url)) or True)

    assert bot.check_for_new_filings() == 1
    assert calls == [('0001193125-26-000009', 'https://www.sec.gov/Archives/x/mstr.htm')]

    # Already processed on the next tick → no duplicate alert
    calls.clear()
    assert bot.check_for_new_filings() == 0
    assert calls == []


# EDGAR's browse-edgar atom output carries the accession under a MISSPELLED
# tag. The parser used to require the correct spelling, so every entry was
# dropped and the feed silently produced nothing — while the two sources it
# was meant to replace had been slowed down to make room for it. The fixture
# above was hand-written with the correct spelling, so it never caught this.
ATOM_BODY_TYPO = ATOM_BODY.replace('accession-number', 'accession-nunber')


def test_atom_feed_parses_the_misspelled_edgar_accession_tag(monkeypatch):
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: TextResp(200, ATOM_BODY_TYPO))

    results = bot.fetch_mstr_filings_atom()
    assert [r["accession"] for r in results] == ['0001193125-26-320011',
                                                 '0001193125-26-295586']


def test_atom_feed_recovers_the_accession_from_filing_href_alone(monkeypatch):
    body = """<feed><entry><content>
   <filing-date>2026-08-03</filing-date>
   <filing-href>https://www.sec.gov/Archives/edgar/data/1050446/000119312526320011/0001193125-26-320011-index.htm</filing-href>
   <filing-type>8-K</filing-type>
  </content></entry></feed>"""
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: TextResp(200, body))

    results = bot.fetch_mstr_filings_atom()
    assert [r["accession"] for r in results] == ['0001193125-26-320011']


def test_efts_query_drops_the_bitcoin_full_text_filter(monkeypatch):
    """q="bitcoin" made EFTS blind to every 8-K without that literal word."""
    seen = {}

    def fake_get(url, timeout=None, headers=None):
        seen['url'] = url
        return FakeResp(200, {"hits": {"hits": []}})

    monkeypatch.setattr(bot.http_session, 'get', fake_get)
    bot.fetch_mstr_filings_efts()
    assert 'bitcoin' not in seen['url']
    assert 'ciks=0001050446' in seen['url']
    assert 'forms=8-K' in seen['url']


def test_efts_legacy_shape_rejects_a_file_number(monkeypatch):
    """`file_num` is not an accession; storing it poisons dedup forever."""
    payload = {"hits": {"hits": [{
        "_id": "not-an-accession",
        "_source": {"file_num": "001-33049", "file_url": "https://x/y.htm",
                    "file_date": "2026-07-06"},
    }]}}
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: FakeResp(200, payload))
    assert bot.fetch_mstr_filings_efts() == []


def test_submissions_url_wins_over_the_atom_guess(monkeypatch):
    """Whoever was scanned first used to claim the accession and shadow the
    authoritative primaryDocument URL — a wrong guess could livelock."""
    monkeypatch.setattr(bot, '_processed_cache', set())
    monkeypatch.setattr(bot, '_processed_cache_time', bot.time.time())
    acc = '0001193125-26-320011'
    submissions = {"filings": {"recent": {
        "form": ["8-K"], "accessionNumber": [acc],
        "filingDate": ["2026-08-03"], "primaryDocument": ["mstr-20260803.htm"],
    }}}
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False:
                            (submissions, {}) if return_state else submissions)
    monkeypatch.setattr(bot, 'fetch_mstr_filings_efts', lambda: [])
    monkeypatch.setattr(bot, 'fetch_mstr_filings_atom',
                        lambda: [{"accession": acc, "date": "2026-08-03", "url": ""}])
    monkeypatch.setattr(bot, '_resolve_primary_document',
                        lambda a: 'https://www.sec.gov/Archives/WRONG.htm')
    calls = []
    monkeypatch.setattr(bot, 'process_filing',
                        lambda a, d, f, url: calls.append(url) or True)

    bot.check_for_new_filings()
    assert calls == ['https://www.sec.gov/Archives/edgar/data/1050446/'
                     '000119312526320011/mstr-20260803.htm']


def test_newest_filing_is_dispatched_first(monkeypatch):
    """reversed() alerted the just-landed filing LAST, behind every stale one."""
    monkeypatch.setattr(bot, '_processed_cache', set())
    monkeypatch.setattr(bot, '_processed_cache_time', bot.time.time())
    recent = {
        "form": ["8-K", "8-K", "8-K"],
        "accessionNumber": ['0001193125-26-000003', '0001193125-26-000002',
                            '0001193125-26-000001'],
        "filingDate": ["2026-08-03", "2026-07-27", "2026-07-20"],
        "primaryDocument": ["c.htm", "b.htm", "a.htm"],
    }
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False:
                            ({"filings": {"recent": recent}}, {}) if return_state
                            else {"filings": {"recent": recent}})
    monkeypatch.setattr(bot, 'fetch_mstr_filings_efts', lambda: [])
    monkeypatch.setattr(bot, 'fetch_mstr_filings_atom', lambda: [])
    order = []
    monkeypatch.setattr(bot, 'process_filing',
                        lambda a, d, f, u: order.append(d) or True)

    bot.check_for_new_filings()
    assert order == ["2026-08-03", "2026-07-27", "2026-07-20"]


def test_a_slow_source_cannot_withhold_the_others(monkeypatch):
    """Results are read from their cells whether or not the thread finished.

    All three lists used to be read only after three sequential join(4)
    calls, so one hung request blinded every source for up to 12 seconds.
    """
    monkeypatch.setattr(bot, '_processed_cache', set())
    monkeypatch.setattr(bot, '_processed_cache_time', bot.time.time())
    monkeypatch.setattr(bot, 'POLL_INTERVAL_CRITICAL', 0.25)

    def hanging_submissions(use_conditional=True, return_state=False):
        bot.time.sleep(30)
        return (None, None) if return_state else None

    monkeypatch.setattr(bot, 'fetch_mstr_filings', hanging_submissions)
    monkeypatch.setattr(bot, 'fetch_mstr_filings_efts', lambda: [])
    monkeypatch.setattr(bot, 'fetch_mstr_filings_atom',
                        lambda: [{"accession": '0001193125-26-320011',
                                  "date": "2026-08-03",
                                  "url": "https://www.sec.gov/Archives/x/mstr.htm"}])
    calls = []
    monkeypatch.setattr(bot, 'process_filing',
                        lambda a, d, f, u: calls.append(a) or True)

    started = bot.time.time()
    bot.check_for_new_filings()
    elapsed = bot.time.time() - started

    assert calls == ['0001193125-26-320011']
    assert elapsed < 5, f"a hung source stalled the tick for {elapsed:.1f}s"


def test_concurrent_scans_do_not_double_alert(monkeypatch):
    """/check and /api/trigger share every global with the poll loop."""
    import threading

    monkeypatch.setattr(bot, '_processed_cache', set())
    monkeypatch.setattr(bot, '_processed_cache_time', bot.time.time())
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False:
                            (None, None) if return_state else None)
    monkeypatch.setattr(bot, 'fetch_mstr_filings_efts', lambda: [])
    monkeypatch.setattr(bot, 'fetch_mstr_filings_atom',
                        lambda: [{"accession": '0001193125-26-320011',
                                  "date": "2026-08-03",
                                  "url": "https://www.sec.gov/Archives/x/mstr.htm"}])
    calls = []

    def slow_process(a, d, f, u):
        bot.time.sleep(0.2)
        calls.append(a)
        return True

    monkeypatch.setattr(bot, 'process_filing', slow_process)

    threads = [threading.Thread(target=bot.check_for_new_filings) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert calls == ['0001193125-26-320011']


def test_a_fetch_slower_than_the_tick_is_delivered_on_the_next_one(monkeypatch):
    """Production logs show constant 3s read timeouts against www.sec.gov, so
    reads are now allowed longer than a tick. A result that lands after the
    join deadline must not be thrown away."""
    monkeypatch.setattr(bot, '_processed_cache', set())
    monkeypatch.setattr(bot, '_processed_cache_time', bot.time.time())
    monkeypatch.setattr(bot, 'POLL_INTERVAL_CRITICAL', 0.25)
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False:
                            (None, None) if return_state else None)
    monkeypatch.setattr(bot, 'fetch_mstr_filings_efts', lambda: [])

    def slow_atom():
        bot.time.sleep(2.5)   # outruns the ~2s join deadline
        return [{"accession": '0001193125-26-320011', "date": "2026-08-03",
                 "url": "https://www.sec.gov/Archives/x/mstr.htm"}]

    monkeypatch.setattr(bot, 'fetch_mstr_filings_atom', slow_atom)
    calls = []
    monkeypatch.setattr(bot, 'process_filing',
                        lambda a, d, f, u: calls.append(a) or True)

    assert bot.check_for_new_filings() == 0   # tick 1: not back yet
    assert calls == []

    bot.time.sleep(1.5)                        # the fetch lands meanwhile
    monkeypatch.setattr(bot, '_last_atom_time', 0.0)
    bot.check_for_new_filings()                # tick 2 drains the mailbox
    assert calls == ['0001193125-26-320011']


def test_sec_get_retries_a_dropped_keepalive_socket(monkeypatch):
    """Production logs show RemoteDisconnected on the submissions index: a
    pooled socket the peer closed after we wrote the request."""
    import requests as _rq
    attempts = []

    def flaky(url, timeout=None, headers=None):
        attempts.append(timeout)
        if len(attempts) == 1:
            raise _rq.exceptions.ConnectionError("Connection aborted.")
        return FakeResp(200, {})

    monkeypatch.setattr(bot.http_session, 'get', flaky)
    assert bot.sec_get("https://data.sec.gov/x").status_code == 200
    assert len(attempts) == 2
    # split connect/read timeouts, not one flat value applied to each phase
    assert attempts[0] == (bot.SEC_CONNECT_TIMEOUT, bot.SEC_READ_TIMEOUT)


def test_sec_get_does_not_retry_a_slow_origin(monkeypatch):
    """A read timeout means SEC is slow; retrying would only add load."""
    import requests as _rq
    attempts = []

    def always_slow(url, timeout=None, headers=None):
        attempts.append(1)
        raise _rq.exceptions.ReadTimeout("Read timed out.")

    monkeypatch.setattr(bot.http_session, 'get', always_slow)
    with pytest.raises(_rq.exceptions.ReadTimeout):
        bot.sec_get("https://www.sec.gov/x")
    assert len(attempts) == 1
