import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


def test_db_seeding(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, 'DB_PATH', str(tmp_path / 'seed.db'))

    bot.init_db()

    conn = bot.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM purchase_history")
    history_count = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM purchase_history ORDER BY id DESC LIMIT 1")
    newest = cursor.fetchone()
    conn.close()

    # Derived from the seed list itself, not a hardcoded count
    assert history_count == len(bot.SEED_HISTORY)
    assert newest['filing_date'] == bot.SEED_HISTORY[0][0]
    assert newest['total_holdings'] == '843,775'


def test_seeding_only_runs_on_empty_table(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, 'DB_PATH', str(tmp_path / 'seed.db'))

    bot.init_db()
    bot.init_db()

    conn = bot.get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM purchase_history").fetchone()[0]
    conn.close()
    assert count == len(bot.SEED_HISTORY)


def test_restart_never_swallows_a_fresh_filing(tmp_path, monkeypatch):
    """A redeploy minutes after an 8-K must not mark it processed silently."""
    import sqlite3
    from datetime import datetime, timedelta

    db_path = str(tmp_path / 'restart.db')
    monkeypatch.setattr(bot, 'DB_PATH', db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE processed_filings (
        accession_number TEXT PRIMARY KEY, filing_date TEXT, form TEXT, url TEXT)""")
    conn.commit()

    today = datetime.now().date()
    data = {"filings": {"recent": {
        "form": ["8-K", "8-K", "8-K"],
        "accessionNumber": ["acc-today", "acc-yesterday", "acc-old"],
        "filingDate": [today.strftime("%Y-%m-%d"),
                       (today - timedelta(days=1)).strftime("%Y-%m-%d"),
                       (today - timedelta(days=30)).strftime("%Y-%m-%d")],
        "primaryDocument": ["a.htm", "b.htm", "c.htm"],
    }}}
    monkeypatch.setattr(bot, 'fetch_mstr_filings',
                        lambda use_conditional=True, return_state=False: data)

    bot.mark_current_filings_processed(conn)
    marked = {r[0] for r in conn.execute("SELECT accession_number FROM processed_filings")}
    conn.close()

    # Only the old filing is suppressed; today's and yesterday's still alert
    assert marked == {'acc-old'}
