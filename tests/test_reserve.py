"""Tests for parsing the USD Reserve from 8-K text and using it as cash."""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


@pytest.fixture(autouse=True)
def silence_log(monkeypatch):
    monkeypatch.setattr(bot, '_usd_reserve_logged', True)


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
    conn.execute("""CREATE TABLE financial_metrics (
        metric TEXT, period_end TEXT, value REAL, form TEXT, filed TEXT,
        PRIMARY KEY (metric, period_end))""")
    conn.commit()
    conn.close()
    return db_path


@pytest.mark.parametrize("text,expect", [
    ("Strategy announced a USD Reserve of $3.0 billion to support dividends "
     "on its preferred stock and interest on its indebtedness.", 3000.0),
    ("increased its USD Reserve to $2.55 billion", 2550.0),
    ("raised $466.7 million, boosting the U.S. dollar reserve to $3 billion", 3000.0),
    ("maintains a $1.44 billion cash reserve", 1440.0),
    ("just bitcoin holdings of 843,775 BTC", None),
])
def test_parse_usd_reserve(text, expect):
    assert bot.parse_usd_reserve(text) == expect


def test_parse_usd_reserve_prefers_reserve_over_raise():
    # The $466.7M raise must not be mistaken for the reserve figure
    text = "The company raised $466.7 million and now holds a USD Reserve of $3.0 billion."
    assert bot.parse_usd_reserve(text) == 3000.0


def test_reserve_series_becomes_primary_cash(temp_db):
    conn = sqlite3.connect(temp_db)
    # A quarterly XBRL cash figure + weekly reserve figures from 8-Ks
    conn.execute("INSERT INTO financial_metrics VALUES ('cash_and_equivalents','2026-03-31',2210000000,'10-Q','2026-05-06')")
    conn.execute("INSERT INTO financial_metrics VALUES ('usd_reserve','2026-07-06',2550000000,'sec-8k','2026-07-06')")
    conn.execute("INSERT INTO financial_metrics VALUES ('usd_reserve','2026-07-13',3000000000,'sec-8k','2026-07-13')")
    conn.execute("INSERT INTO purchase_history (filing_date, btc_acquired, total_holdings) VALUES ('2026-07-13','0','843,775')")
    conn.commit()
    conn.close()

    result = bot.compute_cash_estimate()
    assert result['cash_source'] == 'sec-8k'
    # The chart's actuals are the weekly reserve series, not the XBRL quarter
    assert [a['period_end'] for a in result['actuals']] == ['2026-07-06', '2026-07-13']
    assert result['actuals'][-1]['cash_m'] == 3000.0
    # Runway basis is the latest real reserve ($3B)
    assert result['runway']['basis_cash_m'] == 3000.0
    assert result['runway']['basis_source'] == 'sec-8k'


def test_falls_back_to_xbrl_without_reserve(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("INSERT INTO financial_metrics VALUES ('cash_and_equivalents','2026-03-31',2210000000,'10-Q','2026-05-06')")
    conn.commit()
    conn.close()
    result = bot.compute_cash_estimate()
    assert result['cash_source'] == 'xbrl'


def test_store_usd_reserve_roundtrip(temp_db):
    assert bot.store_usd_reserve('2026-07-13', 3000.0) is True
    assert bot.store_usd_reserve('2026-07-13', None) is False
    m = bot.get_official_metric('usd_reserve')
    assert m['value_m'] == 3000.0

    # /api/cash serves the reserve series as primary
    client = bot.app.test_client()
    data = client.get('/api/cash').get_json()
    assert data[-1]['value'] == 3000000000
    assert data[-1]['form'] == 'sec-8k'


def test_backfill_usd_reserves(temp_db, monkeypatch):
    conn = sqlite3.connect(temp_db)
    conn.execute("INSERT INTO purchase_history (filing_date, btc_acquired, url) "
                 "VALUES ('2026-07-13','0','https://www.sec.gov/Archives/edgar/data/1050446/x/mstr.htm')")
    conn.execute("INSERT INTO purchase_history (filing_date, btc_acquired, url) "
                 "VALUES ('2026-06-01','0','https://www.sec.gov/Archives/edgar/data/1050446/y/mstr.htm')")
    conn.commit()
    conn.close()

    htmls = {
        'https://www.sec.gov/Archives/edgar/data/1050446/x/mstr.htm':
            '<html><body>Strategy holds a USD Reserve of $3.0 billion for dividends.</body></html>',
        'https://www.sec.gov/Archives/edgar/data/1050446/y/mstr.htm':
            '<html><body>No reserve statement, just routine matters.</body></html>',
    }
    monkeypatch.setattr(bot, 'fetch_html', lambda url: htmls.get(url, ''))
    bot.backfill_usd_reserves(sleep_seconds=0)

    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    got = {r['period_end']: r['value'] for r in conn.execute(
        "SELECT period_end, value FROM financial_metrics WHERE metric='usd_reserve'")}
    none_marked = [r['period_end'] for r in conn.execute(
        "SELECT period_end FROM financial_metrics WHERE metric='usd_reserve_none'")]
    conn.close()
    assert got == {'2026-07-13': 3000000000.0}
    assert none_marked == ['2026-06-01']  # scanned, no reserve → sentinel, won't re-fetch
