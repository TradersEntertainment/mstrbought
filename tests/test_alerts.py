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
        atm_sales TEXT, event_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()
    return db_path


def parse_with_atm(fixture):
    tables = bot.extract_filing_tables(load_fixture(fixture))
    data = bot.parse_btc_tables(tables)
    atm = bot.parse_atm_table(tables)
    if data and atm:
        data['atm'] = atm
        data['financing_details'] = bot.financing_source_from_atm(atm)
    return data, atm


def test_hold_with_atm_alert_july13(temp_db):
    """The corrected first message for the July 13 incident filing."""
    data, _ = parse_with_atm('july13_hold_atm.html')
    alert = bot.format_alert(data, 'http://example.com')

    assert 'ALMADI / SATMADI (0 BTC)' in alert
    assert 'SATTI' not in alert
    assert '843,775' in alert
    assert 'ATM Satışı VAR' in alert
    assert 'MSTR: 4,818,781 adet' in alert
    assert '$466.7M' in alert
    # Unsold tickers collapsed into one line
    assert 'STRF / STRC / STRK / STRD: satış yok' in alert


def test_sale_alert_with_breakdown(temp_db):
    data, _ = parse_with_atm('july06_double_sale.html')
    alert = bot.format_alert(data, 'http://example.com')

    assert 'MSTR BTC SATTI: -3,588 BTC!' in alert
    assert '↳' in alert  # multi-period breakdown
    assert '-1,363 BTC @ $59,256' in alert
    assert '-2,225 BTC @ $60,773' in alert
    assert '843,775' in alert


def test_purchase_alert_with_atm_financing(temp_db):
    data, _ = parse_with_atm('june22_purchase.html')
    alert = bot.format_alert(data, 'http://example.com')

    assert 'MSTR BTC ALDI: +520 BTC!' in alert
    assert 'ATM Satışı VAR' in alert
    assert 'MSTR: 512,344 adet' in alert


def test_financing_alert_atm_only(temp_db):
    tables = bot.extract_filing_tables(load_fixture('atm_only.html'))
    atm = bot.parse_atm_table(tables)
    parsed = {
        'event_type': 'financing',
        'atm': atm,
        'financing_details': bot.financing_source_from_atm(atm),
        'purchase_period': atm.get('period'),
    }
    alert = bot.format_alert(parsed, 'http://example.com')
    assert 'ATM Satışı VAR' in alert
    assert 'STRC: 1,200,000 adet' in alert
    assert '$119.4M' in alert


def test_inferred_amount_is_labeled(temp_db):
    parsed = {
        'event_type': 'btc_sale',
        'inferred': True,
        'btc_abs_str': '2,225',
        'btc_signed_str': '-2,225',
        'total_holdings': '843,775',
        'purchase_period': 'July 12, 2026',
    }
    alert = bot.format_alert(parsed, 'http://example.com')
    assert 'bilanço farkından tahmini' in alert
