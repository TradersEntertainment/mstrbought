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
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, alerted_size REAL,
        PRIMARY KEY (address, condition_id, asset))""")
    conn.execute("""CREATE TABLE polymarket_seen (
        address TEXT PRIMARY KEY,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE polymarket_markets (
        condition_id TEXT PRIMARY KEY, slug TEXT, event_slug TEXT,
        question TEXT, outcomes TEXT, prices TEXT, end_date TEXT,
        closed INTEGER NOT NULL DEFAULT 0, volume REAL, yes_price REAL,
        alerted_price REAL,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
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
    # A wallet that already has a snapshot has plainly been synced before.
    # The migration maintains exactly this invariant in production.
    conn.execute("INSERT OR IGNORE INTO polymarket_seen (address) VALUES (?)",
                 (address,))
    conn.commit()
    conn.close()


def add_market(cid, question, yes_price=0.63, closed=0, volume=50000.0,
               event_slug="an-event"):
    conn = bot.get_db_connection()
    conn.execute("INSERT OR REPLACE INTO polymarket_markets "
                 "(condition_id, slug, event_slug, question, outcomes, prices, "
                 " end_date, closed, volume, yes_price) "
                 "VALUES (?,?,?,?,'[\"Yes\", \"No\"]','[]','',?,?,?)",
                 (cid, event_slug, event_slug, question, closed, volume,
                  yes_price))
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


def test_the_panel_is_empty_not_broken_when_both_halves_are_off(db, monkeypatch):
    monkeypatch.setattr(bot, 'POLYMARKET_ENABLED', False)
    monkeypatch.setattr(bot, 'POLYMARKET_MARKETS_ENABLED', False)
    out = bot.build_whale_expectations()
    assert out == {"enabled": False, "fetched_at": None, "markets": []}


def test_the_market_list_does_not_need_a_wallet_list(db, monkeypatch):
    """The catalogue exists precisely for the market nobody tracked is in, so
    tying it to POLYMARKET_INSIDERS would defeat it. A deployment with no
    wallets still shows the weekly market and its odds."""
    monkeypatch.setattr(bot, 'POLYMARKET_ENABLED', False)
    add_market("c9", "Will MicroStrategy announce a Bitcoin purchase "
                     "September 1-7, 2026?", yes_price=0.63)

    out = bot.build_whale_expectations()
    assert out["enabled"] is True
    assert len(out["markets"]) == 1
    assert out["markets"][0]["market_pct"] == 63.0
    assert out["fetched_at"]           # the stamp falls back to the catalogue


def test_whale_rows_are_skipped_without_a_wallet_list(db, monkeypatch):
    """A stale snapshot from before the wallets were removed must not keep
    showing positions the bot is no longer tracking."""
    add("c1", "Will MicroStrategy buy more bitcoin?", "Yes")
    monkeypatch.setattr(bot, 'POLYMARKET_ENABLED', False)
    assert bot.build_whale_expectations()["markets"] == []


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


# ------------------------------------------------------- verb forms
#
# Polymarket writes its questions as gerunds ("announce selling any Bitcoin"),
# and the first version of this classifier matched only "sell|sells|sold". The
# panel went live saying "yorum yok" on a plainly readable sell question. Every
# form the real titles use is pinned here.

@pytest.mark.parametrize("title,expected", [
    ("Will Microstrategy announce selling any Bitcoin August 25-31?", "sell"),
    ("Will Microstrategy announce buying Bitcoin September 1-7?", "buy"),
    ("Will MicroStrategy announce a Bitcoin purchase September 1-7, 2026?", "buy"),
    ("Will Strategy be purchasing bitcoin this quarter?", "buy"),
    ("Will MicroStrategy have sold bitcoin by year end?", "sell"),
    ("Will Strategy be acquiring more BTC in October?", "buy"),
    ("Will MicroStrategy be accumulating bitcoin through Q4?", "buy"),
    ("Will Strategy be disposing of bitcoin holdings?", "sell"),
    ("Will MicroStrategy be offloading its BTC stack?", "sell"),
    ("Will Strategy be divesting from bitcoin?", "sell"),
])
def test_every_verb_form_the_real_titles_use(title, expected):
    assert bot.classify_mstr_market(title) == expected


@pytest.mark.parametrize("title,outcome,expected", [
    ("Will MicroStrategy announce holding 1M+ BTC by December 31?", "Yes",
     "tutacak"),
    ("Will MicroStrategy announce holding 1M+ BTC by December 31?", "No",
     "tutmayacak"),
    ("Will Strategy's bitcoin holdings reach 700k by June?", "Yes", "tutacak"),
    ("Will MicroStrategy's BTC stack surpass 800,000?", "Yes", "tutacak"),
])
def test_a_threshold_question_reads_as_hold(title, outcome, expected):
    """"Holding 1M+ by December" is neither a buy nor a sell question, but
    leaving it blank throws away a reading we can take literally."""
    assert bot.whale_verdict(title, outcome) == expected


@pytest.mark.parametrize("title", [
    "Will MicroStrategy be added to the S&P 500?",
    "Will Strategy be acquiring another company this year?",
    "Will MSTR stock reach $1000 in 2026?",
    "Will Saylor be selling his shares?",
])
def test_a_title_without_bitcoin_never_gets_a_reading(title):
    """The subject guard. Without it "be ADDED to the S&P 500" classified as a
    buy and the panel read "MSTR alacak" — an invented disclosure, the same
    class of error as this morning's false sale."""
    assert bot.classify_mstr_market(title) is None
    assert bot.whale_verdict(title, "Yes") is None


@pytest.mark.parametrize("raw,clean", [
    # Polymarket disambiguates duplicated questions with a short suffix.
    ("Will MicroStrategy buy bitcoin by December 31, 2026?-bV81",
     "Will MicroStrategy buy bitcoin by December 31, 2026?"),
    ("Will MSTR announce a purchase September 1-7?-a1",
     "Will MSTR announce a purchase September 1-7?"),      # two chars is one
    ("Will MSTR announce a purchase September 1-7?-x",
     "Will MSTR announce a purchase September 1-7?-x"),    # one char is not
    # A normal hyphenated title must survive untouched.
    ("Will MicroStrategy announce a bitcoin purchase September 1-7?",
     "Will MicroStrategy announce a bitcoin purchase September 1-7?"),
    ("Will Strategy buy bitcoin in the May 26-June 1 week?",
     "Will Strategy buy bitcoin in the May 26-June 1 week?"),
])
def test_the_title_suffix_is_stripped_without_eating_real_hyphens(raw, clean):
    assert bot.clean_market_title(raw) == clean


# ------------------------------------------------------- markets with no whale

def test_a_market_nobody_holds_still_reaches_the_panel(db):
    """The owner's weekly market had no position in it at all. The wallet
    endpoint can never surface that one — it only reports what someone holds —
    so the catalogue has to carry it."""
    add_market("c9", "Will MicroStrategy announce a Bitcoin purchase "
                     "September 1-7, 2026?", yes_price=0.63,
               event_slug="will-microstrategy-announce-a-bitcoin-purchase-september-1-7-2026")

    markets = bot.build_whale_expectations()["markets"]
    assert len(markets) == 1
    m = markets[0]
    assert m["positions"] == []
    assert m["market_pct"] == 63.0
    assert m["market_verdict"] == "alacak"       # odds above 50 on a buy question
    assert m["event_slug"].endswith("september-1-7-2026")


def test_odds_below_fifty_read_as_the_other_side(db):
    add_market("c9", "Will MicroStrategy announce a Bitcoin purchase "
                     "September 1-7, 2026?", yes_price=0.19)
    m = bot.build_whale_expectations()["markets"][0]
    assert m["market_pct"] == 19.0
    assert m["market_verdict"] == "almayacak"


def test_an_exact_coin_flip_gets_no_reading(db):
    add_market("c9", "Will MicroStrategy sell any bitcoin in 2026?",
               yes_price=0.50)
    assert bot.build_whale_expectations()["markets"][0]["market_verdict"] is None


def test_a_closed_market_is_not_an_open_expectation(db):
    add_market("c9", "Will MicroStrategy buy bitcoin last week?", closed=1)
    assert bot.build_whale_expectations()["markets"] == []


def test_a_whale_position_and_the_catalogue_merge_into_one_row(db):
    """Same condition_id from two sources must not produce two rows."""
    add("c1", "Will MicroStrategy buy more bitcoin?", "Yes", size=5000)
    add_market("c1", "Will MicroStrategy buy more bitcoin?", yes_price=0.71)

    markets = bot.build_whale_expectations()["markets"]
    assert len(markets) == 1
    assert len(markets[0]["positions"]) == 1
    assert markets[0]["market_pct"] == 71.0
    assert markets[0]["verdict"] == "alacak"


def test_markets_with_whale_money_rank_above_markets_without(db):
    add("c1", "Will MicroStrategy buy more bitcoin?", "Yes", size=5000)
    add_market("c2", "Will MicroStrategy announce a Bitcoin purchase "
                     "September 1-7, 2026?", volume=9_000_000.0)

    titles = [m["title"] for m in bot.build_whale_expectations()["markets"]]
    assert titles[0] == "Will MicroStrategy buy more bitcoin?"


def test_the_panel_survives_a_missing_catalogue_table(db):
    """The catalogue is the newer of the two tables. A deployment that has not
    migrated yet must degrade to whale-only, not to an empty panel."""
    conn = bot.get_db_connection()
    conn.execute("DROP TABLE polymarket_markets")
    conn.commit()
    conn.close()

    add("c1", "Will MicroStrategy buy more bitcoin?", "Yes")
    assert len(bot.build_whale_expectations()["markets"]) == 1


# ------------------------------------------------------- movement alerts

def _stub_send(monkeypatch, ok=True):
    sent = []

    def fake(parts):
        sent.append(parts)
        return ok

    monkeypatch.setattr(bot, 'send_telegram_digest', fake)
    return sent


def _stub_fetch(monkeypatch, rows, truncated=False):
    monkeypatch.setattr(bot, 'fetch_polymarket_positions',
                        lambda addr, deadline: (rows, truncated))


def pos(cid, title, outcome, size, cur=0.72, avg=0.60):
    return {"condition_id": cid, "asset": f"{cid}-{outcome}", "outcome": outcome,
            "title": title, "event_slug": "e", "size": size, "avg_price": avg,
            "cur_price": cur, "redeemable": 0, "end_date": ""}


BUY_Q = "Will MicroStrategy buy more bitcoin this week?"


def test_an_empty_response_does_not_wipe_the_panel(db, monkeypatch):
    """HTTP 200 with an empty list is what a well-formed but WRONG address
    returns, and what an edge failure can return. Storing it emptied the panel
    — and now that movements are alerted, it would also fire a "closed" notice
    for every open position the whale still holds."""
    add("c1", BUY_Q, "Yes", size=1000)
    _stub_fetch(monkeypatch, [])
    sent = _stub_send(monkeypatch)

    bot.refresh_polymarket_live()

    assert len(bot.build_whale_expectations()["markets"]) == 1
    assert sent == []


def test_a_truncated_fetch_does_not_report_a_phantom_exit(db, monkeypatch):
    """Hitting the page limit means we did not see every position. The ones we
    did not see are missing, not sold."""
    add("c1", BUY_Q, "Yes", size=1000)
    add("c2", "Will Strategy sell bitcoin in 2026?", "No", size=2000)
    # Only the first came back, and the fetch says it was cut short.
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 1000)], truncated=True)
    sent = _stub_send(monkeypatch)

    bot.refresh_polymarket_live()
    assert sent == []


def test_a_real_exit_is_reported_when_the_fetch_was_complete(db, monkeypatch):
    add("c1", BUY_Q, "Yes", size=1000)
    _stub_fetch(monkeypatch, [pos("c2", BUY_Q, "Yes", 500)], truncated=False)
    sent = _stub_send(monkeypatch)

    bot.refresh_polymarket_live()
    assert len(sent) == 1


def test_a_new_wallets_existing_bets_are_not_announced_as_movements(db, monkeypatch):
    """A wallet added to the config today must not produce an alert for every
    open bet it already had."""
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 1000)])
    sent = _stub_send(monkeypatch)

    bot.refresh_polymarket_live()
    assert sent == []


def test_a_size_increase_is_announced(db, monkeypatch):
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 1000)])
    _stub_send(monkeypatch)
    bot.refresh_polymarket_live()          # seeds the baseline

    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 9000)])
    sent = _stub_send(monkeypatch)
    bot.refresh_polymarket_live()
    assert len(sent) == 1


def test_a_failed_send_does_not_advance_the_alert_baseline(db, monkeypatch):
    """size tracks the site (which must stay fresh) and alerted_size tracks the
    alert (which must not be lost). A Telegram outage may cost a delay, never
    the movement itself."""
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 1000)])
    _stub_send(monkeypatch)
    bot.refresh_polymarket_live()

    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 9000)])
    _stub_send(monkeypatch, ok=False)
    bot.refresh_polymarket_live()

    conn = bot.get_db_connection()
    row = conn.execute("SELECT size, alerted_size FROM polymarket_live").fetchone()
    conn.close()
    assert row["size"] == 9000              # the page is up to date
    assert row["alerted_size"] == 1000      # the alert is still owed

    sent = _stub_send(monkeypatch)
    bot.refresh_polymarket_live()
    assert len(sent) == 1                   # and it is paid next hour


def test_a_non_mstr_movement_is_not_announced(db, monkeypatch):
    _stub_fetch(monkeypatch, [pos("c1", "Will the Fed cut rates in December?",
                                  "Yes", 1000)])
    _stub_send(monkeypatch)
    bot.refresh_polymarket_live()

    _stub_fetch(monkeypatch, [pos("c1", "Will the Fed cut rates in December?",
                                  "Yes", 9000)])
    sent = _stub_send(monkeypatch)
    bot.refresh_polymarket_live()
    assert sent == []


def test_closing_every_position_is_kept_quiet_on_purpose(db, monkeypatch):
    """A deliberate blind spot, worth naming.

    An empty response cannot be told apart from a wrong address or an edge
    failure, so it is never treated as a close-out. The cost is that a whale
    exiting EVERYTHING goes unreported; the alternative cost was a false
    "closed" notice for every open bet whenever the API hiccupped, which is
    what this guard was added for. Partial exits are still reported, because
    those arrive alongside positions that prove the response was real.
    """
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 1000)])
    _stub_send(monkeypatch)
    bot.refresh_polymarket_live()          # first sync, silent

    _stub_fetch(monkeypatch, [])
    sent = _stub_send(monkeypatch)
    bot.refresh_polymarket_live()
    assert sent == []

    # And the panel keeps showing the last thing we actually saw.
    assert len(bot.build_whale_expectations()["markets"]) == 1


def test_the_first_sync_marker_is_not_the_snapshot_being_empty(db, monkeypatch):
    """Keying "first sync" off an empty snapshot would conflate two different
    states. The marker survives the snapshot being rewritten."""
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 1000)])
    _stub_send(monkeypatch)
    bot.refresh_polymarket_live()

    conn = bot.get_db_connection()
    seen = conn.execute("SELECT COUNT(*) FROM polymarket_seen").fetchone()[0]
    conn.close()
    assert seen == 1

    # Second sync is no longer a first sync, so a change is announced.
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 8000)])
    sent = _stub_send(monkeypatch)
    bot.refresh_polymarket_live()
    assert len(sent) == 1


def test_an_existing_snapshot_counts_as_already_synced():
    """Upgrading a running deployment must not swallow a cycle of movements:
    a wallet that already has rows has obviously been synced before."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'u.db')
        conn = sqlite3.connect(path)
        conn.execute("""CREATE TABLE polymarket_live (
            address TEXT NOT NULL, condition_id TEXT NOT NULL,
            asset TEXT NOT NULL DEFAULT '', outcome TEXT, title TEXT,
            event_slug TEXT, size REAL NOT NULL DEFAULT 0, avg_price REAL,
            cur_price REAL, redeemable INTEGER NOT NULL DEFAULT 0,
            end_date TEXT, fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            alerted_size REAL,
            PRIMARY KEY (address, condition_id, asset))""")
        conn.execute("INSERT INTO polymarket_live (address, condition_id, "
                     "asset, size) VALUES (?, 'c1', 'a1', 500)", (ADDR,))
        conn.commit()
        conn.close()

        old_path = bot.DB_PATH
        bot.DB_PATH = path
        try:
            bot.init_db()
            conn = bot.get_db_connection()
            seen = conn.execute("SELECT address FROM polymarket_seen").fetchall()
            conn.close()
        finally:
            bot.DB_PATH = old_path
        assert [r["address"] for r in seen] == [ADDR]


def test_the_panel_shows_the_owners_two_markets_correctly(db):
    """The exact rows from the screenshot that read "yorum yok".

    Both were plainly readable questions: the first said "announce SELLING"
    (the classifier only knew sell/sells/sold) and the second was a threshold
    question with a disambiguator suffix the page never stripped.
    """
    add("c1", "Will Microstrategy announce selling any Bitcoin August 25-31?",
        "No", size=790, cur=1.0, avg=1.0)
    add("c2", "Will MicroStrategy announce holding 1M+ BTC by "
              "December 31, 2026?-bV81", "Yes", size=1600, cur=0.12, avg=0.12)

    by_title = {m["title"]: m for m in bot.build_whale_expectations()["markets"]}

    sell = by_title["Will Microstrategy announce selling any Bitcoin "
                    "August 25-31?"]
    assert sell["verdict"] == "satmayacak"

    # The suffix is gone from the title the page renders.
    hold = by_title["Will MicroStrategy announce holding 1M+ BTC by "
                    "December 31, 2026?"]
    assert hold["verdict"] == "tutacak"
    assert "bV81" not in hold["title"]


def test_a_whale_position_survives_the_catalogue_topic_filter(db):
    """The subject filter culls the catalogue, never the whale rows.

    Money is information. If the tracked wallet backs "Will MicroStrategy be
    margin called in 2026?", that belongs on the panel — unreadable, so shown
    without a verdict, which is what an unclassifiable question has always
    done here.
    """
    add("c1", "Will MicroStrategy be margin called in 2026?", "Yes", size=5000)

    markets = bot.build_whale_expectations()["markets"]
    assert len(markets) == 1
    assert markets[0]["verdict"] is None
    assert markets[0]["positions"][0]["size"] == 5000


def test_the_panel_after_the_cull_is_only_readable_markets(db):
    """The shape the owner asked for: no "yorum yok" rows from the catalogue."""
    add_market("c1", "Will Microstrategy announce a Bitcoin purchase "
                     "September 1-7?", yes_price=0.18)
    add_market("c2", "Will Microstrategy announce selling any Bitcoin "
                     "September 1-7?", yes_price=0.17)

    markets = bot.build_whale_expectations()["markets"]
    assert len(markets) == 2
    assert all(m["market_verdict"] for m in markets)


# ------------------------------------------------------- the alert headline
#
# The owner's ask, verbatim: "MicroStrategy Insider balinası bu hafta bitcoin
# alınmayacak beti alıyor ... ilk satırda her şeyi söyleyip sonra alta
# detayları yazacak". An address and an English market title tell a reader
# nothing at a glance.

from datetime import timedelta


def move(kind="opened", title="Will Microstrategy announce a Bitcoin purchase "
                              "September 1-7?", outcome="No", usd=900.0,
         end_date=None, days_out=5):
    if end_date is None:
        end_date = (bot.now_trt().date() + timedelta(days=days_out)).isoformat()
    return {"kind": kind, "title": title, "outcome": outcome, "event_slug": "e",
            "end_date": end_date, "usd": usd, "pct": 100.0, "price": 0.18,
            "delta": 5000, "new_size": 5000, "prev_size": 0}


def test_the_headline_is_the_sentence_the_owner_asked_for():
    assert bot.whale_headline("Balina", [move()]) == (
        "🐋 **MicroStrategy Insider balinası bu hafta "
        "bitcoin alınmayacak beti alıyor**")


def test_the_other_side_of_the_same_market():
    assert "bitcoin alınacak beti alıyor" in bot.whale_headline(
        "Balina", [move(outcome="Yes")])


@pytest.mark.parametrize("kind,verb", [
    ("opened", "beti alıyor"),
    ("increased", "betini büyütüyor"),
    ("decreased", "betini azaltıyor"),
    ("closed", "betini kapatıyor"),
])
def test_every_kind_of_movement_reads_as_a_sentence(kind, verb):
    assert verb in bot.whale_headline("Balina", [move(kind=kind)])


@pytest.mark.parametrize("outcome,phrase", [
    ("Yes", "bitcoin alınacak"),
    ("No", "bitcoin alınmayacak"),
])
def test_a_buy_question_reads_from_bitcoins_side(outcome, phrase):
    assert bot.whale_bet_phrase(
        "Will Microstrategy announce a Bitcoin purchase September 1-7?",
        outcome) == phrase


@pytest.mark.parametrize("outcome,phrase", [
    ("Yes", "bitcoin satılacak"),
    ("No", "bitcoin satılmayacak"),
])
def test_a_sell_question_reads_from_bitcoins_side(outcome, phrase):
    assert bot.whale_bet_phrase(
        "Will Microstrategy announce selling any Bitcoin September 1-7?",
        outcome) == phrase


def test_a_threshold_question_reads_from_bitcoins_side():
    assert bot.whale_bet_phrase(
        "Will MicroStrategy announce holding 1M+ BTC by December 31, 2026?",
        "Yes") == "bitcoin hedefi tutulacak"


# ------------------------------------------------------- when

@pytest.mark.parametrize("days,expected", [
    (0, "bu hafta"),
    (5, "bu hafta"),
    (7, "bu hafta"),
    (8, "bu ay"),
    (31, "bu ay"),
])
def test_the_timeframe_comes_from_the_end_date_not_the_title(days, expected):
    """"September 1-7" is text, and reading meaning out of Polymarket's title
    text has broken this bot three times. end_date is a structured field."""
    end = (bot.now_trt().date() + timedelta(days=days)).isoformat()
    assert bot.bet_timeframe(end) == expected


def test_a_distant_market_gets_a_real_date():
    from datetime import date
    assert bet_tf("2026-12-31", date(2026, 8, 31)) == "31 Aralık'a kadar"
    assert bet_tf("2026-09-30", date(2026, 6, 1)) == "30 Eylül'e kadar"
    assert bet_tf("2026-10-15", date(2026, 6, 1)) == "15 Ekim'e kadar"


def bet_tf(end, today):
    return bot.bet_timeframe(end, today=today)


@pytest.mark.parametrize("end", ["", None, "not-a-date", "2026-13-45", "2026"])
def test_an_unusable_end_date_claims_no_timeframe(end):
    """Better a headline with no "bu hafta" than a wrong one."""
    assert bot.bet_timeframe(end) == ""


def test_a_market_that_already_ended_claims_no_timeframe():
    past = (bot.now_trt().date() - timedelta(days=3)).isoformat()
    assert bot.bet_timeframe(past) == ""


def test_the_headline_drops_the_timeframe_rather_than_guessing():
    head = bot.whale_headline("Balina", [move(end_date="")])
    assert "bitcoin alınmayacak beti alıyor" in head
    assert "bu hafta" not in head


# ------------------------------------------------------- more than one move

def test_several_movements_lead_with_the_biggest():
    head = bot.whale_headline("Balina", [
        move(usd=300.0, outcome="Yes"),
        move(usd=5000.0, outcome="No", title="MicroStrategy announces >1000 "
                                             "BTC purchase September 1-7?"),
    ])
    assert "bitcoin alınmayacak" in head.split("\n")[0]


def test_movements_pointing_the_same_way_just_count_the_rest():
    head = bot.whale_headline("Balina", [
        move(usd=5000.0, outcome="No"),
        move(usd=300.0, outcome="No", title="MicroStrategy announces >1000 "
                                            "BTC purchase September 1-7?"),
    ])
    assert "+1 hareket daha" in head


def test_movements_pointing_opposite_ways_say_so():
    """Two bets in opposite directions must not be blended into one confident
    verdict — the headline names the biggest and admits that is what it is."""
    head = bot.whale_headline("Balina", [
        move(usd=5000.0, outcome="No"),
        move(usd=300.0, outcome="Yes", title="MicroStrategy announces >1000 "
                                             "BTC purchase September 1-7?"),
    ])
    assert "en büyük hareket" in head


# ------------------------------------------------------- honesty

def test_an_unreadable_question_gets_no_invented_headline():
    head = bot.whale_headline(
        "Balina", [move(title="Will MicroStrategy be margin called in 2026?")])
    assert "yeni pozisyon açıyor" in head
    for invented in ("bitcoin alınacak", "bitcoin alınmayacak", "bu hafta"):
        assert invented not in head


def test_a_second_wallet_is_named_so_the_alerts_stay_apart():
    one = bot.whale_headline("Balina", [move()], wallet_count=1)
    many = bot.whale_headline("Balina", [move()], wallet_count=3)
    assert "(Balina)" not in one
    assert "(Balina)" in many


def test_the_whole_alert_leads_with_the_sentence_then_the_detail(db, monkeypatch):
    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 1000)])
    _stub_send(monkeypatch)
    bot.refresh_polymarket_live()

    _stub_fetch(monkeypatch, [pos("c1", BUY_Q, "Yes", 9000)])
    sent = _stub_send(monkeypatch)
    bot.refresh_polymarket_live()

    text = "".join(sent[0])
    first = text.split("\n")[0]
    assert first.startswith("🐋 **MicroStrategy Insider balinası")
    assert "betini büyütüyor**" in first
    # ...and the numbers are below it, not in it.
    assert "9.000" in text and "9.000" not in first
