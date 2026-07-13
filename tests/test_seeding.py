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
