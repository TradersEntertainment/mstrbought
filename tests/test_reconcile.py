"""Recovering weeks that were marked processed but never parsed.

Production froze at the seed's newest date, 2026-07-13, because a fresh
database marked every 8-K in the EDGAR index as processed without parsing
any of it. The poller then skipped them as "not new" forever, and neither
existing backfill could help: both iterate purchase_history, and the row was
never created. The false-sale alert of 2026-08-30 computed against 843,775 —
the hardcoded 13 July seed figure — which is how the freeze was found.
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / 'r.db')
    monkeypatch.setattr(bot, 'DB_PATH', path)
    monkeypatch.setattr(bot.time, 'sleep', lambda s: None)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE purchase_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, filing_date TEXT, period TEXT,
            btc_acquired TEXT, purchase_price TEXT, avg_price TEXT,
            total_holdings TEXT, total_cost TEXT, avg_cost TEXT, url TEXT,
            total_debt TEXT, financing_source TEXT, atm_sales TEXT, event_type TEXT);
        CREATE TABLE processed_filings (
            accession_number TEXT PRIMARY KEY, filing_date TEXT, form TEXT, url TEXT);
    """)
    # The seed's newest week, recorded.
    conn.execute("INSERT INTO purchase_history (filing_date, total_holdings) "
                 "VALUES ('2026-07-13', '843,775')")
    conn.execute("INSERT INTO processed_filings VALUES "
                 "('acc-0713', '2026-07-13', '8-K', 'https://x/0713.htm')")
    # Five later weeks: marked processed, never parsed. The freeze.
    for i, date in enumerate(['2026-07-20', '2026-07-27', '2026-08-03',
                              '2026-08-17', '2026-08-24']):
        conn.execute("INSERT INTO processed_filings VALUES (?, ?, '8-K', ?)",
                     (f'acc-{i}', date, f'https://x/{date}.htm'))
    conn.commit()
    conn.close()
    return path


def test_the_frozen_weeks_are_found_and_re_parsed(db, monkeypatch):
    seen = []
    monkeypatch.setattr(bot, '_record_without_alert',
                        lambda acc, date, form, url: seen.append(date))

    assert bot.reconcile_missing_history() == 5
    assert seen == ['2026-07-20', '2026-07-27', '2026-08-03',
                    '2026-08-17', '2026-08-24']


def test_weeks_already_recorded_are_left_alone(db, monkeypatch):
    """Re-fetching a week we already hold is pointless traffic."""
    seen = []
    monkeypatch.setattr(bot, '_record_without_alert',
                        lambda acc, date, form, url: seen.append(date))
    bot.reconcile_missing_history()

    assert '2026-07-13' not in seen


def test_a_second_run_is_a_no_op(db, monkeypatch):
    """Once the rows exist the join stops matching, so a redeploy does not
    re-fetch the same weeks every boot."""
    def record(acc, date, form, url):
        conn = bot.get_db_connection()
        conn.execute("INSERT INTO purchase_history (filing_date, total_holdings) "
                     "VALUES (?, '1')", (date,))
        conn.commit()
        conn.close()

    monkeypatch.setattr(bot, '_record_without_alert', record)
    assert bot.reconcile_missing_history() == 5
    assert bot.reconcile_missing_history() == 0


def test_the_batch_is_bounded(db, monkeypatch):
    monkeypatch.setattr(bot, 'RECONCILE_MAX', 2)
    seen = []
    monkeypatch.setattr(bot, '_record_without_alert',
                        lambda acc, date, form, url: seen.append(date))

    bot.reconcile_missing_history()
    assert len(seen) == 2


def test_one_bad_filing_does_not_abort_the_rest(db, monkeypatch):
    seen = []

    def flaky(acc, date, form, url):
        if date == '2026-07-27':
            raise ValueError("unparseable")
        seen.append(date)

    monkeypatch.setattr(bot, '_record_without_alert', flaky)
    assert bot.reconcile_missing_history() == 4
    assert len(seen) == 4


def test_rows_without_a_url_are_skipped(db, monkeypatch):
    """The seed writes some processed rows with a placeholder URL."""
    conn = sqlite3.connect(bot.DB_PATH)
    conn.execute("INSERT INTO processed_filings VALUES ('acc-x', '2026-08-31', '8-K', '')")
    conn.commit()
    conn.close()
    seen = []
    monkeypatch.setattr(bot, '_record_without_alert',
                        lambda acc, date, form, url: seen.append(date))

    bot.reconcile_missing_history()
    assert '2026-08-31' not in seen


def test_startup_marking_stops_at_the_newest_row_we_hold(db, monkeypatch):
    """The freeze itself: marking every 8-K in the index, including weeks the
    seed does not cover, made them unreachable forever."""
    recent = {
        "form": ["8-K"] * 3,
        "accessionNumber": ["acc-a", "acc-b", "acc-c"],
        "filingDate": ["2026-07-06", "2026-07-20", "2026-08-24"],
        "primaryDocument": ["a.htm", "b.htm", "c.htm"],
    }
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False:
                            {"filings": {"recent": recent}})
    conn = sqlite3.connect(bot.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("DELETE FROM processed_filings")
    conn.commit()

    bot.mark_current_filings_processed(conn)
    conn.commit()

    marked = {r[0] for r in conn.execute("SELECT filing_date FROM processed_filings")}
    conn.close()
    # We hold history up to 2026-07-13, so only older filings may be marked.
    assert marked == {'2026-07-06'}


def test_the_status_endpoint_describes_the_data_not_just_the_poller(db, monkeypatch):
    """'Son sorgu' ticks every second regardless of whether the data moved.
    That is how a seven-week freeze stayed invisible."""
    client = bot.app.test_client()
    payload = client.get('/api/status').get_json()

    assert payload["latest_filing_date"] == '2026-07-13'
    from datetime import date
    assert payload["data_age_days"] == (bot.now_et().date() - date(2026, 7, 13)).days
    assert payload["data_age_days"] > 0


def test_freshness_survives_a_missing_table(tmp_path, monkeypatch):
    """One absent table must not blank the whole report — an endpoint whose
    job is exposing staleness cannot fail quietly."""
    monkeypatch.setattr(bot, 'DB_PATH', str(tmp_path / 'empty.db'))
    conn = sqlite3.connect(bot.DB_PATH)
    conn.execute("CREATE TABLE purchase_history (id INTEGER PRIMARY KEY, filing_date TEXT)")
    conn.commit()
    conn.close()

    out = bot.data_freshness()
    assert out["latest_filing_date"] is None and out["data_age_days"] is None
