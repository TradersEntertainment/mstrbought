"""Tests for Strategy's official (strategy.com) figures overriding estimates."""
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
        atm_sales TEXT, event_type TEXT)""")
    conn.execute("""CREATE TABLE financial_metrics (
        metric TEXT, period_end TEXT, value REAL, form TEXT, filed TEXT,
        PRIMARY KEY (metric, period_end))""")
    conn.commit()
    conn.close()
    return db_path


def test_official_reserve_becomes_latest_anchor(temp_db):
    # A real 10-Q, then Strategy's official reserve dated later
    bot.store_official_figures(usd_reserve_m=3000, annual_dividends_m=1763,
                               pref_m=15464, debt_m=6754, asof='2026-07-13')
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed) "
        "VALUES ('cash_and_equivalents', '2026-03-31', 2210000000, '10-Q', '2026-05-06')")
    conn.commit()
    conn.close()

    result = bot.compute_cash_estimate()
    # The official $3B (2026-07-13) is the most recent actual anchor
    assert result['actuals'][-1]['form'] == 'strategy.com'
    assert result['actuals'][-1]['cash_m'] == 3000.0

    # Dividend burn now comes from the official annual figure
    cal = result['calibration']
    assert cal['dividend_source'] == 'strategy.com'
    assert cal['weekly_dividend_m'] == round(1763 / 52.0, 2)

    # Official block surfaces the ground-truth figures
    off = result['official']
    assert off['usd_reserve_m'] == 3000.0
    assert off['annual_dividends_m'] == 1763.0
    assert off['pref_m'] == 15464.0
    assert off['asof'] == '2026-07-13'

    # The 10-Q calendar ignores the strategy.com anchor
    fi = result['filing_info']
    assert fi['last_form'] == '10-Q'
    assert fi['last_period_end'] == '2026-03-31'


def test_official_dividends_in_dividend_model(temp_db):
    bot.store_official_figures(annual_dividends_m=1763, pref_m=15464, asof='2026-07-13')
    model = bot.compute_dividend_model()
    assert model['official']['annual_dividends_m'] == 1763.0
    assert model['official']['monthly_dividends_m'] == round(1763 / 12.0, 1)
    assert model['official']['pref_outstanding_m'] == 15464.0


def test_api_official_get_and_post(temp_db, monkeypatch):
    monkeypatch.setattr(bot, 'ADMIN_PASSWORD', 'secret')
    client = bot.app.test_client()

    # Wrong password rejected
    assert client.post('/api/official?password=nope&asof=2026-07-13&usd_reserve_m=3000').status_code == 401

    # Correct password stores
    r = client.post('/api/official?password=secret&asof=2026-07-13'
                    '&usd_reserve_m=3000&annual_dividends_m=1763&pref_m=15464&debt_m=6754')
    assert r.get_json()['status'] == 'success'

    got = client.get('/api/official').get_json()
    assert got['usd_reserve']['value_m'] == 3000.0
    assert got['annual_dividends_m'] == 1763.0
    assert got['pref_m'] == 15464.0


def test_env_sync(temp_db, monkeypatch):
    monkeypatch.setenv('STRATEGY_USD_RESERVE_M', '3000')
    monkeypatch.setenv('STRATEGY_ANNUAL_DIVIDENDS_M', '1763')
    monkeypatch.setenv('STRATEGY_ASOF', '2026-07-13')
    bot.sync_official_figures_from_env()

    m = bot.get_official_metric('official_annual_dividends')
    assert m['value_m'] == 1763.0
