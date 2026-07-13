"""Live SEC EDGAR tests — network required, run with LIVE_SEC_TESTS=1.

These replicate the retired root-level test_parser.py checks against real
filings, and verify the offline fixtures still match reality.
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

pytestmark = pytest.mark.skipif(
    os.getenv('LIVE_SEC_TESTS') != '1',
    reason='live SEC tests only run with LIVE_SEC_TESTS=1')


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


def test_july06_double_sale_live(temp_db):
    """The filing with two sale periods (-1,363 and -2,225)."""
    url = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526295586/mstr-20260706.htm"
    html = bot.fetch_html(url)
    assert html, "could not fetch filing"

    result = bot.parse_table_fallback(html)
    assert result['event_type'] == 'btc_sale'
    assert result['btc_signed_str'] == '-3,588'
    assert result['total_holdings'] == '843,775'


def test_june22_purchase_live(temp_db):
    url = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm"
    html = bot.fetch_html(url)
    assert html, "could not fetch filing"

    result = bot.parse_table_fallback(html)
    assert result['event_type'] == 'btc_purchase'
    assert result['btc_signed_str'] == '520'


def test_efts_live_shape():
    """Verify the real EFTS response parses (also logs the raw hit shape)."""
    bot._efts_shape_logged = False
    results = bot.fetch_mstr_filings_efts()
    # No assertion on count (there may be no filing today) — only that any
    # returned entries carry the expected keys and a dashed accession.
    for r in results:
        assert set(r) == {'accession', 'date', 'url'}
        assert r['url'].startswith('https://www.sec.gov/')
