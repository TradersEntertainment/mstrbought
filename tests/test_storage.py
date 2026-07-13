import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


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
    conn.execute("""CREATE TABLE processed_filings (
        accession_number TEXT PRIMARY KEY, filing_date TEXT, form TEXT, url TEXT,
        parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()
    return db_path


def test_sale_is_stored_signed_and_roundtrips_through_api(temp_db):
    parsed = {
        "event_type": "btc_sale",
        "purchase_period": "June 29, 2026 to July 5, 2026",
        "btc_signed_str": "-3,588",
        "btc_abs_str": "3,588",
        "btc_acquired": "3,588",
        "purchase_price": "$216.0M",
        "avg_price": "$60,197",
        "total_holdings": "843,775",
        "total_cost": "$63.69B",
        "avg_cost": "$75,476",
        "total_debt": "$6.7B",
        "financing_details": "-",
        "atm": {
            "securities": [
                {"ticker": "MSTR", "shares_sold": "4,818,781", "net_proceeds": "$466.7M"},
            ],
            "sold_tickers": ["MSTR"],
            "sold_any": True,
            "total_net_proceeds": "$466.7M",
        },
    }
    bot.save_to_database('2026-07-06', parsed, 'http://example.com/filing',
                         '0001193125-26-000001', '8-K')

    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM purchase_history ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row['btc_acquired'] == '-3,588'
    assert row['event_type'] == 'btc_sale'
    assert json.loads(row['atm_sales'])['sold_tickers'] == ['MSTR']

    client = bot.app.test_client()
    data = client.get('/api/history').get_json()
    assert data[0]['btc_acquired'] == '-3,588'
    assert data[0]['event_type'] == 'btc_sale'
    assert data[0]['atm_sales']['securities'][0]['ticker'] == 'MSTR'


def test_hold_week_is_stored_as_zero(temp_db):
    parsed = {
        "event_type": "no_purchase",
        "purchase_period": "July 6, 2026 to July 12, 2026",
        "btc_signed_str": "0",
        "btc_abs_str": "0",
        "btc_acquired": "0",
        "purchase_price": "-",
        "avg_price": "-",
        "total_holdings": "843,775",
        "total_cost": "$63.69B",
        "avg_cost": "$75,476",
        "total_debt": "$6.7B",
        "financing_details": "MSTR ATM Hisse Satışı ($466.7M)",
    }
    bot.save_to_database('2026-07-13', parsed, 'http://example.com/filing2',
                         '0001193125-26-000002', '8-K')

    client = bot.app.test_client()
    data = client.get('/api/history').get_json()
    assert data[0]['btc_acquired'] == '0'
    assert data[0]['financing_source'] == 'MSTR ATM Hisse Satışı ($466.7M)'
    assert data[0]['atm_sales'] is None


def test_legacy_unsigned_path_still_works(temp_db):
    # The Groq-only no-table path supplies legacy fields without btc_signed_str
    parsed = {
        "event_type": "corporate_update",
        "summary_turkish": "x",
        "total_debt_usd": "$6.7B",
        "financing_source_turkish": "-",
    }
    bot.save_to_database('2026-07-14', parsed, 'http://example.com/filing3',
                         '0001193125-26-000003', '8-K')

    client = bot.app.test_client()
    data = client.get('/api/history').get_json()
    assert data[0]['btc_acquired'] == '-'
