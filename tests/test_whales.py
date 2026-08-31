"""The dashboard's "balinalara göre beklenti" panel.

Turns a tracked wallet's Polymarket position on an MSTR market into a plain
Turkish reading: a buy question held Yes reads "MSTR alacak", a sell question
held Yes reads "MSTR satacak", and so on. It is a bet, not a disclosure.
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

ADDR = "0xa0c37cb0587b0dd1542f794bcfa345762bba5b9a"


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / 'w.db')
    monkeypatch.setattr(bot, 'DB_PATH', path)
    monkeypatch.setattr(bot, 'INSIDER_WALLETS', [(ADDR, "Balina")])
    monkeypatch.setattr(bot, 'POLYMARKET_ENABLED', True)
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE polymarket_live (
        address TEXT NOT NULL, condition_id TEXT NOT NULL,
        asset TEXT NOT NULL DEFAULT '', outcome TEXT, title TEXT,
        event_slug TEXT, size REAL NOT NULL DEFAULT 0, avg_price REAL,
        cur_price REAL, redeemable INTEGER NOT NULL DEFAULT 0, end_date TEXT,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (address, condition_id, asset))""")
    conn.commit()
    conn.close()
    return path


def add(cid, title, outcome, size=1000, cur=0.72, avg=0.60,
        redeemable=0, end_date="", address=ADDR):
    conn = bot.get_db_connection()
    conn.execute("INSERT OR REPLACE INTO polymarket_live "
                 "(address, condition_id, asset, outcome, title, event_slug, "
                 " size, avg_price, cur_price, redeemable, end_date) "
                 "VALUES (?,?,?,?,?,'e',?,?,?,?,?)",
                 (address, cid, f"{cid}-{outcome}", outcome, title,
                  size, avg, cur, redeemable, end_date))
    conn.commit()
    conn.close()


# ------------------------------------------------------- the reading

@pytest.mark.parametrize("title,outcome,expected", [
    ("Will MicroStrategy buy more bitcoin this week?", "Yes", "alacak"),
    ("Will MicroStrategy buy more bitcoin this week?", "No", "almayacak"),
    ("Will MicroStrategy sell any bitcoin in 2026?", "Yes", "satacak"),
    ("Will MicroStrategy sell any bitcoin in 2026?", "No", "satmayacak"),
    # the company renamed; both names must read the same
    ("Will Strategy purchase bitcoin before September?", "Yes", "alacak"),
    ("Will Strategy liquidate part of its treasury?", "Yes", "satacak"),
])
def test_the_four_readings(title, outcome, expected):
    assert bot.whale_verdict(title, outcome) == expected


@pytest.mark.parametrize("title", [
    "Will MicroStrategy be added to the S&P 500?",
    "Will Saylor step down as chairman?",
    "Will MicroStrategy buy or sell bitcoin this month?",   # both — ambiguous
])
def test_a_question_we_cannot_classify_gets_no_verdict(title):
    """After this morning's false sale, we do not invent a reading we cannot
    derive. The market is still shown, just without a verdict."""
    assert bot.whale_verdict(title, "Yes") is None


# ------------------------------------------------------- the panel data

def test_only_mstr_markets_reach_the_page(db):
    add("c1", "Will MicroStrategy buy more bitcoin?", "Yes")
    add("c2", "Will Arsenal win the Premier League?", "Yes")

    titles = [m["title"] for m in bot.build_whale_expectations()["markets"]]
    assert titles == ["Will MicroStrategy buy more bitcoin?"]


def test_a_settled_market_is_not_an_expectation(db):
    add("c1", "Will Strategy buy bitcoin last week?", "Yes", redeemable=1)
    add("c2", "Will Strategy buy bitcoin next week?", "Yes")

    titles = [m["title"] for m in bot.build_whale_expectations()["markets"]]
    assert titles == ["Will Strategy buy bitcoin next week?"]


def test_a_missing_price_shows_nothing_rather_than_zero_percent(db):
    """_pm_num returns 0.0 for an absent field, so 0 cannot be told apart
    from "the API never sent this"."""
    add("c1", "Will Strategy buy bitcoin?", "Yes", cur=0.0, avg=0.5)

    m = bot.build_whale_expectations()["markets"][0]
    assert m["implied_pct"] is None


def test_both_legs_of_one_market_are_kept_and_ranked(db):
    add("c1", "Will Strategy buy bitcoin?", "Yes", size=5000, cur=0.7)
    add("c1", "Will Strategy buy bitcoin?", "No", size=100, cur=0.3)

    m = bot.build_whale_expectations()["markets"][0]
    assert [p["outcome"] for p in m["positions"]] == ["Yes", "No"]
    # the market reading follows the money, not the row order
    assert m["verdict"] == "alacak"


def test_the_market_verdict_follows_the_larger_stake(db):
    add("c1", "Will Strategy sell bitcoin?", "Yes", size=100, cur=0.5)
    add("c1", "Will Strategy sell bitcoin?", "No", size=9000, cur=0.5)

    assert bot.build_whale_expectations()["markets"][0]["verdict"] == "satmayacak"


def test_the_panel_is_empty_not_broken_when_disabled(db, monkeypatch):
    monkeypatch.setattr(bot, 'POLYMARKET_ENABLED', False)
    out = bot.build_whale_expectations()
    assert out == {"enabled": False, "fetched_at": None, "markets": []}


def test_the_route_returns_a_valid_shape_on_an_empty_db(db):
    payload = bot.app.test_client().get('/api/polymarket').get_json()
    assert payload["enabled"] is True and payload["markets"] == []


# ------------------------------------------------- isolation from the digest

def test_the_hourly_refresh_never_touches_the_digest_baseline(db, monkeypatch):
    """polymarket_positions is the digest's diff baseline and may only be
    written after a successful Telegram send. Writing it hourly for the
    website would make the digest silently lose movements."""
    conn = bot.get_db_connection()
    conn.execute("""CREATE TABLE polymarket_positions (
        address TEXT, condition_id TEXT, asset TEXT, outcome TEXT, title TEXT,
        event_slug TEXT, size REAL, avg_price REAL, cur_price REAL,
        redeemable INTEGER, end_date TEXT, snapshot_at TIMESTAMP,
        PRIMARY KEY (address, condition_id, asset))""")
    conn.execute("INSERT INTO polymarket_positions VALUES "
                 "(?, 'c1', 'a', 'Yes', 'old', 'e', 1, 0.5, 0.5, 0, '', NULL)",
                 (ADDR,))
    conn.commit()
    conn.close()

    monkeypatch.setattr(bot, 'fetch_polymarket_positions',
                        lambda addr, deadline: ([bot._normalise_position({
                            "conditionId": "c9", "asset": "t", "outcome": "Yes",
                            "title": "Will Strategy buy bitcoin?", "size": 500,
                            "avgPrice": 0.4, "curPrice": 0.6})], False))

    assert bot.refresh_polymarket_live() == 1

    conn = bot.get_db_connection()
    baseline = conn.execute("SELECT title FROM polymarket_positions").fetchall()
    live = conn.execute("SELECT title FROM polymarket_live").fetchall()
    conn.close()
    assert [r[0] for r in baseline] == ['old'], "the digest baseline was overwritten"
    assert [r[0] for r in live] == ['Will Strategy buy bitcoin?']


def test_a_failed_fetch_leaves_the_previous_snapshot(db, monkeypatch):
    add("c1", "Will Strategy buy bitcoin?", "Yes")
    monkeypatch.setattr(bot, 'fetch_polymarket_positions',
                        lambda addr, deadline: (None, False))

    assert bot.refresh_polymarket_live() == 0
    assert len(bot.build_whale_expectations()["markets"]) == 1
