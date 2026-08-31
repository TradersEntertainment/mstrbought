"""Polymarket insider digest.

The data-api endpoints could not be reached from the machine this was written
on, so the fixtures below are SYNTHETIC — built from documentation, not from a
captured response. Every test that matters here is therefore about how the
code behaves when the API misbehaves, not about the happy path.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

ADDR = "0xa0c37cb0587b0dd1542f794bcfa345762bba5b9a"
OTHER = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"


class FakeResp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or json.dumps(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def position(condition_id, size, price=0.50, outcome="Evet",
             title="Fed Eylül'de faiz indirir mi?", redeemable=False,
             end_date="", asset=None):
    return {
        "conditionId": condition_id, "asset": asset or f"{condition_id}-tok",
        "outcome": outcome, "title": title, "eventSlug": "fed-eylul",
        "size": size, "avgPrice": price, "curPrice": price,
        "redeemable": redeemable, "endDate": end_date,
        "proxyWallet": ADDR,
    }


@pytest.fixture(autouse=True)
def reset(monkeypatch, tmp_path):
    monkeypatch.setattr(bot, 'DB_PATH', str(tmp_path / 'pm.db'))
    monkeypatch.setattr(bot, '_polymarket_shape_logged', True)
    monkeypatch.setattr(bot, '_pm_failure_streak', 0)
    monkeypatch.setattr(bot, '_source_stats', {})
    monkeypatch.setattr(bot, '_source_error_logged', {})
    monkeypatch.setattr(bot, 'INSIDER_WALLETS', [(ADDR, "Balina")])
    monkeypatch.setattr(bot, 'POLYMARKET_ENABLED', True)
    conn = sqlite3.connect(bot.DB_PATH)
    conn.executescript("""
        CREATE TABLE polymarket_positions (
            address TEXT NOT NULL, condition_id TEXT NOT NULL,
            asset TEXT NOT NULL DEFAULT '', outcome TEXT, title TEXT,
            event_slug TEXT, size REAL NOT NULL DEFAULT 0, avg_price REAL,
            cur_price REAL, redeemable INTEGER NOT NULL DEFAULT 0,
            end_date TEXT, snapshot_at TIMESTAMP,
            PRIMARY KEY (address, condition_id, asset));
        CREATE TABLE polymarket_digests (
            digest_date TEXT PRIMARY KEY, posted_at TIMESTAMP, status TEXT,
            movements INTEGER DEFAULT 0, addresses INTEGER DEFAULT 0, note TEXT);
    """)
    conn.commit()
    conn.close()


def seed(rows, address=ADDR):
    conn = bot.get_db_connection()
    bot.store_position_snapshot(conn, address, [bot._normalise_position(r) for r in rows])
    conn.commit()
    conn.close()


def serve(monkeypatch, payload, status=200):
    monkeypatch.setattr(bot.polymarket_session, 'get',
                        lambda url, params=None, timeout=None: FakeResp(status, payload))


# ---------------------------------------------------------------- addresses

def test_the_owners_profile_url_yields_the_address():
    """The link ends in '?via=betmoar'. Splitting on '=' to find a label
    would name the wallet 'betmoar' — or take the URL as the address."""
    got = bot.parse_insider_addresses(
        f"https://polymarket.com/profile/{ADDR}?via=betmoar")
    assert got == [(ADDR, f"{ADDR[:6]}…{ADDR[-4:]}")]


def test_a_named_profile_url_keeps_its_name():
    """The owner will paste links; they should still be able to name them."""
    got = bot.parse_insider_addresses(
        f"Balina=https://polymarket.com/profile/{ADDR}?via=betmoar")
    assert got == [(ADDR, "Balina")]


def test_an_unnamed_wallet_is_not_labelled_twice():
    block = bot.format_wallet_block(f"{ADDR[:6]}…{ADDR[-4:]}", ADDR, [], seeded=3)
    assert block.count(f"{ADDR[:6]}…{ADDR[-4:]}") == 1


def test_labels_addresses_and_urls_mix_freely():
    raw = f"Balina={ADDR}\n{OTHER.upper()}, https://polymarket.com/profile/{ADDR}"
    got = bot.parse_insider_addresses(raw)
    assert got == [(ADDR, "Balina"), (OTHER, f"{OTHER[:6]}…{OTHER[-4:]}")]


def test_a_checksummed_address_is_the_same_wallet():
    """Storing both cases would create two snapshots diffing forever."""
    mixed = "0xA0C37CB0587B0DD1542F794BCFA345762BBA5B9A"
    got = bot.parse_insider_addresses(f"{mixed},{ADDR}")
    assert [a for a, _ in got] == [ADDR]


def test_an_uppercase_0x_prefix_is_still_an_address():
    """Dropping a wallet over one character, silently, is a poor way to
    learn the list is misconfigured."""
    assert bot.parse_insider_addresses("0X" + ADDR[2:].upper()) == \
        [(ADDR, f"{ADDR[:6]}…{ADDR[-4:]}")]


@pytest.mark.parametrize("raw", ["", "not-an-address", "0x123", "0x" + "f" * 39])
def test_garbage_is_dropped_not_raised(raw):
    assert bot.parse_insider_addresses(raw) == []


def test_the_insider_cap_is_honoured(monkeypatch):
    monkeypatch.setattr(bot, 'POLYMARKET_MAX_INSIDERS', 2)
    raw = ",".join(f"0x{i:040x}" for i in range(1, 9))
    assert len(bot.parse_insider_addresses(raw)) == 2


# -------------------------------------------------------------- fetch layer

def test_a_wrapped_response_parses_like_a_bare_array():
    """The docs imply a bare array; other Polymarket surfaces wrap it. This
    could not be verified, so both must work."""
    rows = [position("c1", 100)]
    assert bot._as_rows(rows) == rows
    assert bot._as_rows({"data": rows}) == rows


@pytest.mark.parametrize("payload", [{"error": "x"}, "a string", [1, 2, 3], None, 42])
def test_an_unrecognised_shape_degrades_to_no_data(payload):
    assert bot._as_rows(payload) == []


def test_string_numerics_are_accepted():
    norm = bot._normalise_position({"conditionId": "c", "size": "1250.5",
                                    "avgPrice": "0.62"})
    assert norm["size"] == 1250.5 and norm["avg_price"] == 0.62


@pytest.mark.parametrize("status", [403, 429, 500])
def test_an_http_error_is_unknown_not_empty(monkeypatch, status):
    """None and [] must stay distinguishable: [] is 'holds nothing',
    None is 'we could not find out'. The zero-guard depends on it."""
    serve(monkeypatch, {}, status=status)
    rows, truncated = bot.fetch_polymarket_positions(ADDR, bot.time.time() + 5)
    assert rows is None and truncated is False


def test_a_non_json_body_is_unknown_not_empty(monkeypatch):
    """A bot challenge answers 200 with HTML."""
    monkeypatch.setattr(bot.polymarket_session, 'get',
                        lambda url, params=None, timeout=None:
                            FakeResp(200, None, text="<html>Just a moment…</html>"))
    rows, _ = bot.fetch_polymarket_positions(ADDR, bot.time.time() + 5)
    assert rows is None


def test_a_timeout_does_not_raise(monkeypatch):
    def boom(url, params=None, timeout=None):
        raise requests.exceptions.ReadTimeout("slow")
    monkeypatch.setattr(bot.polymarket_session, 'get', boom)
    assert bot.fetch_polymarket_positions(ADDR, bot.time.time() + 5) == (None, False)


# --------------------------------------------------------------------- diff

def norm(rows):
    return {(r["condition_id"], r["asset"]): r
            for r in (bot._normalise_position(x) for x in rows)}


def test_all_four_movement_kinds():
    prev = norm([position("keep", 1000), position("shrink", 1000),
                 position("gone", 1000)])
    cur = norm([position("keep", 3000), position("shrink", 200),
                position("fresh", 800)])
    kinds = {m["kind"]: m for m in bot.diff_positions(prev, cur)}

    assert kinds["increased"]["delta"] == 2000
    assert kinds["decreased"]["delta"] == -800
    assert kinds["opened"]["new_size"] == 800
    assert kinds["closed"]["prev_size"] == 1000


def test_dust_and_rounding_are_not_news():
    prev = norm([position("a", 10000), position("b", 1000)])
    cur = norm([position("a", 10200),                    # 2% — below the pct floor
                position("b", 900, price=0.01)])         # $1 — below the USD floor
    assert bot.diff_positions(prev, cur) == []


def test_a_resolved_market_is_not_a_sale():
    """A resolved position simply vanishes from the next snapshot. Calling
    that 'closed' is the biggest false-positive source in a snapshot diff."""
    yesterday = (bot.now_trt().date() - timedelta(days=2)).isoformat()
    prev = norm([position("done", 5000, redeemable=True),
                 position("expired", 5000, end_date=yesterday)])
    assert bot.diff_positions(prev, {}) == []


def test_a_truncated_fetch_never_reports_a_close():
    """A position missing from a capped page set was not closed; we simply
    did not look far enough."""
    prev = norm([position("a", 5000), position("b", 5000)])
    cur = norm([position("a", 9000)])
    kinds = [m["kind"] for m in bot.diff_positions(prev, cur, truncated=True)]
    assert kinds == ["increased"]


def test_both_legs_of_one_market_survive():
    """A wallet can hold Yes and No of the same conditionId; keyed on
    conditionId alone one leg would overwrite the other."""
    seed([position("c1", 100, outcome="Evet", asset="tok-yes"),
          position("c1", 200, outcome="Hayır", asset="tok-no")])
    conn = bot.get_db_connection()
    snap = bot.load_position_snapshot(conn, ADDR)
    conn.close()
    assert len(snap) == 2


# ------------------------------------------------------- orchestration

def test_a_first_sighting_is_seeded_not_announced_as_40_new_bets(monkeypatch):
    serve(monkeypatch, [position(f"c{i}", 500) for i in range(40)])
    result = bot.build_polymarket_digest()

    assert result["movements"] == 0
    assert result["wallets"][0]["seeded"] == 40


def test_an_empty_response_never_reads_as_liquidation(monkeypatch):
    """HTTP 200 + [] is what a well-formed but WRONG address returns, and
    what some edge failures return. A wallet we hold positions for coming
    back empty is a fetch problem, not a sell-everything."""
    seed([position("c1", 5000), position("c2", 5000)])
    serve(monkeypatch, [])
    result = bot.build_polymarket_digest()

    assert result["movements"] == 0
    assert result["pending"] == {}, "the good snapshot was overwritten"
    assert any("boş cevap" in e for e in result["errors"])


def test_a_genuinely_empty_wallet_is_accepted(monkeypatch):
    serve(monkeypatch, [])
    result = bot.build_polymarket_digest()
    assert result["errors"] == [] and result["wallets"][0]["seeded"] == 0


def test_the_snapshot_is_committed_only_after_a_successful_send(monkeypatch):
    """Writing first would mean a crash in between destroys the day's
    movements: the next run diffs new-against-new and sees nothing."""
    seed([position("c1", 1000)])
    serve(monkeypatch, [position("c1", 9000)])
    monkeypatch.setattr(bot, 'send_telegram_alert', lambda *a, **k: None)   # send fails

    res = bot.run_polymarket_digest()
    assert res["status"] == "send_failed"

    conn = bot.get_db_connection()
    size = conn.execute("SELECT size FROM polymarket_positions "
                        "WHERE address=? AND condition_id='c1'", (ADDR,)).fetchone()[0]
    conn.close()
    assert size == 1000, "snapshot advanced despite the send failing"

    # ...so the very same movement is still reported on the next run
    monkeypatch.setattr(bot, 'send_telegram_alert', lambda *a, **k: 7)
    again = bot.run_polymarket_digest(force=True)
    assert again["movements"] == 1


def test_the_same_day_is_not_posted_twice(monkeypatch):
    seed([position("c1", 1000)])
    serve(monkeypatch, [position("c1", 9000)])
    monkeypatch.setattr(bot, 'send_telegram_alert', lambda *a, **k: 7)

    assert bot.run_polymarket_digest()["status"] == "posted"
    assert bot.run_polymarket_digest()["status"] == "already_posted"
    assert bot.run_polymarket_digest(force=True)["status"] in ("posted", "empty")


def test_a_dry_run_sends_nothing_and_commits_nothing(monkeypatch):
    seed([position("c1", 1000)])
    serve(monkeypatch, [position("c1", 9000)])
    monkeypatch.setattr(bot, 'send_telegram_alert',
                        lambda *a, **k: pytest.fail("dry run must not post"))

    res = bot.run_polymarket_digest(dry_run=True)
    assert res["status"] == "dry" and res["parts"]

    conn = bot.get_db_connection()
    size = conn.execute("SELECT size FROM polymarket_positions "
                        "WHERE address=? AND condition_id='c1'", (ADDR,)).fetchone()[0]
    assert conn.execute("SELECT COUNT(*) FROM polymarket_digests").fetchone()[0] == 0
    conn.close()
    assert size == 1000


def test_a_total_failure_posts_nothing(monkeypatch):
    """A digest made entirely of error lines is noise."""
    serve(monkeypatch, {}, status=403)
    monkeypatch.setattr(bot, 'send_telegram_alert',
                        lambda *a, **k: pytest.fail("must stay quiet"))
    assert bot.run_polymarket_digest()["status"] == "failed"


# ----------------------------------------------------------- rendering

def test_telegram_counts_utf16_units_not_characters():
    """Every emoji is two units while len() reports one; a Python-len budget
    undercounts an emoji-led digest enough to blow past 4096."""
    assert len("🐋") == 1 and bot._tg_len("🐋") == 2


def test_an_untrusted_title_cannot_break_the_markdown():
    """One unbalanced * in a third-party title makes Telegram reject the
    WHOLE digest, losing every bold in it."""
    m = {"kind": "opened", "title": "Will *anyone* [win]_now?", "outcome": "Evet",
         "delta": 100, "new_size": 100, "prev_size": 0, "usd": 50, "pct": 100,
         "price": 0.5, "event_slug": ""}
    line = bot.format_movement(m)
    assert "*" not in line.replace("**", "") and "[" not in line and "_" not in line


def test_every_part_fits_and_no_block_is_split():
    blocks = [f"🐋 **W{i}**\n" + "\n".join(f"🟢 YENİ: {'x'*180} — Evet" for _ in range(8))
              for i in range(12)]
    parts = bot.split_telegram_blocks("🎯 **Başlık**", blocks, "📊 son satır")

    assert len(parts) > 1
    for p in parts:
        assert bot._tg_len(p) <= bot.TELEGRAM_TEXT_LIMIT
    assert "(1/" in parts[0] and "📊 son satır" in parts[-1]
    assert "📊 son satır" not in parts[0]


def test_an_oversized_block_is_clipped_not_dropped():
    parts = bot.split_telegram_blocks("H", ["y" * 9000], "F")
    assert len(parts) == 1 and "…" in parts[0]


def test_a_busy_wallet_is_capped_with_a_tail(monkeypatch):
    monkeypatch.setattr(bot, 'POLYMARKET_MAX_MOVES_PER_ADDR', 3)
    moves = [{"kind": "opened", "title": f"M{i}", "outcome": "Evet", "delta": 100,
              "new_size": 100, "prev_size": 0, "usd": 500, "pct": 100,
              "price": 0.5, "event_slug": ""} for i in range(9)]
    block = bot.format_wallet_block("Balina", ADDR, moves)
    assert "+6 hareket daha" in block


# ----------------------------------------------------------- scheduling

def trt(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=bot.TRT_TZ)


def test_the_digest_slot_is_weekdays_only():
    # 2026-08-31 is a Monday; 2026-09-05 a Saturday.
    assert bot.seconds_until_digest(trt(2026, 8, 31, 13, 0)) == 60 * 60
    sat = bot.seconds_until_digest(trt(2026, 9, 5, 13, 0))
    assert sat / 3600 > 24, "a weekend slot was scheduled"


def test_waiting_never_overshoots_the_slot():
    for hour in range(24):
        for minute in (0, 17, 43, 59):
            now = trt(2026, 8, 31, hour, minute)
            landed = now + timedelta(seconds=bot.seconds_until_digest(now))
            assert (landed.hour * 60 + landed.minute) == bot.POLYMARKET_DIGEST_MINUTE
            assert landed.weekday() < 5


def test_the_default_slot_clears_the_sec_window():
    """14:30 TRT would be 07:30 ET under US DST — the exact minute
    ULTRA_WINDOW_ET opens. 14:00 clears it in both offsets."""
    assert bot.POLYMARKET_DIGEST_MINUTE == 14 * 60
    for month in (8, 12):
        slot = trt(2026, month, 31 if month == 8 else 14, 14, 0)
        if slot.weekday() >= 5:
            slot += timedelta(days=2)
        mode, _, _ = bot.poll_schedule(slot.astimezone(bot.ET_TZ))
        assert mode != "Ultra High-Speed Mode"


def test_the_health_report_is_not_a_hardcoded_list(capsys):
    """A source could be counted, exposed on /api/status, and still never
    appear in the periodic log line."""
    bot._record_source('polymarket', True)
    bot.report_source_health(force=True)
    assert 'polymarket' in capsys.readouterr().out


# ------------------------------------------------------- digest schedule
#
# MSTR files its purchase 8-K on a Monday morning, so the whale's position is
# worth reporting on three days: Friday (the week's bets are in), Sunday (the
# last look before the weekend ends) and Monday (the last look before the
# announcement). Every other day was repeating what the hourly whale alert
# had already said.
#
# Reference week: 2026-08-31 is a Monday.

MON, TUE, WED, THU, FRI, SAT, SUN = (
    datetime(2026, 8, 31) + timedelta(days=i) for i in range(7))
DIGEST_H, DIGEST_M = divmod(14 * 60, 60)


def at(day, hh, mm=0):
    return day.replace(hour=hh, minute=mm, second=0)


@pytest.mark.parametrize("day,name", [
    (FRI, "Friday"), (SUN, "Sunday"), (MON, "Monday")])
def test_the_digest_posts_on_friday_sunday_and_monday(day, name):
    assert bot.digest_due(at(day, DIGEST_H, DIGEST_M)), name


@pytest.mark.parametrize("day,name", [
    (TUE, "Tuesday"), (WED, "Wednesday"), (THU, "Thursday"), (SAT, "Saturday")])
def test_the_digest_stays_quiet_the_rest_of_the_week(day, name):
    assert not bot.digest_due(at(day, DIGEST_H, DIGEST_M)), name


def test_it_is_not_due_before_its_hour():
    assert not bot.digest_due(at(FRI, DIGEST_H - 1, 59))


def test_a_late_wake_still_posts_within_the_catchup_window():
    """A restart or a slow tick must not skip the day entirely."""
    assert bot.digest_due(at(FRI, DIGEST_H, DIGEST_M + 30))
    assert not bot.digest_due(at(FRI, DIGEST_H + 3, DIGEST_M))


@pytest.mark.parametrize("now,expect_day,expect_hour", [
    # same day, before the hour
    (at(FRI, 13, 0), "Friday", 14),
    # after the hour rolls to the next allowed day
    (at(FRI, 15, 0), "Sunday", 14),
    (at(SUN, 15, 0), "Monday", 14),
    # Monday is the last of the three: the next one is Friday
    (at(MON, 15, 0), "Friday", 14),
    # a skipped day jumps the whole gap
    (at(TUE, 9, 0), "Friday", 14),
    (at(WED, 9, 0), "Friday", 14),
    (at(SAT, 9, 0), "Sunday", 14),
])
def test_the_sleep_lands_on_the_next_allowed_slot(now, expect_day, expect_hour):
    landed = now + timedelta(seconds=bot.seconds_until_digest(now))
    assert landed.strftime("%A") == expect_day
    assert landed.hour == expect_hour


def test_waking_from_the_sleep_always_finds_the_digest_due():
    """The bug this guards: seconds_until_digest sleeps towards one day while
    digest_due checks another. The loop wakes, says "not today", and the
    digest silently never posts. One set feeds both."""
    for day in (MON, TUE, WED, THU, FRI, SAT, SUN):
        for hour in (0, 9, 13, 14, 15, 23):
            now = at(day, hour)
            landed = now + timedelta(seconds=bot.seconds_until_digest(now))
            assert bot.digest_due(landed), f"{now} -> {landed}"


def test_the_monday_digest_lands_before_the_filing_window():
    """The owner's actual requirement: "pazartesi resmi açıklamadan önce".

    MSTR's 8-K arrives in the 07:30-09:30 ET band. TRT is a fixed UTC+3 while
    ET shifts with US DST, so this has to hold in both halves of the year —
    a TRT-anchored time that clears the window in August can sit inside it in
    January.
    """
    for label, day in [("summer", datetime(2026, 8, 31)),
                       ("winter", datetime(2026, 1, 5))]:
        assert day.strftime("%A") == "Monday", label
        trt = day.replace(hour=DIGEST_H, minute=DIGEST_M, tzinfo=bot.TRT_TZ)
        et = trt.astimezone(bot.ET_TZ)
        assert et.hour * 60 + et.minute < bot.ULTRA_WINDOW_ET[0], (
            f"{label}: digest at {et:%H:%M} ET is not before the filing band")


def test_no_configured_days_means_no_digest(monkeypatch):
    monkeypatch.setattr(bot, 'POLYMARKET_DIGEST_DAYS', frozenset())
    for day in (MON, TUE, WED, THU, FRI, SAT, SUN):
        assert not bot.digest_due(at(day, DIGEST_H, DIGEST_M))
    # ...and the loop still sleeps rather than spinning.
    assert bot.seconds_until_digest(at(MON, 9)) >= 60


@pytest.mark.parametrize("raw,expected", [
    ("fri,sun,mon", {4, 6, 0}),
    ("4,6,0", {4, 6, 0}),
    ("Friday, Sunday, Monday", {4, 6, 0}),
    ("MON;FRI", {0, 4}),
    ("", set()),
    ("nope,fri", {4}),          # a typo drops that day, never the process
    ("9,fri", {4}),             # out of range
])
def test_the_day_list_parses_names_and_numbers(raw, expected):
    assert set(bot._digest_days(raw)) == expected
