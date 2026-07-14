"""Tests for the historical ATM backfill job."""
import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    monkeypatch.setattr(bot, 'DB_PATH', db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filing_date TEXT, period TEXT, btc_acquired TEXT, purchase_price TEXT,
        avg_price TEXT, total_holdings TEXT, total_cost TEXT, avg_cost TEXT,
        url TEXT, total_debt TEXT, financing_source TEXT,
        atm_sales TEXT, event_type TEXT)""")
    conn.commit()
    conn.close()
    return db_path


def insert_row(db_path, url, financing_source='-', atm_sales=None):
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        """INSERT INTO purchase_history
           (filing_date, btc_acquired, total_holdings, url, financing_source, atm_sales)
           VALUES ('2026-06-22', '520', '847,363', ?, ?, ?)""",
        (url, financing_source, atm_sales))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_row(db_path, row_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM purchase_history WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return dict(row)


ARCHIVES_URL = 'https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260622.htm'


def test_backfill_fills_atm_and_empty_financing(temp_db, monkeypatch):
    row_id = insert_row(temp_db, ARCHIVES_URL, financing_source='-')
    monkeypatch.setattr(bot, 'fetch_html', lambda url: load_fixture('june22_purchase.html'))

    bot.backfill_atm_history(sleep_seconds=0)

    row = get_row(temp_db, row_id)
    atm = json.loads(row['atm_sales'])
    assert atm['sold_tickers'] == ['MSTR']
    assert atm['securities'][4]['shares_sold'] == '512,344'
    # Empty '-' badge is filled from the parsed ATM data
    assert row['financing_source'] == 'MSTR ATM ($34.9M)'


def test_backfill_preserves_existing_financing_text(temp_db, monkeypatch):
    row_id = insert_row(temp_db, ARCHIVES_URL, financing_source='Konvertibl Tahvil İhracı')
    monkeypatch.setattr(bot, 'fetch_html', lambda url: load_fixture('june22_purchase.html'))

    bot.backfill_atm_history(sleep_seconds=0)

    row = get_row(temp_db, row_id)
    assert json.loads(row['atm_sales'])['sold_any'] is True
    assert row['financing_source'] == 'Konvertibl Tahvil İhracı'


def test_backfill_fetch_failure_retries_next_run(temp_db, monkeypatch):
    row_id = insert_row(temp_db, ARCHIVES_URL)
    calls = []

    def failing_fetch(url):
        calls.append(url)
        return ""

    monkeypatch.setattr(bot, 'fetch_html', failing_fetch)
    bot.backfill_atm_history(sleep_seconds=0)
    assert get_row(temp_db, row_id)['atm_sales'] is None  # stays NULL

    # Next run retries the same row
    monkeypatch.setattr(bot, 'fetch_html', lambda url: load_fixture('june22_purchase.html'))
    bot.backfill_atm_history(sleep_seconds=0)
    assert json.loads(get_row(temp_db, row_id)['atm_sales'])['sold_any'] is True


def test_backfill_no_atm_table_writes_sentinel_once(temp_db, monkeypatch):
    row_id = insert_row(temp_db, ARCHIVES_URL)
    calls = []

    def counting_fetch(url):
        calls.append(url)
        return load_fixture('july06_double_sale.html')  # BTC tables only, no ATM

    monkeypatch.setattr(bot, 'fetch_html', counting_fetch)

    bot.backfill_atm_history(sleep_seconds=0)
    row = get_row(temp_db, row_id)
    assert json.loads(row['atm_sales'])['note'] == 'no_atm_table'
    assert len(calls) == 1

    # Sentinel present → second run must not fetch again
    bot.backfill_atm_history(sleep_seconds=0)
    assert len(calls) == 1


def test_backfill_reparses_pre_fmt2_rows(temp_db, monkeypatch):
    """Rows stored before the period_scoped guard get re-fetched once."""
    old_json = json.dumps({"sold_any": True, "securities": [],
                           "sold_tickers": ["STRC"]})  # no fmt marker
    row_id = insert_row(temp_db, ARCHIVES_URL, atm_sales=old_json)

    monkeypatch.setattr(bot, 'fetch_html', lambda url: load_fixture('june22_purchase.html'))
    bot.backfill_atm_history(sleep_seconds=0)

    row = get_row(temp_db, row_id)
    atm = json.loads(row['atm_sales'])
    assert atm['fmt'] == 4
    assert atm['period_scoped'] is True

    # fmt-2 rows are not fetched again
    def must_not_fetch(url):
        raise AssertionError('fmt-2 rows must not be re-fetched')
    monkeypatch.setattr(bot, 'fetch_html', must_not_fetch)
    bot.backfill_atm_history(sleep_seconds=0)


def test_backfill_placeholder_url_no_fetch(temp_db, monkeypatch):
    row_id = insert_row(
        temp_db, 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001050446&type=8-K')

    def must_not_be_called(url):
        raise AssertionError('fetch_html must not be called for placeholder URLs')

    monkeypatch.setattr(bot, 'fetch_html', must_not_be_called)
    bot.backfill_atm_history(sleep_seconds=0)

    assert json.loads(get_row(temp_db, row_id)['atm_sales'])['note'] == 'no_fetchable_doc'
