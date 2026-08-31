"""The Gamma market catalogue: seeing markets nobody in the wallet list holds.

The wallet endpoint only ever reports positions someone already has, so a
market with no whale in it — like the owner's weekly "will MSTR announce a
purchase" market — is invisible to it. This is the layer that finds those.

polymarket.com is unreachable from the development environment, so every shape
here is pinned from Polymarket's own client (agents/polymarket/gamma.py) rather
than from a live call. The one thing that file documents explicitly is that
outcomePrices arrives as a JSON-encoded STRING, not a list.
"""
import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / 'm.db')
    monkeypatch.setattr(bot, 'DB_PATH', path)
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE polymarket_markets (
        condition_id TEXT PRIMARY KEY, slug TEXT, event_slug TEXT,
        question TEXT, outcomes TEXT, prices TEXT, end_date TEXT,
        closed INTEGER NOT NULL DEFAULT 0, volume REAL, yes_price REAL,
        alerted_price REAL,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()
    return path


class Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def market(question="Will MicroStrategy announce a Bitcoin purchase "
                    "September 1-7, 2026?",
           yes="0.63", no="0.37", cid="0xabc", slug="mstr-week"):
    """A Gamma market body, with the string-encoded arrays the API really sends."""
    return {
        "conditionId": cid,
        "slug": slug,
        "question": question,
        "outcomes": json.dumps(["Yes", "No"]),
        "outcomePrices": json.dumps([yes, no]),
        "clobTokenIds": json.dumps(["111", "222"]),
        "endDate": "2026-09-07T12:00:00Z",
        "closed": False,
        "volume": "125000.5",
    }


# ------------------------------------------------------- the price trap

def test_prices_arrive_as_a_json_string_not_a_list():
    """Polymarket's own client json.loads() these two fields. Reading them as
    lists returns nothing at all — silently, which is the dangerous part."""
    outcomes, prices = bot._gamma_prices(market())
    assert outcomes == ["Yes", "No"]
    assert prices == [0.63, 0.37]


def test_a_plain_list_is_accepted_too():
    """A string is what the API documents today; a list is what it would take
    to break this."""
    outcomes, prices = bot._gamma_prices(
        {"outcomes": ["Yes", "No"], "outcomePrices": [0.4, 0.6]})
    assert (outcomes, prices) == (["Yes", "No"], [0.4, 0.6])


@pytest.mark.parametrize("bad", ["", "not json", "{}", None, 17])
def test_an_unparseable_price_field_yields_no_price_not_an_exception(bad):
    assert bot._gamma_prices({"outcomes": bad, "outcomePrices": bad}) == ([], [])


def test_the_yes_leg_is_the_implied_probability():
    outcomes, prices = bot._gamma_prices(market(yes="0.81", no="0.19"))
    assert bot._yes_price(outcomes, prices) == 0.81


def test_yes_is_found_even_when_it_is_listed_second():
    assert bot._yes_price(["No", "Yes"], [0.3, 0.7]) == 0.7


def test_a_non_binary_market_falls_back_to_the_first_leg():
    assert bot._yes_price(["Above", "Below"], [0.55, 0.45]) == 0.55


# ------------------------------------------------------- row normalisation

def test_a_market_row_carries_what_the_panel_needs():
    row = bot._gamma_market_row(market())
    assert row["condition_id"] == "0xabc"
    assert row["yes_price"] == 0.63
    assert row["volume"] == 125000.5
    assert row["closed"] == 0
    assert row["end_date"].startswith("2026-09-07")


def test_a_non_mstr_market_is_dropped():
    assert bot._gamma_market_row(market(question="Will BTC hit 200k?")) is None


def test_a_market_without_a_condition_id_is_dropped():
    """condition_id is the join key to the whale positions. A row without one
    cannot be merged, so it is not stored."""
    m = market()
    del m["conditionId"]
    assert bot._gamma_market_row(m) is None


def test_a_nested_market_inherits_its_event_title():
    """Search answers with events; a market nested in one may carry no question
    of its own, and the event's title is the question."""
    m = market()
    del m["question"]
    row = bot._gamma_market_row(
        m, "Will MicroStrategy announce a Bitcoin purchase September 1-7, 2026?")
    assert row["question"].startswith("Will MicroStrategy announce")


def test_the_title_disambiguator_is_stripped_on_the_way_in():
    row = bot._gamma_market_row(
        market(question="Will MicroStrategy buy bitcoin in 2026?-bV81"))
    assert row["question"] == "Will MicroStrategy buy bitcoin in 2026?"


# ------------------------------------------------------- search envelopes

def test_markets_are_unwrapped_from_a_search_response():
    payload = {"events": [{
        "title": "Will MicroStrategy announce a Bitcoin purchase Sept 1-7?",
        "slug": "will-microstrategy-announce-a-bitcoin-purchase-september-1-7-2026",
        "markets": [market()],
    }], "tags": [], "profiles": []}
    pairs = bot._gamma_events_markets(payload)
    assert len(pairs) == 1
    _m, title, slug = pairs[0]
    assert title.startswith("Will MicroStrategy")
    assert slug.endswith("september-1-7-2026")


@pytest.mark.parametrize("payload", [
    [],                                  # bare array
    {"data": []},                        # paginated envelope
    {"events": []},                      # search envelope, nothing found
    {"error": "nope"},                   # something else entirely
    None,
    "a string",
])
def test_an_unrecognised_envelope_degrades_to_nothing_not_an_exception(payload):
    """This runs on a background thread. A shape we do not know must mean "no
    data", never a traceback that kills the refresh loop."""
    assert bot._gamma_events_markets(payload) == []


def test_an_event_that_is_already_market_shaped_is_used_directly():
    pairs = bot._gamma_events_markets([market()])
    assert len(pairs) == 1


# ------------------------------------------------------- fetch

def test_search_finds_the_weekly_market(monkeypatch):
    calls = []

    def fake_get(path, params, deadline):
        calls.append((path, params))
        return Resp({"events": [{
            "title": "Will MicroStrategy announce a Bitcoin purchase Sept 1-7?",
            "slug": "will-mstr-purchase-september-1-7-2026",
            "markets": [market()],
        }]})

    monkeypatch.setattr(bot, '_gamma_get', fake_get)
    monkeypatch.setattr(bot, 'POLYMARKET_SEARCH_TERMS', ["microstrategy"])
    found = bot.fetch_mstr_markets()
    assert [c[0] for c in calls] == ["/public-search"]
    assert len(found) == 1
    assert found[0]["yes_price"] == 0.63


def test_the_same_market_from_two_search_terms_is_stored_once(monkeypatch):
    monkeypatch.setattr(bot, '_gamma_get',
                        lambda p, q, d: Resp({"events": [
                            {"title": "t", "slug": "s", "markets": [market()]}]}))
    monkeypatch.setattr(bot, 'POLYMARKET_SEARCH_TERMS', ["microstrategy", "mstr"])
    assert len(bot.fetch_mstr_markets()) == 1


def test_paging_takes_over_when_search_returns_nothing(monkeypatch):
    """An empty search is not proof there is no market — it is an endpoint that
    could not be verified from here. Falling through is the whole point."""
    paths = []

    def fake_get(path, params, deadline):
        paths.append(path)
        if path == "/public-search":
            return Resp({"events": []})
        return Resp([market()] if params["offset"] == 0 else [])

    monkeypatch.setattr(bot, '_gamma_get', fake_get)
    monkeypatch.setattr(bot, 'POLYMARKET_SEARCH_TERMS', ["microstrategy"])
    monkeypatch.setattr(bot, 'POLYMARKET_MARKET_PAGE_SIZE', 1)
    found = bot.fetch_mstr_markets()
    assert "/markets" in paths
    assert len(found) == 1


def test_paging_takes_over_when_search_errors(monkeypatch):
    def fake_get(path, params, deadline):
        if path == "/public-search":
            return Resp({"detail": "gone"}, status=404)
        return Resp([market()] if params["offset"] == 0 else [])

    monkeypatch.setattr(bot, '_gamma_get', fake_get)
    monkeypatch.setattr(bot, 'POLYMARKET_SEARCH_TERMS', ["microstrategy"])
    monkeypatch.setattr(bot, 'POLYMARKET_MARKET_PAGE_SIZE', 1)
    assert len(bot.fetch_mstr_markets()) == 1


def test_a_dead_endpoint_yields_no_markets_rather_than_raising(monkeypatch):
    monkeypatch.setattr(bot, '_gamma_get', lambda p, q, d: None)
    assert bot.fetch_mstr_markets() == []


def test_paging_stops_at_a_short_page(monkeypatch):
    pages = []

    def fake_get(path, params, deadline):
        if path == "/public-search":
            return Resp({"events": []})
        pages.append(params["offset"])
        return Resp([market()])          # one row, page size is 2 -> short

    monkeypatch.setattr(bot, '_gamma_get', fake_get)
    monkeypatch.setattr(bot, 'POLYMARKET_SEARCH_TERMS', [])
    monkeypatch.setattr(bot, 'POLYMARKET_MARKET_PAGE_SIZE', 2)
    monkeypatch.setattr(bot, 'POLYMARKET_MARKET_PAGES', 9)
    bot.fetch_mstr_markets()
    assert pages == [0]


# ------------------------------------------------------- odds alerts

def _stub_send(monkeypatch, ok=True):
    sent = []

    def fake(parts):
        sent.append(parts)
        return ok

    monkeypatch.setattr(bot, 'send_telegram_digest', fake)
    return sent


def test_the_first_sighting_of_a_market_never_alerts(db, monkeypatch):
    """A market we have not seen before has no baseline to have moved from.
    Alerting on it would mean a burst of noise on every fresh deploy."""
    monkeypatch.setattr(bot, 'fetch_mstr_markets', lambda: [bot._gamma_market_row(market())])
    sent = _stub_send(monkeypatch)
    assert bot.refresh_mstr_markets() == 1
    assert sent == []

    conn = bot.get_db_connection()
    row = conn.execute("SELECT yes_price, alerted_price FROM "
                       "polymarket_markets").fetchone()
    conn.close()
    assert row["yes_price"] == 0.63 and row["alerted_price"] == 0.63


def test_a_small_drift_does_not_alert(db, monkeypatch):
    monkeypatch.setattr(bot, 'fetch_mstr_markets', lambda: [bot._gamma_market_row(market())])
    _stub_send(monkeypatch)
    bot.refresh_mstr_markets()

    monkeypatch.setattr(bot, 'fetch_mstr_markets',
                        lambda: [bot._gamma_market_row(market(yes="0.70"))])
    sent = _stub_send(monkeypatch)
    bot.refresh_mstr_markets()
    assert sent == []


def test_a_big_move_alerts_once_and_rebaselines(db, monkeypatch):
    monkeypatch.setattr(bot, 'fetch_mstr_markets', lambda: [bot._gamma_market_row(market())])
    _stub_send(monkeypatch)
    bot.refresh_mstr_markets()

    monkeypatch.setattr(bot, 'fetch_mstr_markets',
                        lambda: [bot._gamma_market_row(market(yes="0.90"))])
    sent = _stub_send(monkeypatch)
    bot.refresh_mstr_markets()
    assert len(sent) == 1
    assert "90" in "".join(sent[0])

    # The same price next hour is no longer news.
    sent2 = _stub_send(monkeypatch)
    bot.refresh_mstr_markets()
    assert sent2 == []


def test_slow_drift_still_reports_once_it_adds_up(db, monkeypatch):
    """Measured against the last ALERTED price, not the last seen one.

    Eight points an hour never trips a 20-point threshold if each hour is
    compared to the hour before it. Against the baseline, the same drift
    reports once it has actually gone 20 points.
    """
    all_sent = []
    for price in ("0.30", "0.38", "0.46", "0.53"):
        monkeypatch.setattr(bot, 'fetch_mstr_markets',
                            lambda p=price: [bot._gamma_market_row(market(yes=p))])
        sent = _stub_send(monkeypatch)
        bot.refresh_mstr_markets()
        all_sent.extend(sent)
    # 0.30 is the baseline; 0.38 and 0.46 are under 20 points from it, 0.53 is
    # 23 points and reports.
    assert len(all_sent) == 1
    assert "53" in "".join(all_sent[0])


def test_a_failed_send_does_not_advance_the_baseline(db, monkeypatch):
    """The alert must survive a Telegram outage. If alerted_price moved anyway,
    the move would be silently swallowed and never reported."""
    monkeypatch.setattr(bot, 'fetch_mstr_markets', lambda: [bot._gamma_market_row(market())])
    _stub_send(monkeypatch)
    bot.refresh_mstr_markets()

    monkeypatch.setattr(bot, 'fetch_mstr_markets',
                        lambda: [bot._gamma_market_row(market(yes="0.90"))])
    _stub_send(monkeypatch, ok=False)
    bot.refresh_mstr_markets()

    conn = bot.get_db_connection()
    row = conn.execute("SELECT alerted_price FROM polymarket_markets").fetchone()
    conn.close()
    assert row["alerted_price"] == 0.63        # still the old baseline

    # ...so the next refresh tries again.
    sent = _stub_send(monkeypatch)
    bot.refresh_mstr_markets()
    assert len(sent) == 1


def test_an_empty_fetch_leaves_the_stored_markets_alone(db, monkeypatch):
    """Same guard as the whale snapshot: an HTTP 200 with an empty body must
    not wipe the panel."""
    monkeypatch.setattr(bot, 'fetch_mstr_markets', lambda: [bot._gamma_market_row(market())])
    _stub_send(monkeypatch)
    bot.refresh_mstr_markets()

    monkeypatch.setattr(bot, 'fetch_mstr_markets', lambda: [])
    assert bot.refresh_mstr_markets() == 0

    conn = bot.get_db_connection()
    assert conn.execute("SELECT COUNT(*) FROM polymarket_markets").fetchone()[0] == 1
    conn.close()


def test_no_alert_path_writes_the_digest_baseline(db, monkeypatch):
    """polymarket_positions is the daily digest's diff baseline and may only be
    written after a successful digest send. The market refresh must not touch
    it — there is no such table here, and that must not raise."""
    monkeypatch.setattr(bot, 'fetch_mstr_markets',
                        lambda: [bot._gamma_market_row(market())])
    _stub_send(monkeypatch)
    bot.refresh_mstr_markets()      # would raise if it tried
