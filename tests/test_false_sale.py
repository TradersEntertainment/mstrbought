"""The August 30, 2026 false-sale regression.

The bot announced to the channel:

    MSTR BTC SATTI: -839,172 BTC! (estimated from the balance difference)
    Remaining portfolio: 4,603 BTC | Cost: $369.7M (Avg: $80,318)

MSTR had *bought* 4,603 BTC that week. Two defects lined up:

1. The activity header did not match the literal 'BTC Acquired', so the
   combined table fell through to the holdings-only branch — which assumed
   the holdings block starts at column 0 and read the week's purchase
   columns as the entire treasury. ($369.7M / 4,603 = $80,318 exactly.)
2. With no activity parsed, the fallback subtracted that 4,603 from the
   843,775 on record and published the difference as a sale.
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

PREV_HOLDINGS = 843_775


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / 'test.db')
    monkeypatch.setattr(bot, 'DB_PATH', path)
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filing_date TEXT, period TEXT, btc_acquired TEXT, purchase_price TEXT,
        avg_price TEXT, total_holdings TEXT, total_cost TEXT, avg_cost TEXT,
        url TEXT, total_debt TEXT, financing_source TEXT, atm_sales TEXT,
        event_type TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute(
        "INSERT INTO purchase_history (filing_date, total_holdings, total_debt) "
        "VALUES (?, ?, ?)", ('2026-08-24', f'{PREV_HOLDINGS:,}', '$6.7B'))
    conn.commit()
    conn.close()
    return path


def combined_table(activity_header):
    """The real August 2026 layout: activity in columns 0-2, treasury in 3-5."""
    return [[
        ['During Period August 24, 2026 to August 30, 2026', 'As of August 30, 2026'],
        [activity_header,
         'Aggregate Purchase Price (in millions) (2)', 'Average Purchase Price (2)',
         'Aggregate BTC Holdings',
         'Aggregate Purchase Price (in billions) (2)', 'Average Purchase Price (2)'],
        ['4,603', '$', '369.7', '$', '80,318',
         '848,378', '$', '68.10', '$', '80,270'],
    ]]


@pytest.mark.parametrize("header", [
    'BTC Acquired (1)',
    'BTC Purchased (1)',      # a rewording must not break the parse
    'BTC Acquired (1)',  # nor a non-breaking space from the extractor
])
def test_a_purchase_is_read_as_a_purchase(db, header):
    data = bot.parse_btc_tables(combined_table(header))

    assert data["event_type"] == "btc_purchase"
    assert data["btc_signed_str"] == "4,603"
    assert data["total_holdings"] == "848,378"
    assert data["total_cost"] == "$68.10B"


def test_an_unreadable_activity_header_never_becomes_a_sale(db):
    """The exact failure, reproduced.

    Even with the activity column unrecognisable, the holdings block is found
    by its own header instead of being assumed to start at column 0 — so the
    treasury reads 848,378, not 4,603, and the delta against the previous
    843,775 is a 4,603 BTC purchase. Which is what happened.
    """
    data = bot.parse_btc_tables(combined_table('Digital Assets Added'))

    assert data["event_type"] != "btc_sale", (
        f"announced a sale of {data.get('btc_signed_str')} BTC from a table "
        f"containing no disposal")
    assert data["total_holdings"] == "848,378"
    assert data["btc_signed_str"] == "4,603"
    assert data["inferred"] is True     # honestly labelled as derived


def test_holdings_only_table_still_parses(db):
    """The branch that assumed column 0 must keep working where that is true."""
    data = bot.parse_btc_tables([[
        ['As of August 30, 2026'],
        ['Aggregate BTC Holdings', 'Aggregate Purchase Price (in billions)',
         'Average Purchase Price'],
        ['848,378', '$', '68.10', '$', '80,270'],
    ]])

    assert data["total_holdings"] == "848,378"
    assert data["event_type"] == "btc_purchase"     # inferred, and plausible
    assert data["inferred"] is True


def test_an_inferred_sale_is_refused(db):
    """No BTC Sold table anywhere: a negative delta reached only by
    subtraction is a parse failure, not news."""
    data = bot.parse_btc_tables([[
        ['As of August 30, 2026'],
        ['Aggregate BTC Holdings', 'Aggregate Purchase Price (in billions)',
         'Average Purchase Price'],
        ['4,603', '$', '0.36', '$', '80,318'],
    ]])

    assert data is None


def test_an_explicit_sale_is_still_reported(db):
    """The guardrail must not muzzle a disposal the filing actually states."""
    data = bot.parse_btc_tables([[
        ['During Period August 24, 2026 to August 30, 2026', 'As of August 30, 2026'],
        ['BTC Sold (1)', 'Aggregate Sale Price (in millions)', 'Average Sale Price',
         'Aggregate BTC Holdings',
         'Aggregate Purchase Price (in billions)', 'Average Purchase Price'],
        ['1,200', '$', '96.4', '$', '80,333',
         '842,575', '$', '67.70', '$', '80,300'],
    ]])

    assert data["event_type"] == "btc_sale"
    assert data["btc_signed_str"] == "-1,200"
    assert data.get("inferred") is not True


def test_the_migration_removes_the_bad_row_and_spares_the_good_ones(tmp_path, monkeypatch):
    """The August 30 row records 4,603 BTC held against 843,775 the week
    before. Left in place it puts a cliff in the chart and hands the next
    filing a nonsense baseline."""
    path = str(tmp_path / 'm.db')
    monkeypatch.setattr(bot, 'DB_PATH', path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, filing_date TEXT, period TEXT,
        btc_acquired TEXT, purchase_price TEXT, avg_price TEXT,
        total_holdings TEXT, total_cost TEXT, avg_cost TEXT, url TEXT,
        total_debt TEXT, financing_source TEXT, atm_sales TEXT, event_type TEXT)""")
    conn.execute("""CREATE TABLE processed_filings (
        accession_number TEXT PRIMARY KEY, filing_date TEXT, form TEXT, url TEXT)""")
    conn.execute("INSERT INTO processed_filings VALUES ('acc-bad', '2026-08-30', '8-K', 'u')")
    rows = [
        ('2026-08-17', '520',       '843,255', 'btc_purchase'),
        ('2026-08-24', '520',       '843,775', 'btc_purchase'),
        ('2026-08-30', '-839,172',  '4,603',   'btc_sale'),      # the bad one
    ]
    for date, acquired, holdings, kind in rows:
        conn.execute("INSERT INTO purchase_history "
                     "(filing_date, btc_acquired, total_holdings, event_type) "
                     "VALUES (?, ?, ?, ?)", (date, acquired, holdings, kind))
    conn.commit()

    bot._migrate_drop_false_sale_rows(conn)
    conn.commit()

    left = [r["filing_date"] for r in
            conn.execute("SELECT filing_date FROM purchase_history ORDER BY filing_date")]
    assert left == ['2026-08-17', '2026-08-24']

    # ...and the filing is unmarked, so the week can be parsed again. Deleting
    # only the history row left it processed forever — a hole the migration
    # could not close.
    assert conn.execute("SELECT COUNT(*) FROM processed_filings "
                        "WHERE filing_date='2026-08-30'").fetchone()[0] == 0


def test_the_migration_leaves_a_sale_the_filing_actually_stated(tmp_path, monkeypatch):
    """A disposal MSTR really reported must survive, however large."""
    path = str(tmp_path / 'm2.db')
    monkeypatch.setattr(bot, 'DB_PATH', path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, filing_date TEXT, period TEXT,
        btc_acquired TEXT, purchase_price TEXT, avg_price TEXT,
        total_holdings TEXT, total_cost TEXT, avg_cost TEXT, url TEXT,
        total_debt TEXT, financing_source TEXT, atm_sales TEXT, event_type TEXT)""")
    conn.execute("""CREATE TABLE processed_filings (
        accession_number TEXT PRIMARY KEY, filing_date TEXT, form TEXT, url TEXT)""")
    # A stated sale of half the treasury: extraordinary, but it is the
    # filing's own number, so it is not ours to delete.
    conn.execute("INSERT INTO purchase_history "
                 "(filing_date, btc_acquired, total_holdings, event_type) "
                 "VALUES ('2026-08-17', '520', '843,255', 'btc_purchase')")
    conn.execute("INSERT INTO purchase_history "
                 "(filing_date, btc_acquired, total_holdings, event_type) "
                 "VALUES ('2026-08-24', '-421,000', '422,255', 'btc_sale')")
    conn.commit()

    bot._migrate_drop_false_sale_rows(conn)
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM purchase_history").fetchone()[0] == 2
