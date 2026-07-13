"""Tests for the dividend model and the backtested cash estimate."""
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
        atm_sales TEXT, event_type TEXT)""")
    conn.execute("""CREATE TABLE financial_metrics (
        metric TEXT, period_end TEXT, value REAL, form TEXT, filed TEXT,
        PRIMARY KEY (metric, period_end))""")
    conn.commit()
    conn.close()
    return db_path


def atm_json(ticker, name, notional_m, net_m):
    return json.dumps({
        "securities": [{
            "ticker": ticker, "name": name,
            "shares_sold": "1,000", "shares_sold_num": 1000,
            "notional": f"${notional_m}M" if notional_m else "-",
            "net_proceeds": f"${net_m}M" if net_m else "-",
            "net_proceeds_num_m": net_m or 0.0,
        }],
        "sold_tickers": [ticker], "sold_any": True,
    })


def insert_flow(db_path, date, btc_signed='0', price='-', atm=None):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO purchase_history (filing_date, btc_acquired, purchase_price, atm_sales)
           VALUES (?, ?, ?, ?)""", (date, btc_signed, price, atm))
    conn.commit()
    conn.close()


def insert_metric(db_path, metric, period_end, value):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed) "
        "VALUES (?, ?, ?, '10-Q', '')", (metric, period_end, value))
    conn.commit()
    conn.close()


# --- XBRL duration parsing -------------------------------------------------

def test_quarterly_duration_series_with_q4_derivation():
    entries = [
        {"start": "2025-01-01", "end": "2025-03-31", "val": 10e6, "form": "10-Q", "frame": "CY2025Q1"},
        {"start": "2025-04-01", "end": "2025-06-30", "val": 20e6, "form": "10-Q", "frame": "CY2025Q2"},
        {"start": "2025-07-01", "end": "2025-09-30", "val": 30e6, "form": "10-Q", "frame": "CY2025Q3"},
        # Annual total only — Q4 must be derived as 100 - 60 = 40
        {"start": "2025-01-01", "end": "2025-12-31", "val": 100e6, "form": "10-K", "frame": "CY2025"},
        # Non-frame duplicate must be ignored
        {"start": "2025-01-01", "end": "2025-03-31", "val": 999e6, "form": "10-K"},
    ]
    series = bot._quarterly_duration_series(entries)
    assert [s["val"] for s in series] == [10e6, 20e6, 30e6, 40e6]
    assert series[-1]["end"] == '2025-12-31'
    assert 'derived' in series[-1]["form"]


# --- Dividend model ---------------------------------------------------------

def test_dividend_model_rates_from_filing_names(temp_db, monkeypatch):
    monkeypatch.setattr(bot, 'PREFERRED_BASELINE_NOTIONAL_M',
                        {"STRF": 100.0, "STRK": 0.0, "STRD": 0.0, "STRC": 0.0})
    monkeypatch.setattr(bot, 'PREFERRED_BASELINE_AS_OF', '2026-02-01')
    monkeypatch.setattr(bot, 'STRC_ANNUAL_RATE', 0.105)

    insert_flow(temp_db, '2026-06-08', atm=atm_json(
        'STRC', 'STRC Stock Variable Rate Series A Perpetual Stretch Preferred Stock', 120.0, 119.4))
    insert_flow(temp_db, '2026-06-15', atm=atm_json(
        'STRF', 'STRF Stock 10.00% Series A Perpetual Strife Preferred Stock', 50.0, 49.5))
    insert_flow(temp_db, '2026-06-22', atm=atm_json(
        'STRK', 'STRK Stock 8.00% Series A Perpetual Strike Preferred Stock', 200.0, 198.0))
    # Actual dividends paid last quarter
    insert_metric(temp_db, 'dividends_paid', '2026-03-31', 39e6)

    model = bot.compute_dividend_model()
    by_ticker = {s['ticker']: s for s in model['series']}

    # Rates parsed from the stored security names
    assert by_ticker['STRF']['rate'] == 0.10
    assert by_ticker['STRF']['rate_source'] == 'filing_name'
    assert by_ticker['STRK']['rate'] == 0.08
    # STRC has no % in its name → config rate
    assert by_ticker['STRC']['rate'] == 0.105
    assert by_ticker['STRC']['rate_source'] == 'config (variable)'
    assert by_ticker['STRC']['frequency'] == 'aylık'

    # Outstanding = baseline + ATM notional
    assert by_ticker['STRF']['outstanding_notional_m'] == 150.0
    assert by_ticker['STRF']['monthly_cost_m'] == round(150.0 * 0.10 / 12, 2)
    assert by_ticker['STRK']['outstanding_notional_m'] == 200.0

    expected_total = 150.0 * 0.10 / 12 + 200.0 * 0.08 / 12 + 120.0 * 0.105 / 12 + 0.0
    assert model['model_monthly_total_m'] == round(expected_total, 2)

    assert model['actual_last_quarter']['paid_usd'] == 39e6
    assert model['actual_last_quarter']['monthly_avg_usd'] == 13e6
    assert model['model_vs_actual_pct'] is not None


def test_dividend_model_ignores_common_stock_and_prebaseline_sales(temp_db, monkeypatch):
    monkeypatch.setattr(bot, 'PREFERRED_BASELINE_NOTIONAL_M',
                        {"STRF": 0.0, "STRK": 0.0, "STRD": 0.0, "STRC": 0.0})
    monkeypatch.setattr(bot, 'PREFERRED_BASELINE_AS_OF', '2026-02-01')

    # MSTR common: never a dividend payer
    insert_flow(temp_db, '2026-06-08', atm=atm_json('MSTR', 'MSTR Stock Class A Common Stock', 500.0, 495.0))
    # Pre-baseline preferred sale must not be double counted
    insert_flow(temp_db, '2026-01-15', atm=atm_json(
        'STRF', 'STRF Stock 10.00% Series A Perpetual Strife Preferred Stock', 80.0, 79.0))

    model = bot.compute_dividend_model()
    by_ticker = {s['ticker']: s for s in model['series']}
    assert 'MSTR' not in by_ticker
    assert by_ticker['STRF']['atm_notional_m'] == 0.0


# --- Cash estimate + backtest ----------------------------------------------

def seed_cash_scenario(temp_db):
    # Reported quarters
    insert_metric(temp_db, 'cash_and_equivalents', '2026-03-31', 1000e6)
    insert_metric(temp_db, 'cash_and_equivalents', '2026-06-30', 1200e6)
    # Latest actual quarterly dividends: 39M → 3.0M/week
    insert_metric(temp_db, 'dividends_paid', '2026-03-31', 39e6)
    # Weekly flows inside Q2: +100 (ATM), −50 (BTC buy), +30 (BTC sale)
    insert_flow(temp_db, '2026-04-06',
                atm=atm_json('MSTR', 'MSTR Stock Class A Common Stock', None, 100.0))
    insert_flow(temp_db, '2026-05-04', btc_signed='1,000', price='$50.0M')
    insert_flow(temp_db, '2026-06-01', btc_signed='-500', price='$30.0M')
    # One flow after the last reported quarter: +10 (ATM)
    insert_flow(temp_db, '2026-07-06',
                atm=atm_json('MSTR', 'MSTR Stock Class A Common Stock', None, 10.0))


def test_cash_estimate_backtest_and_calibration(temp_db):
    seed_cash_scenario(temp_db)
    result = bot.compute_cash_estimate()

    # Raw backtest: 1000 + (100-50+30) − 3*3 = 1071 vs actual 1200
    assert len(result['backtest']) == 1
    bt = result['backtest'][0]
    assert bt['quarter_end'] == '2026-06-30'
    assert bt['predicted_m'] == 1071.0
    assert bt['actual_m'] == 1200.0
    assert bt['error_m'] == -129.0
    assert bt['weeks'] == 3

    # Calibration: residual +129 over 3 weeks → other = −43/week (an inflow
    # correction, i.e. the raw model under-estimated)
    assert result['calibration']['other_outflow_per_week_m'] == -43.0
    assert result['calibration']['weekly_dividend_m'] == 3.0
    assert result['calibration']['dividend_source'] == 'xbrl_actual'

    # Calibrated walk converges to the actual at quarter end...
    est = {e['date']: e['cash_m'] for e in result['estimate']}
    assert est['2026-06-01'] == 1200.0
    # ...then re-anchors and continues past the last reported quarter
    assert est['2026-07-06'] == 1200.0 + 10.0 - 3.0 + 43.0
    assert result['current_estimate']['date'] == '2026-07-06'


def test_runway_infinite_when_net_flow_positive(temp_db):
    # seed_cash_scenario calibrates other = −43/week; net burn = 3 − 43 < 0
    seed_cash_scenario(temp_db)
    result = bot.compute_cash_estimate()

    assert result['runway']['infinite'] is True
    assert result['runway']['weeks'] is None
    assert result['projection'] == []


def test_runway_finite_weeks_and_projection(temp_db):
    # Reverse scenario: the raw model OVER-estimates, so calibration yields a
    # POSITIVE other-outflow term and a finite runway.
    insert_metric(temp_db, 'cash_and_equivalents', '2026-03-31', 1000e6)
    insert_metric(temp_db, 'cash_and_equivalents', '2026-06-30', 900e6)
    insert_metric(temp_db, 'dividends_paid', '2026-03-31', 39e6)   # 3.0/week
    # Two flows of +50 each inside Q2:
    # raw predicted = 1000 + 100 − 2*3 = 1094 vs actual 900 → residual −194
    # → other = +97/week; net burn = 3 + 97 = 100/week
    insert_flow(temp_db, '2026-04-06',
                atm=atm_json('MSTR', 'MSTR Stock Class A Common Stock', None, 50.0))
    insert_flow(temp_db, '2026-05-04',
                atm=atm_json('MSTR', 'MSTR Stock Class A Common Stock', None, 50.0))
    # One flow after the anchor: +100 → estimate = 900 + 100 − 3 − 97 = 900
    insert_flow(temp_db, '2026-07-06',
                atm=atm_json('MSTR', 'MSTR Stock Class A Common Stock', None, 100.0))

    result = bot.compute_cash_estimate()
    r = result['runway']

    assert r['infinite'] is False
    assert r['net_burn_per_week_m'] == 100.0
    assert r['basis_cash_m'] == 900.0
    assert r['basis_date'] == '2026-07-06'
    assert r['weeks'] == 9.0
    # 9 weeks from 2026-07-06 → 2026-09-07
    assert r['depletion_date'] == '2026-09-07'

    proj = result['projection']
    assert proj[0]['date'] == '2026-07-13'
    assert proj[0]['cash_m'] == 800.0
    assert proj[-1]['cash_m'] == 0.0
    assert len(proj) <= 120


def test_change_summary_explains_the_move(temp_db):
    seed_cash_scenario(temp_db)
    result = bot.compute_cash_estimate()
    c = result['change_summary']

    # After the last re-anchor (2026-06-30 @ 1200): one week, +10 MSTR ATM,
    # no BTC, −3 dividends, −(−43) other → 1250
    assert c['since'] == '2026-06-30'
    assert c['from_cash_m'] == 1200.0
    assert c['to_cash_m'] == 1250.0
    assert c['delta_m'] == 50.0
    assert c['weeks'] == 1
    assert c['atm_by_ticker'] == {'MSTR': 10.0}
    assert c['atm_total_m'] == 10.0
    assert c['btc_buys_m'] == 0.0
    assert c['btc_sales_m'] == 0.0
    assert c['dividends_m'] == 3.0
    assert c['other_m'] == -43.0

    # Per-week driver breakdown is exposed on every estimate point
    last = result['estimate'][-1]
    assert last['atm_m'] == 10.0
    assert last['btc_m'] == 0.0
    assert last['atm_detail'] == [{'ticker': 'MSTR', 'net_m': 10.0}]


def test_cash_estimate_without_actuals_is_empty(temp_db):
    insert_flow(temp_db, '2026-04-06',
                atm=atm_json('MSTR', 'MSTR Stock Class A Common Stock', None, 100.0))
    result = bot.compute_cash_estimate()
    assert result['estimate'] == []
    assert result['backtest'] == []
    assert result['current_estimate'] is None


def test_api_cashflow_and_dividends_roundtrip(temp_db, monkeypatch):
    monkeypatch.setattr(bot, 'PREFERRED_BASELINE_NOTIONAL_M',
                        {"STRF": 0.0, "STRK": 0.0, "STRD": 0.0, "STRC": 0.0})
    seed_cash_scenario(temp_db)

    client = bot.app.test_client()
    flow = client.get('/api/cashflow').get_json()
    assert flow['current_estimate']['cash_m'] == 1250.0

    divs = client.get('/api/dividends').get_json()
    assert {s['ticker'] for s in divs['series']} == {'STRF', 'STRK', 'STRD', 'STRC'}
    assert divs['actual_last_quarter']['monthly_avg_usd'] == 13e6
