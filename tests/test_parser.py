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
    """Isolated SQLite DB; bot.get_db_connection reads bot.DB_PATH at call time."""
    db_path = str(tmp_path / 'test.db')
    monkeypatch.setattr(bot, 'DB_PATH', db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filing_date TEXT, period TEXT, btc_acquired TEXT, purchase_price TEXT,
        avg_price TEXT, total_holdings TEXT, total_cost TEXT, avg_cost TEXT,
        url TEXT, total_debt TEXT, financing_source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE processed_filings (
        accession_number TEXT PRIMARY KEY, filing_date TEXT, form TEXT, url TEXT,
        parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()
    return db_path


def insert_prev_row(db_path, holdings, filing_date='2026-07-06'):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO purchase_history
           (filing_date, period, btc_acquired, purchase_price, avg_price,
            total_holdings, total_cost, avg_cost, url, total_debt, financing_source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (filing_date, 'prev period', '0', '-', '-', holdings,
         '$63.69B', '$75,476', 'http://example.com', '$6.7B', '-'))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# The July 13 incident: filing says "BTC Acquired: -" (no transaction) but the
# DB held a stale holdings value (846,000 instead of 843,775). The bot must
# report HOLD — never a fabricated sale from the holdings delta.
# ---------------------------------------------------------------------------

def test_july13_with_stale_db_reports_hold(temp_db, capsys):
    insert_prev_row(temp_db, '846,000')
    result = bot.parse_table_fallback(load_fixture('july13_hold_atm.html'))

    assert result is not None
    assert result['event_type'] == 'no_purchase'
    assert result['btc_signed_str'] == '0'
    assert result['btc_net_signed'] == 0
    assert result['inferred'] is False
    assert result['total_holdings'] == '843,775'
    assert result['total_cost'] == '$63.69B'
    assert result['avg_cost'] == '$75,476'

    # The stale DB must surface as a consistency warning, not as an event
    assert 'CONSISTENCY' in capsys.readouterr().out

    alert = bot.format_alert(result, 'http://example.com')
    assert 'SATTI' not in alert
    assert '843,775' in alert


def test_july13_with_fresh_db_reports_hold(temp_db, capsys):
    insert_prev_row(temp_db, '843,775')
    result = bot.parse_table_fallback(load_fixture('july13_hold_atm.html'))

    assert result['event_type'] == 'no_purchase'
    assert result['btc_signed_str'] == '0'
    assert 'CONSISTENCY' not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The July 6 filing: TWO sale periods in one filing (-1,363 and -2,225).
# Amounts come from the filing's own tables; holdings from the LAST snapshot.
# ---------------------------------------------------------------------------

def test_july06_double_sale_sums_periods(temp_db):
    insert_prev_row(temp_db, '847,363', filing_date='2026-06-29')
    result = bot.parse_table_fallback(load_fixture('july06_double_sale.html'))

    assert result['event_type'] == 'btc_sale'
    assert result['btc_net_signed'] == -3588
    assert result['btc_signed_str'] == '-3,588'
    assert result['btc_abs_str'] == '3,588'
    assert result['total_holdings'] == '843,775'
    assert result['purchase_price'] == '$216.0M'
    assert result['avg_price'] == '$60,197'
    assert len(result['sale_breakdown']) == 2
    assert result['inferred'] is False


def test_july06_double_sale_without_db_history(temp_db):
    # Activity tables are primary: event detection works with an empty DB too
    result = bot.parse_table_fallback(load_fixture('july06_double_sale.html'))
    assert result['event_type'] == 'btc_sale'
    assert result['btc_signed_str'] == '-3,588'


def test_july06_stale_db_triggers_warning_but_amount_from_tables(temp_db, capsys):
    # DB is nonsense (900,000) — amount must still come from the filing tables
    insert_prev_row(temp_db, '900,000')
    result = bot.parse_table_fallback(load_fixture('july06_double_sale.html'))
    assert result['event_type'] == 'btc_sale'
    assert result['btc_signed_str'] == '-3,588'
    assert 'CONSISTENCY' in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Normal purchase week (combined-format table)
# ---------------------------------------------------------------------------

def test_june22_purchase(temp_db):
    insert_prev_row(temp_db, '846,843', filing_date='2026-06-15')
    result = bot.parse_table_fallback(load_fixture('june22_purchase.html'))

    assert result['event_type'] == 'btc_purchase'
    assert result['btc_net_signed'] == 520
    assert result['btc_signed_str'] == '520'
    assert result['total_holdings'] == '847,363'
    assert result['purchase_price'] == '$34.9M'
    assert result['avg_price'] == '$67,068'


def test_no_btc_tables_returns_none(temp_db):
    result = bot.parse_table_fallback(load_fixture('atm_only.html'))
    assert result is None


# ---------------------------------------------------------------------------
# Sign hygiene: rendered alerts must never contain double signs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('fixture,prev', [
    ('july06_double_sale.html', '847,363'),
    ('june22_purchase.html', '846,843'),
    ('july13_hold_atm.html', '843,775'),
])
def test_alert_has_no_double_sign(temp_db, fixture, prev):
    insert_prev_row(temp_db, prev)
    result = bot.parse_table_fallback(load_fixture(fixture))
    alert = bot.format_alert(result, 'http://example.com')
    assert '+-' not in alert
    assert '--' not in alert
    assert '+0 BTC' not in alert
