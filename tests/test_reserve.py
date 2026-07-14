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


def _atm_row(ticker, name, notional_m, net_m):
    import json
    return json.dumps({
        "fmt": 4, "period_scoped": True,
        "securities": [{
            "ticker": ticker, "name": name,
            "shares_sold": "1,000", "shares_sold_num": 1000,
            "notional": f"${notional_m}M" if notional_m else "-",
            "net_proceeds": f"${net_m}M" if net_m else "-",
            "net_proceeds_num_m": net_m or 0.0,
        }],
        "sold_tickers": [ticker], "sold_any": True,
    })


def _insert(db_path, sql, params):
    conn = sqlite3.connect(db_path)
    conn.execute(sql, params)
    conn.commit()
    conn.close()


# --- Fast (alert-path) reserve parse ----------------------------------------

def test_parse_usd_reserve_fast_tag_split():
    # Real filings split the sentence across spans/fonts — the windowed
    # parser must still find it after stripping tags locally
    html = ('<html><body><p>The company <span>increased its </span>'
            '<b>USD&nbsp;Reserve</b> to <font>$3.0&#160;billion</font> to support '
            'dividends.</p></body></html>')
    assert bot.parse_usd_reserve_fast(html) == 3000.0


def test_parse_usd_reserve_fast_no_statement():
    assert bot.parse_usd_reserve_fast('<html><body>bitcoin holdings of 843,775 BTC</body></html>') is None
    assert bot.parse_usd_reserve_fast('') is None


# --- Official annual dividends (strategy.com figure, auto-derived) ----------

def test_annual_dividends_from_xbrl(temp_db):
    # strategy.com publishes ~$1,763M/yr; the same figure = latest reported
    # quarter of dividends paid ×4 (SEC XBRL)
    _insert(temp_db, "INSERT INTO financial_metrics VALUES ('dividends_paid','2026-03-31',440750000,'10-Q','2026-05-05')", ())
    annual = bot.compute_annual_dividends()
    assert annual['source'] == 'xbrl_actual'
    assert annual['annual_m'] == 1763.0
    assert annual['detail']['xbrl_annualized_m'] == 1763.0
    assert annual['detail']['atm_added_annual_m'] == 0.0


def test_annual_dividends_topped_up_by_post_quarter_atm(temp_db):
    # $400M paid in Q1 → $1,600M/yr base; $1,000M STRC (10%) sold via ATM
    # AFTER the quarter end adds $100M/yr → $1,700M/yr total
    _insert(temp_db, "INSERT INTO financial_metrics VALUES ('dividends_paid','2026-03-31',400000000,'10-Q','2026-05-05')", ())
    _insert(temp_db,
            "INSERT INTO purchase_history (filing_date, btc_acquired, atm_sales) VALUES (?,?,?)",
            ('2026-05-18', '0', _atm_row('STRC', 'STRC Stock 10.00% Series A Perpetual Stretch Preferred Stock', 1000.0, 998.0)))
    # A pre-quarter sale must NOT be added (already inside the paid quarter)
    _insert(temp_db,
            "INSERT INTO purchase_history (filing_date, btc_acquired, atm_sales) VALUES (?,?,?)",
            ('2026-02-10', '0', _atm_row('STRC', 'STRC Stock 10.00% Series A Perpetual Stretch Preferred Stock', 500.0, 498.0)))
    annual = bot.compute_annual_dividends()
    assert annual['annual_m'] == 1700.0
    assert annual['detail']['atm_added_annual_m'] == 100.0


def test_annual_dividends_official_override_wins(temp_db):
    _insert(temp_db, "INSERT INTO financial_metrics VALUES ('dividends_paid','2026-03-31',400000000,'10-Q','2026-05-05')", ())
    bot.store_official_figures(annual_dividends_m=1763, asof='2026-07-13')
    annual = bot.compute_annual_dividends()
    assert annual['source'] == 'strategy.com'
    assert annual['annual_m'] == 1763.0


# --- Reserve context for the Telegram alert ---------------------------------

def test_build_reserve_context_months_from_official_annual(temp_db):
    # Previous week's reserve + real dividend quarter seeded
    _insert(temp_db, "INSERT INTO financial_metrics VALUES ('usd_reserve','2026-07-06',2550000000,'sec-8k','2026-07-06')", ())
    _insert(temp_db, "INSERT INTO financial_metrics VALUES ('dividends_paid','2026-03-31',440750000,'10-Q','2026-05-05')", ())

    html = '<html><body>boosting its USD Reserve to $3.0 billion.</body></html>'
    ctx = bot.build_reserve_context('2026-07-13', html)

    assert ctx['usd_reserve_m'] == 3000.0
    assert ctx['reserve_prev_m'] == 2550.0
    assert ctx['reserve_change_m'] == 450.0
    # Months of coverage = reserve ÷ (official annual dividends / 12)
    assert ctx['annual_div_m'] == 1763.0
    assert ctx['div_source'] == 'xbrl_actual'
    assert ctx['runway_months'] == round(3000.0 / (1763.0 / 12.0), 1) == 20.4
    assert ctx['runway_infinite'] is False

    # The datapoint was stored for the weekly series
    conn = sqlite3.connect(temp_db)
    val = conn.execute("SELECT value FROM financial_metrics WHERE metric='usd_reserve' "
                       "AND period_end='2026-07-13'").fetchone()[0]
    conn.close()
    assert val == 3000000000.0


def test_build_reserve_context_none_without_statement(temp_db):
    assert bot.build_reserve_context('2026-07-13', '<html><body>no cash talk</body></html>') is None


# --- Telegram line -----------------------------------------------------------

def test_reserve_line_full():
    line = bot._reserve_line({
        'usd_reserve_m': 3000.0, 'reserve_change_m': 450.0,
        'runway_months': 20.4, 'annual_div_m': 1763.0,
    })
    assert '💵 Nakit (USD Reserve): **$3.00B**' in line
    assert '(+$450.0M)' in line
    assert 'yıllık ~$1.76B temettü gideriyle ~20 ay yeter' in line


def test_reserve_line_infinite_and_missing():
    assert bot._reserve_line({}) == ''
    line = bot._reserve_line({'usd_reserve_m': 2550.0, 'runway_infinite': True})
    assert 'tükenmiyor' in line


def test_alert_template_includes_reserve_line():
    parsed = {
        'event_type': 'btc_purchase', 'btc_signed_str': '4,225',
        'purchase_price': '$472.5M', 'avg_price': '$111,827',
        'total_holdings': '848,000', 'total_cost': '$46.1B', 'avg_cost': '$54,000',
        'total_debt': '$8.2B', 'purchase_period': 'Jul 7 - Jul 13, 2026',
        'usd_reserve_m': 3000.0, 'reserve_change_m': 450.0,
        'runway_months': 20.4, 'annual_div_m': 1763.0,
    }
    alert = bot.format_alert(parsed, 'https://sec.gov/x')
    assert 'Nakit (USD Reserve): **$3.00B** (+$450.0M)' in alert
    assert '~20 ay yeter' in alert


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
