"""Regression tests for the adversarial-review findings (F2, F3, F5, F6)."""
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


# --- F2: zero/"-" legs in a multi-period breakdown must not double-sign ---

def test_breakdown_zero_leg_has_no_double_sign():
    parsed = {
        'event_type': 'btc_sale',
        'btc_abs_str': '1,363',
        'btc_signed_str': '-1,363',
        'total_holdings': '843,775',
        'purchase_period': 'x & y',
        'sale_breakdown': [
            {'type': 'sale', 'period': 'Week 1', 'btc_count': '1,363',
             'price': '$80.8M', 'avg_price': '$59,256', 'signed_count': -1363},
            {'type': 'sale', 'period': 'Week 2', 'btc_count': '-',
             'price': '-', 'avg_price': '-', 'signed_count': 0},
        ],
    }
    alert = bot.format_alert(parsed, 'http://example.com')
    assert '+-' not in alert
    assert '--' not in alert
    assert '0 BTC (işlem yok)' in alert
    assert '-1,363 BTC @ $59,256' in alert


# --- F3: mixed buy+sell filings aggregate money/avg per direction ---

MIXED_HTML = """
<table>
 <tr><td colspan="5">During Period August 1, 2026 to August 3, 2026</td></tr>
 <tr><td>BTC Acquired</td><td>Aggregate Purchase Price (in millions)</td><td>Average Purchase Price</td></tr>
 <tr><td>100</td><td>$</td><td>5.0</td><td>$</td><td>50,000</td></tr>
</table>
<table>
 <tr><td colspan="5">During Period August 4, 2026 to August 5, 2026</td></tr>
 <tr><td>BTC Sold</td><td>Aggregate Sale Price (in millions)</td><td>Average Sale Price</td></tr>
 <tr><td>30</td><td>$</td><td>1.8</td><td>$</td><td>60,000</td></tr>
</table>
<table>
 <tr><td colspan="5">As of August 5, 2026</td></tr>
 <tr><td>Aggregate BTC Holdings</td><td>Aggregate Purchase Price (in billions)</td><td>Average Purchase Price</td></tr>
 <tr><td>843,845</td><td>$</td><td>63.70</td><td>$</td><td>75,470</td></tr>
</table>
"""


def test_mixed_buy_sell_uses_direction_consistent_amounts(temp_db):
    result = bot.parse_table_fallback(MIXED_HTML)
    assert result['event_type'] == 'btc_purchase'
    assert result['btc_net_signed'] == 70
    # Only the purchase leg's money and average — not blended with the sale
    assert result['purchase_price'] == '$5.0M'
    assert result['avg_price'] == '$50,000'


# --- F6: footnote markers in price/avg/holdings cells ---

FOOTNOTE_HTML = """
<table>
 <tr><td colspan="5">During Period June 29, 2026 to June 30, 2026</td></tr>
 <tr><td>BTC Sold</td><td>Aggregate Sale Price (in millions)<sup>(2)</sup></td><td>Average Sale Price<sup>(2)</sup></td></tr>
 <tr><td>1,363<sup>(1)</sup></td><td>$</td><td>80.8<sup>(3)</sup></td><td>$</td><td>59,256<sup>(2)</sup></td></tr>
</table>
<table>
 <tr><td colspan="5">As of June 30, 2026</td></tr>
 <tr><td>Aggregate BTC Holdings</td><td>Aggregate Purchase Price (in billions)<sup>(2)</sup></td><td>Average Purchase Price<sup>(2)</sup></td></tr>
 <tr><td>846,000<sup>(4)</sup></td><td>$</td><td>63.94</td><td>$</td><td>75,578<sup>(2)</sup></td></tr>
</table>
"""


def test_footnote_markers_stripped_from_all_value_cells(temp_db):
    result = bot.parse_table_fallback(FOOTNOTE_HTML)
    assert result['event_type'] == 'btc_sale'
    assert result['purchase_price'] == '$80.8M'
    assert result['avg_price'] == '$59,256'
    assert result['total_holdings'] == '846,000'
    assert result['avg_cost'] == '$75,578'


# --- F5: duplicate-URL guard in save_to_database ---

def test_save_skips_duplicate_url(temp_db):
    parsed = {
        'event_type': 'no_purchase',
        'purchase_period': 'July 6, 2026 to July 12, 2026',
        'btc_signed_str': '0',
        'total_holdings': '843,775',
    }
    url = 'https://www.sec.gov/Archives/edgar/data/1050446/000119312526300100/mstr-20260713.htm'
    bot.save_to_database('2026-07-13', parsed, url, 'acc-1', '8-K')
    bot.save_to_database('2026-07-13', parsed, url, 'acc-1', '8-K')

    conn = sqlite3.connect(temp_db)
    count = conn.execute("SELECT COUNT(*) FROM purchase_history WHERE url = ?", (url,)).fetchone()[0]
    conn.close()
    assert count == 1
