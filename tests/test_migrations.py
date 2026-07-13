import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


def make_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    monkeypatch.setattr(bot, 'DB_PATH', db_path)
    return db_path


def create_schema(conn):
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
    conn.execute("""CREATE TABLE schema_migrations (
        migration_id TEXT PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")


def insert_bad_prod_rows(conn):
    """Replicate the exact broken state of the production database."""
    # July 6: only the first of two sale tables was parsed by old code,
    # and the amount was stored unsigned
    conn.execute(
        """INSERT INTO purchase_history
           (filing_date, period, btc_acquired, purchase_price, avg_price,
            total_holdings, total_cost, avg_cost, url, total_debt, financing_source)
           VALUES ('2026-07-06', 'June 29, 2026 to June 30, 2026', '1,363', '$80.8M',
                   '$59,256', '846,000', '$63.94B', '$75,578',
                   'https://www.sec.gov/Archives/edgar/data/1050446/000119312526295586/mstr-20260706.htm',
                   '$6.7B', '-')""")
    # July 13: the fabricated sale, stored unsigned as '2,225'
    conn.execute(
        """INSERT INTO purchase_history
           (filing_date, period, btc_acquired, purchase_price, avg_price,
            total_holdings, total_cost, avg_cost, url, total_debt, financing_source)
           VALUES ('2026-07-13', 'July 6, 2026 to July 12, 2026', '2,225', '-',
                   '-', '843,775', '$63.69B', '$75,476',
                   'https://www.sec.gov/Archives/edgar/data/1050446/000119312526300001/mstr-20260713.htm',
                   '$6.7B', '-')""")
    conn.commit()


def fetch_rows(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM purchase_history ORDER BY filing_date, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def test_migration_repairs_bad_prod_rows(tmp_path, monkeypatch):
    db_path = make_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    insert_bad_prod_rows(conn)

    bot.apply_data_migrations(conn)
    conn.close()

    rows = {r['filing_date']: r for r in fetch_rows(db_path)}

    july6 = rows['2026-07-06']
    assert july6['btc_acquired'] == '-3,588'
    assert july6['total_holdings'] == '843,775'
    assert july6['purchase_price'] == '$216.0M'
    assert july6['avg_price'] == '$60,197'
    assert july6['period'] == 'June 29, 2026 to July 5, 2026'
    assert july6['event_type'] == 'btc_sale'
    assert july6['financing_source'] == 'İmtiyazlı Hisse (STRC) Temettüsü'
    # The original prod URL must be preserved
    assert 'mstr-20260706.htm' in july6['url']

    july13 = rows['2026-07-13']
    assert july13['btc_acquired'] == '0'
    assert july13['total_holdings'] == '843,775'
    assert july13['financing_source'] == 'MSTR ATM Hisse Satışı ($466.7M)'
    assert july13['event_type'] == 'no_purchase'
    assert 'mstr-20260713.htm' in july13['url']


def test_migration_is_idempotent(tmp_path, monkeypatch):
    db_path = make_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    insert_bad_prod_rows(conn)

    bot.apply_data_migrations(conn)
    first = fetch_rows(db_path)

    bot.apply_data_migrations(conn)
    second = fetch_rows(db_path)
    conn.close()

    assert first == second
    assert len(second) == 2


def test_migration_content_guards_survive_lost_ledger(tmp_path, monkeypatch):
    """Even if schema_migrations is wiped, guarded re-runs stay harmless."""
    db_path = make_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    insert_bad_prod_rows(conn)

    bot.apply_data_migrations(conn)
    conn.execute("DELETE FROM schema_migrations")
    conn.commit()
    before = fetch_rows(db_path)

    bot.apply_data_migrations(conn)
    after = fetch_rows(db_path)
    conn.close()
    assert before == after


def test_migration_dedupes_july13_rows(tmp_path, monkeypatch):
    db_path = make_db(tmp_path, monkeypatch)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    insert_bad_prod_rows(conn)
    # A second (duplicate) July 13 row
    conn.execute(
        """INSERT INTO purchase_history
           (filing_date, period, btc_acquired, total_holdings)
           VALUES ('2026-07-13', 'x', '2,225', '843,775')""")
    conn.commit()

    bot.apply_data_migrations(conn)
    conn.close()

    rows = [r for r in fetch_rows(db_path) if r['filing_date'] == '2026-07-13']
    assert len(rows) == 1
    assert rows[0]['btc_acquired'] == '0'


def test_full_init_db_on_fresh_install(tmp_path, monkeypatch):
    """Fresh install: seed provides correct data; migration must not duplicate."""
    db_path = make_db(tmp_path, monkeypatch)

    bot.init_db()
    bot.init_db()  # second boot: everything must be a no-op

    rows = fetch_rows(db_path)
    july13 = [r for r in rows if r['filing_date'] == '2026-07-13']
    july6 = [r for r in rows if r['filing_date'] == '2026-07-06']
    assert len(july13) == 1
    assert july13[0]['btc_acquired'] == '0'
    assert len(july6) == 1
    assert july6[0]['btc_acquired'] == '-3,588'
    assert july6[0]['total_holdings'] == '843,775'
