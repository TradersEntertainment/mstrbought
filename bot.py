import gzip
import os
import time
import json
import sqlite3
import threading
import urllib.request
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup, SoupStrainer
import telebot
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_PATH = os.getenv("DB_PATH", "mstr_state.db")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ----------------- CLOCKS -----------------
# EDGAR disseminates on the US Eastern clock and Turkey sits on a fixed
# UTC+3. Anchoring the fast-poll windows to Turkish local time — as this bot
# did — silently shifts every window by a full hour at each US DST
# transition. MSTR's weekly 8-K lands in a tight 07:55-08:25 ET band, which
# is 14:55-15:25 TRT in summer but 15:55-16:25 TRT in winter, i.e. entirely
# outside the old 14:30-15:15 TRT window for roughly five months a year.
# Every window below is therefore expressed in US Eastern.
try:
    from zoneinfo import ZoneInfo
    ET_TZ = ZoneInfo("America/New_York")
except Exception as _tz_err:  # pragma: no cover - only if tzdata is missing
    print(f"WARNING: falling back to fixed-offset US Eastern ({_tz_err}); "
          f"install tzdata so DST is handled correctly.")
    ET_TZ = timezone(timedelta(hours=-5))

TRT_TZ = timezone(timedelta(hours=3))

def now_et():
    return datetime.now(timezone.utc).astimezone(ET_TZ)

def now_trt():
    return datetime.now(timezone.utc).astimezone(TRT_TZ)

# Optimization: critical poll interval is 0.25s (250ms) by default now
# NORMAL used to be 300s, which meant anything landing outside the narrow
# fast band was found up to five minutes late. EDGAR only disseminates
# 06:00-22:00 ET on business days, so an overnight tick is nearly free.
POLL_INTERVAL_NORMAL = float(os.getenv("POLL_INTERVAL_NORMAL", "60"))
POLL_INTERVAL_CRITICAL = float(os.getenv("POLL_INTERVAL_CRITICAL", "0.25"))
POLL_INTERVAL_FAST = float(os.getenv("POLL_INTERVAL_FAST", "2"))

# Windows in US Eastern minutes-of-day, weekdays only.
#   ULTRA covers the observed 07:55-08:25 ET filing band with margin on both
#   sides (and the 09:04 ET outlier seen in the record). 07:30-09:30 ET is
#   14:30-16:30 Turkish time in summer and 15:30-17:30 in winter — the window
#   is deliberately pinned to the SEC's clock, not Turkey's, so it travels
#   with the filings across the DST change instead of sliding off them.
#   FAST covers the rest of EDGAR's dissemination day, so the non-BTC 8-Ks
#   that land at 16:11 / 16:27 / 17:22 ET are seconds late, not minutes.
def _win(env, default_start, default_end):
    raw = os.getenv(env, "").strip()
    if raw:
        try:
            a, b = raw.split("-")
            ah, am = (int(x) for x in a.strip().split(":"))
            bh, bm = (int(x) for x in b.strip().split(":"))
            return ah * 60 + am, bh * 60 + bm
        except Exception:
            print(f"Ignoring malformed {env}={raw!r}; expected 'HH:MM-HH:MM' ET.")
    return default_start, default_end

ULTRA_WINDOW_ET = _win("ULTRA_WINDOW_ET", 7 * 60 + 30, 9 * 60 + 30)
FAST_WINDOW_ET = _win("FAST_WINDOW_ET", 6 * 60, 18 * 60)

def describe_poll_config():
    """One line stating the cadence actually in effect.

    Env vars override these constants, and the mode-change line only prints
    when a window boundary is crossed — so on a weekend, or any quiet
    stretch, there was no way to confirm a config change had taken effect
    without waiting for the next trading morning. This prints at boot.
    """
    us, ue = ULTRA_WINDOW_ET
    fs, fe = FAST_WINDOW_ET
    warn = ""
    if POLL_INTERVAL_CRITICAL > 1.0:
        warn = ("  <-- WARNING: the ultra window is slower than 1s/tick; "
                "POLL_INTERVAL_CRITICAL is meant to be ~0.25")
    return (f"Poll config: ultra {us//60:02d}:{us%60:02d}-{ue//60:02d}:{ue%60:02d} ET "
            f"@{POLL_INTERVAL_CRITICAL}s | "
            f"fast {fs//60:02d}:{fs%60:02d}-{fe//60:02d}:{fe%60:02d} ET "
            f"@{POLL_INTERVAL_FAST}s | normal @{POLL_INTERVAL_NORMAL}s | "
            f"now {now_et():%Y-%m-%d %H:%M:%S %Z}{warn}")

def poll_schedule(now):
    """Pick the poll cadence for a US-Eastern datetime.

    Returns (mode, interval, seconds_until_this_bucket_can_change).

    The third value is what stops the loop sleeping straight through a
    window opening. The old loop chose an interval once and then slept it
    out, so a tick landing at 13:59 slept until 14:04 — five minutes of
    total blindness starting one minute before the fast window opened.
    Sleeping no longer than the distance to the next boundary makes the
    window open on time, whatever cadence preceded it.
    """
    minute = now.hour * 60 + now.minute
    if now.weekday() >= 5:
        # EDGAR does not disseminate at weekends. Next boundary is Monday.
        secs = ((7 - now.weekday()) * 24 * 60 - minute) * 60 - now.second
        return "Normal Mode", POLL_INTERVAL_NORMAL, max(secs, 60)

    def until(*edges):
        ahead = [(e - minute) * 60 - now.second for e in edges]
        ahead = [a for a in ahead if a > 0]
        # Midnight always ends the current bucket (the weekday may change).
        ahead.append((24 * 60 - minute) * 60 - now.second)
        return max(min(ahead), 1)

    us, ue = ULTRA_WINDOW_ET
    fs, fe = FAST_WINDOW_ET
    edges = (us, ue, fs, fe)
    if us <= minute < ue:
        return "Ultra High-Speed Mode", POLL_INTERVAL_CRITICAL, until(*edges)
    if fs <= minute < fe:
        return "Fast Mode", POLL_INTERVAL_FAST, until(*edges)
    return "Normal Mode", POLL_INTERVAL_NORMAL, until(*edges)

# Global states
current_mode = "Normal Mode"
last_checked_time = None
# Wall-clock of the last completed poll tick; /health reads it to tell a
# wedged loop apart from a quiet one.
_last_tick_time = 0.0
running = True

# Initialize Telegram Bot
bot = None
if TELEGRAM_BOT_TOKEN:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Initialize Flask App
app = Flask(__name__)

# ----------------- RESPONSE COMPRESSION & CACHING -----------------
# Railway serves Flask responses as-is (no edge gzip): compress text
# bodies ourselves and long-cache the versioned (?v=N) static assets.
# First visit: ~263KB of JS/CSS drops to ~84KB; repeat visits: 0 bytes.

_COMPRESSIBLE_TYPES = {"text/html", "text/css", "application/json",
                       "application/javascript", "text/javascript"}
_static_gzip_cache = {}

@app.after_request
def _compress_and_cache(response):
    """Gzip compressible responses and set immutable caching for /static."""
    try:
        if request.path.startswith('/static/'):
            # Assets are referenced with ?v=N cache-busting — safe to pin
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

        if (response.status_code != 200
                or response.mimetype not in _COMPRESSIBLE_TYPES
                or 'Content-Encoding' in response.headers
                or 'Range' in request.headers
                or 'gzip' not in (request.headers.get('Accept-Encoding') or '').lower()):
            return response

        if request.path.startswith('/static/'):
            # Static bytes only change on deploy — compress each file once
            key = (request.path, response.headers.get('ETag'))
            gz = _static_gzip_cache.get(key)
            if gz is None:
                response.direct_passthrough = False
                data = response.get_data()
                if len(data) < 500:
                    return response
                gz = gzip.compress(data, 6)
                if len(_static_gzip_cache) > 32:
                    _static_gzip_cache.clear()
                _static_gzip_cache[key] = gz
        else:
            response.direct_passthrough = False
            data = response.get_data()
            if len(data) < 500:
                return response
            gz = gzip.compress(data, 6)

        response.set_data(gz)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = str(len(gz))
        response.headers.add('Vary', 'Accept-Encoding')
    except Exception as e:
        print(f"Response compression skipped: {e}")
    return response

# Optimization: Keep-Alive Connection Pooling
http_session = requests.Session()
http_session.headers.update({
    'User-Agent': 'Antigravity Telegram Bot antigravity@tradersentertainment.com',
    'Accept-Encoding': 'gzip, deflate',
})
# The default adapter keeps 10 connections per host and, more importantly,
# retries nothing. Five hosts (three SEC, Telegram, Groq) are hit from the
# poll threads, the warmer, the backfills and every Flask request, so give
# the pool real headroom. max_retries stays 0: urllib3 backoff would add
# seconds to a latency-critical fetch, and a blind retry of the Telegram
# POST could double-post. Stale-socket recovery is handled explicitly in
# send_telegram_alert instead.
_https_adapter = requests.adapters.HTTPAdapter(
    pool_connections=16, pool_maxsize=32, pool_block=False, max_retries=0)
http_session.mount('https://', _https_adapter)
http_session.mount('http://', _https_adapter)

# Telegram renders a link preview by fetching the SEC page itself BEFORE it
# answers sendMessage, and every filing URL is a cache miss for it. That wait
# lands squarely on the alert path, so previews are off by default.
TELEGRAM_LINK_PREVIEW = os.getenv("TELEGRAM_LINK_PREVIEW", "false").lower() in ("1", "true", "yes")

def _envbool(name, default="false"):
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")

# ----------------- POLYMARKET CONFIG -----------------
# A daily digest of tracked wallets' new betting activity. The endpoints are
# public and unauthenticated, but they could not be reached from the machine
# this was written on, so every field access below is defensive and the first
# response shape is logged once.
POLYMARKET_DATA_API = os.getenv("POLYMARKET_DATA_API", "https://data-api.polymarket.com").rstrip("/")
POLYMARKET_INSIDERS_RAW = os.getenv("POLYMARKET_INSIDERS", "")
POLYMARKET_MIN_USD = float(os.getenv("POLYMARKET_MIN_USD", "100"))
POLYMARKET_MIN_DELTA_PCT = float(os.getenv("POLYMARKET_MIN_DELTA_PCT", "5"))
POLYMARKET_MAX_INSIDERS = int(os.getenv("POLYMARKET_MAX_INSIDERS", "10"))
POLYMARKET_MAX_MOVES_PER_ADDR = int(os.getenv("POLYMARKET_MAX_MOVES_PER_ADDR", "8"))
POLYMARKET_PAGE_LIMIT = int(os.getenv("POLYMARKET_PAGE_LIMIT", "500"))
POLYMARKET_MAX_PAGES = int(os.getenv("POLYMARKET_MAX_PAGES", "3"))
POLYMARKET_BUDGET_S = float(os.getenv("POLYMARKET_BUDGET_S", "20"))
POLYMARKET_CONNECT_TIMEOUT = float(os.getenv("POLYMARKET_CONNECT_TIMEOUT", "3"))
POLYMARKET_READ_TIMEOUT = float(os.getenv("POLYMARKET_READ_TIMEOUT", "6"))
POLYMARKET_TITLE_MAX = int(os.getenv("POLYMARKET_TITLE_MAX", "70"))
POLYMARKET_CATCHUP_MIN = float(os.getenv("POLYMARKET_CATCHUP_MIN", "120"))
POLYMARKET_MSG_LIMIT = int(os.getenv("POLYMARKET_MSG_LIMIT", "3800"))
POLYMARKET_PART_DELAY_S = float(os.getenv("POLYMARKET_PART_DELAY_S", "1.0"))
POLYMARKET_REPORT_RESOLVED = _envbool("POLYMARKET_REPORT_RESOLVED")
POLYMARKET_ULTRA_GATE = _envbool("POLYMARKET_ULTRA_GATE")

def _hhmm(env, default_minute):
    """Parse 'HH:MM' into minutes-of-day. Sibling of _win()."""
    raw = os.getenv(env, "").strip()
    if raw:
        try:
            hh, mm = (int(x) for x in raw.split(":"))
            return hh * 60 + mm
        except Exception:
            print(f"Ignoring malformed {env}={raw!r}; expected 'HH:MM' TRT.")
    return default_minute

# 14:00 TRT is 07:00 ET in summer and 06:00 ET in winter — clear of
# ULTRA_WINDOW_ET in both. 14:30 TRT would land on 07:30 ET under US DST,
# the exact minute the ultra window opens.
POLYMARKET_DIGEST_MINUTE = _hhmm("POLYMARKET_DIGEST_AT_TRT", 14 * 60)

# The shared http_session carries an SEC-branded, email-identified User-Agent
# that SEC fair-use policy requires. It means nothing to Polymarket's edge and
# datacenter egress (Railway) is known to draw bot challenges there, so this
# gets its own identity — and its own small pool, so a hung Polymarket socket
# can never occupy a slot the SEC or Telegram path wants.
polymarket_session = requests.Session()
polymarket_session.headers.update({
    'User-Agent': os.getenv("POLYMARKET_USER_AGENT",
                            "Mozilla/5.0 (compatible; MSTRInsiderBot/1.0)"),
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate',
})
_pm_adapter = requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, pool_block=False, max_retries=0)
polymarket_session.mount('https://', _pm_adapter)

# ----------------- DB MANAGEMENT -----------------

_wal_enabled = False

def get_db_connection():
    """Open a connection in WAL mode.

    In the default rollback-journal mode a writer takes an EXCLUSIVE lock and
    every reader blocks behind it for the full busy timeout. The alert path
    reads (and, until this change, wrote) while save_to_database, the two
    startup backfills and every Flask request are writing, so a five-second
    stall was reachable on the one path that must never stall. WAL lets
    readers run concurrently with the writer; journal_mode is persistent in
    the database file, so it is set once per process.
    """
    global _wal_enabled
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    if not _wal_enabled:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            _wal_enabled = True
        except Exception as e:
            print(f"Could not enable SQLite WAL mode: {e}")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Self-healing: Check if database contains corrupt data or is missing June 1/June 29 records
    should_reset = False
    try:
        cursor.execute("SELECT COUNT(*) FROM purchase_history WHERE filing_date = '2026-06-01'")
        has_june_1 = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM purchase_history WHERE filing_date = '2026-06-29'")
        has_june_29 = cursor.fetchone()[0]
        
        if has_june_1 == 0 or has_june_29 == 0:
            print("Database is missing June 1 (sale) or June 29 (weekly update) records. Triggering rebuild...")
            should_reset = True
            
        cursor.execute("SELECT COUNT(*) FROM purchase_history WHERE total_holdings = '-' OR total_holdings LIKE '%NaN%'")
        corrupt_count = cursor.fetchone()[0]
        if corrupt_count > 0:
            print(f"Database corruption detected: {corrupt_count} records have NaN/invalid holdings. Triggering reset...")
            should_reset = True
    except sqlite3.OperationalError:
        pass
        
    if should_reset:
        print("Self-healing: Dropping tables to rebuild a clean state...")
        cursor.execute("DROP TABLE IF EXISTS purchase_history")
        cursor.execute("DROP TABLE IF EXISTS processed_filings")
        conn.commit()
    
    # Table for processed filings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_filings (
        accession_number TEXT PRIMARY KEY,
        filing_date TEXT,
        form TEXT,
        url TEXT,
        parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Table for purchase history
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filing_date TEXT,
        period TEXT,
        btc_acquired TEXT,
        purchase_price TEXT,
        avg_price TEXT,
        total_holdings TEXT,
        total_cost TEXT,
        avg_cost TEXT,
        url TEXT,
        total_debt TEXT,
        financing_source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Alter tables in case they already exist from older versions
    try:
        cursor.execute("ALTER TABLE purchase_history ADD COLUMN total_debt TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE purchase_history ADD COLUMN financing_source TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE purchase_history ADD COLUMN atm_sales TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE purchase_history ADD COLUMN event_type TEXT")
    except sqlite3.OperationalError:
        pass

    # Data-repair migrations ledger (survives the purchase_history self-heal drop)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        migration_id TEXT PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Quarterly balance-sheet metrics from the SEC XBRL API (e.g. cash reserves)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS polymarket_positions (
        address       TEXT NOT NULL,
        condition_id  TEXT NOT NULL,
        asset         TEXT NOT NULL DEFAULT '',
        outcome       TEXT,
        title         TEXT,
        event_slug    TEXT,
        size          REAL NOT NULL DEFAULT 0,
        avg_price     REAL,
        cur_price     REAL,
        redeemable    INTEGER NOT NULL DEFAULT 0,
        end_date      TEXT,
        snapshot_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        -- asset is in the key because a wallet can hold BOTH the Yes and the
        -- No token of one market; keyed on condition_id alone the two legs
        -- would silently overwrite each other.
        PRIMARY KEY (address, condition_id, asset)
    )
    """)

    # Which days the digest has already been posted. This is what makes the
    # job idempotent across restarts, and what tells "nothing happened today"
    # apart from "we never ran today".
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS polymarket_digests (
        digest_date TEXT PRIMARY KEY,
        posted_at   TIMESTAMP,
        status      TEXT,
        movements   INTEGER DEFAULT 0,
        addresses   INTEGER DEFAULT 0,
        note        TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_metrics (
        metric TEXT,
        period_end TEXT,
        value REAL,
        form TEXT,
        filed TEXT,
        PRIMARY KEY (metric, period_end)
    )
    """)

    conn.commit()
    
    # Seed database
    seed_database(conn)
    
    # If the processed filings table is fresh (e.g. less than 100 entries), mark all current Edgar index filings as processed
    cursor.execute("SELECT COUNT(*) FROM processed_filings")
    proc_count = cursor.fetchone()[0]
    if proc_count < 100:
        mark_current_filings_processed(conn)

    # Repair known-bad historical rows (runs after self-heal + seed so every
    # ordering is safe; content guards make it a no-op on healthy databases)
    apply_data_migrations(conn)

    conn.close()

# Historical seed data (only applied to an EMPTY purchase_history table).
# TODO: replace the July 13 placeholder URL with the real filing URL
# once it can be read from EDGAR or the Railway logs.
SEED_HISTORY = [
            ("2026-07-13", "July 6, 2026 to July 12, 2026", "0", "-", "-", "843,775", "$63.69B", "$75,476", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001050446&type=8-K", "$6.7B", "MSTR ATM Hisse Satışı ($466.7M)"),
            ("2026-07-06", "June 29, 2026 to July 5, 2026", "-3,588", "$216.0M", "$60,197", "843,775", "$63.69B", "$75,476", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526295586/mstr-20260706.htm", "$6.7B", "İmtiyazlı Hisse (STRC) Temettüsü"),
            ("2026-06-29", "June 22, 2026 to June 28, 2026", "0", "$0M", "$0", "847,363", "$64.10B", "$75,651", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526286871/mstr-20260629.htm", "$6.7B", "-"),
            ("2026-06-22", "June 15, 2026 to June 21, 2026", "520", "$34.9M", "$67,068", "847,363", "$64.10B", "$75,651", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm", "$6.7B", "ATM Hisse Satışı"),
            ("2026-06-15", "June 8, 2026 to June 14, 2026", "1,587", "$100.0M", "$63,024", "846,842", "$64.07B", "$75,656", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526270311/mstr-20260504.htm", "$6.7B", "ATM Hisse Satışı"),
            ("2026-06-08", "June 1, 2026 to June 7, 2026", "1,550", "$101.3M", "$65,332", "845,256", "$63.97B", "$75,680", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526260709/mstr-20260504.htm", "$6.7B", "ATM Hisse Satışı"),
            ("2026-06-01", "May 26, 2026 to May 31, 2026", "-32", "$2.5M", "$77,135", "843,706", "$63.85B", "$75,670", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526249768/mstr-20260530.htm", "$6.7B", "İmtiyazlı Hisse (STRC) Temettüsü"),
            ("2026-05-18", "May 11, 2026 to May 17, 2026", "24,869", "$2.01B", "$80,985", "843,738", "$63.87B", "$75,700", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526227918/mstr-20260504.htm", "$6.7B", "ATM Hisse Satışı & Nakit Rezervleri"),
            ("2026-05-11", "May 4, 2026 to May 10, 2026", "535", "$43.0M", "$80,340", "818,869", "$61.86B", "$75,540", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526215754/mstr-20260504.htm", "$8.2B", "ATM Hisse Satışı"),
            ("2026-05-04", "April 27, 2026 to May 3, 2026", "0", "$0M", "$0", "818,334", "$61.81B", "$75,537", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526202611/mstr-20260504.htm", "$8.2B", "-"),
            ("2026-04-27", "April 20, 2026 to April 26, 2026", "3,273", "$255.0M", "$77,906", "818,334", "$61.81B", "$75,537", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526178994/mstr-20260223.htm", "$8.2B", "ATM Hisse Satışı"),
            ("2026-04-20", "April 13, 2026 to April 19, 2026", "34,164", "$2.54B", "$74,395", "815,061", "$61.56B", "$75,527", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526162756/mstr-20260223.htm", "$8.2B", "Konvertibl Tahvil İhracı & ATM Hisse"),
            ("2026-04-13", "April 6, 2026 to April 12, 2026", "13,927", "$1.00B", "$71,902", "780,897", "$59.02B", "$75,577", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526152015/mstr-20260223.htm", "$8.2B", "Konvertibl Tahvil İhracı"),
            ("2026-04-06", "March 30, 2026 to March 31, 2026", "0", "$0M", "$0", "762,099", "$57.69B", "$75,694", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526142925/mstr-20260406.htm", "$8.2B", "-"),
            ("2026-03-23", "March 16, 2026 to March 22, 2026", "1,031", "$76.6M", "$74,326", "762,099", "$57.69B", "$75,694", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526118584/mstr-20260223.htm", "$8.2B", "ATM Hisse Satışı"),
            ("2026-03-16", "March 9, 2026 to March 15, 2026", "22,337", "$1.57B", "$70,194", "761,068", "$57.61B", "$75,696", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526107263/mstr-20260223.htm", "$8.2B", "Konvertibl Tahvil İhracı"),
            ("2026-03-02", "February 23, 2026 to March 1, 2026", "3,015", "$204.1M", "$67,700", "720,737", "$54.77B", "$75,985", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526084264/mstr-20260228.htm", "$8.2B", "ATM Hisse Satışı"),
            ("2026-02-23", "February 17, 2026 to February 22, 2026", "592", "$39.8M", "$67,286", "717,722", "$54.56B", "$76,020", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526062489/mstr-20260223.htm", "$8.2B", "ATM Hisse Satışı"),
            ("2026-02-17", "February 9, 2026 to February 16, 2026", "2,486", "$168.4M", "$67,710", "717,131", "$54.52B", "$76,027", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526053105/mstr-20260105.htm", "$8.2B", "ATM Hisse Satışı"),
            ("2026-02-09", "February 2, 2026 to February 8, 2026", "1,142", "$90.0M", "$78,815", "714,644", "$54.35B", "$76,056", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526041944/mstr-20260105.htm", "$8.2B", "ATM Hisse Satışı")
]

def seed_database(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM purchase_history")
    count = cursor.fetchone()[0]
    if count == 0:
        print("Seeding database with historical purchase data...")
        for item in reversed(SEED_HISTORY):
            cursor.execute(
                """INSERT INTO purchase_history 
                   (filing_date, period, btc_acquired, purchase_price, avg_price, total_holdings, total_cost, avg_cost, url, total_debt, financing_source) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                item
            )
            
            url = item[8]
            # A real accession number can only be derived from Archives URLs;
            # placeholder rows are covered by mark_current_filings_processed.
            if '/Archives/edgar/data/' in url:
                parts = url.split('/')
                acc_no_dash = parts[-2]
                if len(acc_no_dash) == 18:
                    acc_dashed = f"{acc_no_dash[:10]}-{acc_no_dash[10:12]}-{acc_no_dash[12:]}"
                else:
                    acc_dashed = acc_no_dash

                cursor.execute(
                    "INSERT OR IGNORE INTO processed_filings (accession_number, filing_date, form, url) VALUES (?, ?, '8-K', ?)",
                    (acc_dashed, item[0], url)
                )
        conn.commit()
        print("Database seeded successfully.")

def mark_current_filings_processed(conn):
    """Mark historical filings processed so a fresh DB doesn't backfill-spam.

    Filings from today/yesterday are deliberately LEFT UNMARKED: they are
    still within the alerting window, and a restart that happens to land
    minutes after a new 8-K must not swallow it silently.
    """
    cursor = conn.cursor()
    print("Marking existing SEC filings in EDGAR index as processed to prevent backfilling...")
    # One transient failure here used to mark NOTHING, and the scanner then
    # treated every 8-K still visible in the feeds as new. Production logs
    # show this fetch failing for real ("Error fetching SEC JSON: Connection
    # aborted / RemoteDisconnected"), so retry before giving up.
    data = None
    for attempt in range(3):
        data = fetch_mstr_filings(use_conditional=False)
        if data:
            break
        if attempt < 2:
            print(f"Startup index fetch failed (attempt {attempt + 1}/3); retrying...")
            time.sleep(1.5)
    if not data:
        print("WARNING: could not read the EDGAR index at startup — historical "
              "filings are unmarked and may be re-detected once each.")
    if data:
        recent = data.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        accession_numbers = recent.get('accessionNumber', [])
        filing_dates = recent.get('filingDate', [])
        primary_docs = recent.get('primaryDocument', [])
        usable = min(len(forms), len(accession_numbers),
                     len(filing_dates), len(primary_docs))

        # EDGAR filing dates are US Eastern; the container clock is UTC.
        cutoff = (now_et().date() - timedelta(days=1)).strftime("%Y-%m-%d")

        # And never mark a filing NEWER than the history we actually hold.
        # This function exists to stop a fresh DB backfill-spamming the
        # channel, but it was marking every 8-K in the index — including the
        # weeks the seed does not cover. Those were then skipped forever as
        # "not new", and no backfill could recover them because both backfills
        # iterate purchase_history, which never got the row. Production froze
        # at the seed's newest date, 2026-07-13, while the page kept showing a
        # ticking "Son sorgu" above it.
        try:
            newest_row = cursor.execute(
                "SELECT MAX(filing_date) FROM purchase_history").fetchone()[0]
        except Exception:
            # Marking must not depend on another table existing; the worst
            # case is the old, wider cutoff.
            newest_row = None
        if newest_row and newest_row < cutoff:
            cutoff = newest_row
            print(f"Marking only filings up to {cutoff} — the newest row we hold. "
                  f"Anything after it is left for the poller to parse.")

        count_marked = 0
        skipped_recent = []
        for idx in range(usable):
            if forms[idx] != '8-K':
                continue
            acc_num = accession_numbers[idx]
            date = filing_dates[idx]
            if date >= cutoff:
                skipped_recent.append(f"{acc_num} ({date})")
                continue
            doc = primary_docs[idx]
            acc_num_no_dash = acc_num.replace('-', '')
            url = f"https://www.sec.gov/Archives/edgar/data/1050446/{acc_num_no_dash}/{doc}"

            cursor.execute(
                "INSERT OR IGNORE INTO processed_filings (accession_number, filing_date, form, url) VALUES (?, ?, '8-K', ?)",
                (acc_num, date, url)
            )
            count_marked += 1
        conn.commit()
        print(f"Successfully marked {count_marked} existing filings in EDGAR as processed.")
        if skipped_recent:
            print(f"Left {len(skipped_recent)} recent filing(s) unmarked so they can still "
                  f"alert: {', '.join(skipped_recent)}")

# ----------------- DATA-REPAIR MIGRATIONS -----------------

def apply_data_migrations(conn):
    """Run idempotent data-repair migrations at startup.

    Each migration is recorded in schema_migrations AND content-guarded, so
    every ordering is safe: fresh install (seed already correct, guards
    no-op), stale production DB (rows repaired exactly once), repeated boots
    (ledger skips). A failing migration never blocks startup.
    """
    migrations = [
        ("2026-07-13-repair-july-rows", _migrate_repair_july_2026_rows),
        ("2026-07-14-backfill-july13-atm-json", _migrate_backfill_july13_atm_json),
        ("2026-07-14-backfill-event-types", _migrate_backfill_event_types),
        ("2026-08-30-drop-false-sale-rows", _migrate_drop_false_sale_rows),
    ]
    cursor = conn.cursor()
    for migration_id, fn in migrations:
        try:
            cursor.execute("SELECT 1 FROM schema_migrations WHERE migration_id = ?", (migration_id,))
            if cursor.fetchone():
                continue
            fn(conn)
            cursor.execute("INSERT OR IGNORE INTO schema_migrations (migration_id) VALUES (?)", (migration_id,))
            conn.commit()
            print(f"Data migration applied: {migration_id}")
        except Exception as e:
            print(f"Data migration {migration_id} failed (will retry next boot): {e}")

def _migrate_drop_false_sale_rows(conn):
    """Remove history rows written from a misparsed holdings column.

    The August 30, 2026 filing was parsed with the week's purchase columns
    read as the whole treasury, so the row records 4,603 BTC held against
    843,775 the week before, and an inferred sale of the difference. Left in
    place it puts a cliff in the dashboard chart and hands the next filing a
    nonsense baseline to compare against.

    Deliberately narrow. Whether a row came from the filing's own numbers or
    from inference is not recorded, so the discriminator has to be the shape
    of the damage: a collapse of more than 90% of the treasury in one week.
    A real disposal on that scale would be the story of the decade and no
    operator would need this migration to notice it; a 99.5% drop with the
    week's purchase figures sitting in the holdings columns is a parse
    failure. The next filing restores the week from its own snapshot.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, filing_date, total_holdings, btc_acquired, event_type "
                   "FROM purchase_history ORDER BY filing_date, id")
    rows = cursor.fetchall()

    def as_int(v):
        try:
            return int(str(v).replace(',', '').replace(' ', '').lstrip('+'))
        except (ValueError, TypeError, AttributeError):
            return None

    removed = []
    prev = None
    for row in rows:
        holdings = as_int(row["total_holdings"])
        acquired = as_int(row["btc_acquired"])
        if (prev and holdings and holdings < prev * 0.1
                and row["event_type"] == "btc_sale"
                and acquired is not None and acquired < 0):
            removed.append((row["id"], row["filing_date"], row["total_holdings"]))
            continue
        if holdings:
            prev = holdings

    for row_id, date, holdings in removed:
        cursor.execute("DELETE FROM purchase_history WHERE id = ?", (row_id,))
        # Also un-process the filing. Deleting only the history row left the
        # accession in processed_filings, so the poller skipped it forever and
        # the week became unrecoverable — a migration must not open a hole it
        # cannot close.
        cursor.execute("DELETE FROM processed_filings WHERE filing_date = ?", (date,))
        print(f"Removed false-sale row id={row_id} ({date}, holdings={holdings}); "
              f"the filing is unmarked so it can be re-parsed.")
    if not removed:
        print("No false-sale rows found.")

def _migrate_repair_july_2026_rows(conn):
    """Repair production rows corrupted by the pre-multi-table parser.

    The July 6, 2026 filing contained TWO sale periods; the old parser only
    captured the first (-1,363 → holdings 846,000). The stale holdings then
    made the July 13 filing (no BTC transaction) look like a 2,225 BTC sale.
    """
    cursor = conn.cursor()

    # 1. July 6 row: corrected aggregate of both sale periods
    cursor.execute(
        """UPDATE purchase_history
           SET btc_acquired='-3,588', purchase_price='$216.0M', avg_price='$60,197',
               total_holdings='843,775', total_cost='$63.69B', avg_cost='$75,476',
               period='June 29, 2026 to July 5, 2026', event_type='btc_sale',
               financing_source='İmtiyazlı Hisse (STRC) Temettüsü'
           WHERE filing_date='2026-07-06' AND total_holdings<>'843,775'"""
    )
    if cursor.rowcount > 0:
        print(f"Migration: repaired {cursor.rowcount} July 6 row(s) → -3,588 BTC / 843,775 holdings")

    # Normalize the sign if the amount was stored unsigned or partial
    cursor.execute(
        """UPDATE purchase_history
           SET btc_acquired='-3,588', event_type='btc_sale'
           WHERE filing_date='2026-07-06' AND btc_acquired IN ('3,588', '1,363', '-1,363', '2,225', '-2,225')"""
    )

    # 2. Deduplicate July 13 rows, keeping the earliest
    cursor.execute(
        """DELETE FROM purchase_history
           WHERE filing_date='2026-07-13'
             AND id NOT IN (SELECT MIN(id) FROM purchase_history WHERE filing_date='2026-07-13')"""
    )

    # 3. Fix the fabricated July 13 "sale": there was NO BTC transaction that
    # week, only an MSTR ATM share sale ($466.7M net proceeds)
    cursor.execute(
        """UPDATE purchase_history
           SET btc_acquired='0', purchase_price='-', avg_price='-',
               total_holdings='843,775', total_cost='$63.69B', avg_cost='$75,476',
               period='July 6, 2026 to July 12, 2026',
               financing_source='MSTR ATM Hisse Satışı ($466.7M)', event_type='no_purchase'
           WHERE filing_date='2026-07-13' AND btc_acquired<>'0'"""
    )
    if cursor.rowcount > 0:
        print(f"Migration: repaired {cursor.rowcount} July 13 row(s) → 0 BTC / MSTR ATM $466.7M")

    # 4. Insert the July 13 row when missing entirely (fresh installs whose
    # seed predates July 13). TODO: replace the placeholder URL with the
    # real filing URL once it can be read from EDGAR or the Railway logs.
    cursor.execute("SELECT COUNT(*) FROM purchase_history WHERE filing_date='2026-07-13'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """INSERT INTO purchase_history
               (filing_date, period, btc_acquired, purchase_price, avg_price,
                total_holdings, total_cost, avg_cost, url, total_debt,
                financing_source, event_type)
               VALUES ('2026-07-13', 'July 6, 2026 to July 12, 2026', '0', '-', '-',
                       '843,775', '$63.69B', '$75,476',
                       'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001050446&type=8-K',
                       '$6.7B', 'MSTR ATM Hisse Satışı ($466.7M)', 'no_purchase')"""
        )
        print("Migration: inserted missing July 13 row (0 BTC; MSTR ATM $466.7M)")

    conn.commit()

# Per-security ATM data of the July 13, 2026 filing (from the filing's ATM
# table), in the exact shape parse_atm_table produces — backfilled so the
# dashboard shows WHICH security raised the cash for that week too.
_JULY13_ATM_JSON = {
    "fmt": 4,
    "period_scoped": True,
    "period": "July 6, 2026 to July 12, 2026",
    "securities": [
        {"ticker": "STRF", "name": "STRF Stock 10.00% Series A Perpetual Strife Preferred Stock",
         "shares_sold": "-", "notional": "-", "net_proceeds": "-", "available": "$1,619.3M",
         "shares_sold_num": 0, "net_proceeds_num_m": 0.0},
        {"ticker": "STRC", "name": "STRC Stock Variable Rate Series A Perpetual Stretch Preferred Stock",
         "shares_sold": "-", "notional": "-", "net_proceeds": "-", "available": "$17,510.8M",
         "shares_sold_num": 0, "net_proceeds_num_m": 0.0},
        {"ticker": "STRK", "name": "STRK Stock 8.00% Series A Perpetual Strike Preferred Stock",
         "shares_sold": "-", "notional": "-", "net_proceeds": "-", "available": "$2,100.0M",
         "shares_sold_num": 0, "net_proceeds_num_m": 0.0},
        {"ticker": "STRD", "name": "STRD Stock 10.00% Series A Perpetual Stride Preferred Stock",
         "shares_sold": "-", "notional": "-", "net_proceeds": "-", "available": "$4,014.8M",
         "shares_sold_num": 0, "net_proceeds_num_m": 0.0},
        {"ticker": "MSTR", "name": "MSTR Stock Class A Common Stock",
         "shares_sold": "4,818,781", "notional": "-", "net_proceeds": "$466.7M", "available": "$23,790.3M",
         "shares_sold_num": 4818781, "net_proceeds_num_m": 466.7},
    ],
    "sold_tickers": ["MSTR"],
    "sold_any": True,
    "total_net_proceeds": "$466.7M",
}

def _migrate_backfill_july13_atm_json(conn):
    """Backfill the July 13 row's atm_sales JSON.

    The row was created (live or via repair) before ATM parsing existed, so
    the dashboard's per-security breakdown had nothing to render for the
    very filing that motivated the feature. Guarded on atm_sales IS NULL —
    a live re-parse that already filled it is never overwritten.
    """
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE purchase_history
           SET atm_sales = ?
           WHERE filing_date='2026-07-13' AND (atm_sales IS NULL OR atm_sales = '')""",
        (json.dumps(_JULY13_ATM_JSON, ensure_ascii=False),)
    )
    if cursor.rowcount > 0:
        print(f"Migration: backfilled atm_sales JSON on {cursor.rowcount} July 13 row(s)")
    conn.commit()

def _migrate_backfill_event_types(conn):
    """Classify historical rows so charts/tooltips can rely on event_type.

    Rows are stored with signed amounts (seed included), so the sign is a
    reliable classifier. Only NULL rows are touched.
    """
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE purchase_history SET event_type =
             CASE WHEN btc_acquired IN ('0', '-') THEN 'no_purchase'
                  WHEN btc_acquired LIKE '-%' THEN 'btc_sale'
                  ELSE 'btc_purchase' END
           WHERE event_type IS NULL"""
    )
    if cursor.rowcount > 0:
        print(f"Migration: classified event_type on {cursor.rowcount} historical row(s)")
    conn.commit()

# ----------------- PARSING & SEC SCRAPING -----------------

# lxml is much faster than html.parser on the alert-critical path; fall back
# gracefully if it isn't installed.
try:
    import lxml  # noqa: F401
    HTML_PARSER = 'lxml'
except ImportError:
    HTML_PARSER = 'html.parser'

# Optimization: Highly efficient text cleaning via BeautifulSoup tag decomposition
def clean_html(html_content):
    # HTML_PARSER (lxml when installed) is both faster and, unlike the
    # pure-Python html.parser, releases the GIL — this runs on background
    # threads that overlap the Telegram send.
    soup = BeautifulSoup(html_content, HTML_PARSER)
    # Decompose script, style, xml, and head blocks
    for element in soup(["script", "style", "xml", "head"]):
        element.decompose()
    text = soup.get_text(separator=' ')
    return re.sub(r'\s+', ' ', text).strip()

# SEC fair-use limit is 10 req/s: on 403/429 back off per source
# exponentially (1s → 60s) instead of hammering through a throttle.
_sec_backoff = {}

def _register_sec_throttle(source, status):
    if status in (403, 429):
        prev = _sec_backoff.get(source, {}).get('delay', 0)
        delay = min(max(prev * 2, 1), 60)
        _sec_backoff[source] = {'until': time.time() + delay, 'delay': delay}
        print(f"SEC {source} returned {status}; backing off {delay}s")

def _sec_blocked(source):
    entry = _sec_backoff.get(source)
    return bool(entry and time.time() < entry['until'])

def _sec_clear_backoff(source):
    _sec_backoff.pop(source, None)


# ----------------- SOURCE HEALTH TELEMETRY -----------------
# Only failures were ever logged, so a source that fails a quarter of the
# time and a source that fails nine times in ten look identical in the log:
# a scroll of red. Count both outcomes per source and report the ratio
# periodically, so "the atom feed is flaky" becomes a number and it is
# visible whether submissions is quietly carrying detection on its own.
SOURCE_REPORT_INTERVAL = float(os.getenv("SOURCE_REPORT_INTERVAL", "300"))
_SOURCE_REPORT_ORDER = ("submissions", "atom", "efts", "polymarket")
_source_stats = {}
_source_stats_lock = threading.Lock()
_source_report_time = 0.0
# Identical failures repeat every tick; print at most one per source per
# minute and let the periodic summary carry the true rate.
_source_error_logged = {}

def _record_source(name, ok, err=None, blocked=False):
    """Record one source outcome.

    `blocked` is a third state, not a failure: it means we declined to ask
    because the source is in backoff. Counting it as a failure would inflate
    the error rate, but leaving it out entirely made a backed-off source
    vanish from the report — which is how EFTS came to be missing from three
    consecutive health lines with no indication why.
    """
    with _source_stats_lock:
        st = _source_stats.setdefault(
            name, {"ok": 0, "fail": 0, "blocked": 0, "last_error": ""})
        if blocked:
            st["blocked"] += 1
        elif ok:
            st["ok"] += 1
        else:
            st["fail"] += 1
            st["last_error"] = str(err)[:160]

def _should_log_source_error(name):
    now = time.time()
    if now - _source_error_logged.get(name, 0) < 60:
        return False
    _source_error_logged[name] = now
    return True

def source_health_snapshot():
    """Read-only view of the counters, for /api/status. Does not reset."""
    with _source_stats_lock:
        out = {}
        for name, st in _source_stats.items():
            total = st["ok"] + st["fail"]
            out[name] = {
                "ok": st["ok"], "fail": st["fail"],
                "blocked": st.get("blocked", 0),
                "fail_pct": round(100.0 * st["fail"] / total, 1) if total else None,
                "last_error": st["last_error"] or None,
            }
        return out

def report_source_health(force=False):
    """Print a per-source ok/fail summary and reset the counters."""
    global _source_report_time
    now = time.time()
    if not force and now - _source_report_time < SOURCE_REPORT_INTERVAL:
        return
    window = now - _source_report_time if _source_report_time else 0
    _source_report_time = now
    with _source_stats_lock:
        if not any(v["ok"] or v["fail"] or v.get("blocked")
                   for v in _source_stats.values()):
            return
        parts = []
        # This list used to be hardcoded, so a source could be counted, be
        # exposed on /api/status, and still never appear in this line.
        names = list(_SOURCE_REPORT_ORDER) + sorted(
            n for n in _source_stats if n not in _SOURCE_REPORT_ORDER)
        for name in names:
            st = _source_stats.get(name)
            if not st or not (st["ok"] or st["fail"] or st.get("blocked")):
                continue
            total = st["ok"] + st["fail"]
            pct = 100.0 * st["fail"] / total if total else 0.0
            parts.append(f"{name} {st['ok']}ok/{st['fail']}fail ({pct:.0f}% fail)")
            if st.get("blocked"):
                parts[-1] += f" +{st['blocked']}blocked"
            if st["fail"]:
                parts[-1] += f" last={st['last_error']}"
            st["ok"] = st["fail"] = st["blocked"] = 0
            st["last_error"] = ""
    if parts:
        print(f"Source health over {window/60:.0f}min in {current_mode}: "
              + " | ".join(parts))

# Conditional-GET state for the (large) submissions JSON
_submissions_etag = None
_submissions_last_modified = None

def _commit_submissions_state(state):
    """Remember the conditional-GET validators for the NEXT poll.

    Must only be called after the payload has actually been consumed. If the
    ETag were stored inside the fetch (as it originally was), a poll that
    times out waiting for a slow download would discard the payload while
    the fetch thread stored the new ETag — every later poll would then get
    304 and the filing carried by the dropped payload would stay invisible
    until the index changed again.
    """
    global _submissions_etag, _submissions_last_modified
    if state:
        _submissions_etag = state.get('etag')
        _submissions_last_modified = state.get('last_modified')

# Railway's egress to www.sec.gov is measurably slow and flaky: production
# logs show constant "Read timed out (read timeout=3)" against the atom feed
# and "RemoteDisconnected" against the submissions index — the latter being a
# pooled keep-alive socket the peer closed after we had already written the
# request, which urllib3 cannot transparently recover.
#
# A single flat timeout=3 was both too tight for a slow origin and applied to
# connect and read separately. Split them: a connect that has not landed in
# SEC_CONNECT_TIMEOUT is dead, while a read deserves longer than 3s. This is
# only safe because the poll tick no longer blocks on these — each source
# runs on its own thread behind a shared deadline and its result is read
# whether or not the thread finished, so a slow fetch costs its own signal
# for one tick rather than stalling the loop.
SEC_CONNECT_TIMEOUT = float(os.getenv("SEC_CONNECT_TIMEOUT", "2"))
SEC_READ_TIMEOUT = float(os.getenv("SEC_READ_TIMEOUT", "6"))
# The atom feed lives on browse-edgar, SEC's legacy dynamic CGI, and
# production measures it failing ~19% of the time while data.sec.gov over the
# same window fails 0%. It is a corroborator, not the source detection rests
# on, and while a request hangs its in-flight slot is held — 6s of that is 24
# skipped ticks in the ultra window. Give up sooner and try again instead.
ATOM_READ_TIMEOUT = float(os.getenv("ATOM_READ_TIMEOUT", "2.5"))

def sec_get(url, headers=None, read_timeout=None):
    """GET an SEC endpoint, retrying once on a dropped keep-alive socket."""
    timeout = (SEC_CONNECT_TIMEOUT, read_timeout or SEC_READ_TIMEOUT)
    try:
        return http_session.get(url, timeout=timeout, headers=headers)
    except requests.exceptions.ConnectionError:
        # Stale pooled connection: retry immediately on a fresh socket. Costs
        # nothing in the happy path, and a read timeout is NOT retried here —
        # that one is a slow origin, and hammering it would make things worse.
        return http_session.get(url, timeout=timeout, headers=headers)

def fetch_mstr_filings(use_conditional=True, return_state=False):
    """Fetch the EDGAR submissions index.

    With use_conditional (polling path), sends If-None-Match/If-Modified-Since
    so an unchanged index returns 304 and skips download + JSON parse of the
    multi-MB payload. Callers that NEED the data (startup marking, test
    route) pass use_conditional=False.

    This function never writes the conditional-GET globals itself. The
    polling path passes return_state=True, receives (data, state), and
    commits the state via _commit_submissions_state ONLY after scanning the
    filing list. One-shot consumers must not commit at all — a stored ETag
    from e.g. the admin test route would make the scanner 304 past a filing
    it never saw.
    """
    if _sec_blocked('submissions'):
        _record_source('submissions', False, blocked=True)
        return (None, None) if return_state else None
    cik = "0001050446"
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {}
    if use_conditional and _submissions_etag:
        headers['If-None-Match'] = _submissions_etag
    if use_conditional and _submissions_last_modified:
        headers['If-Modified-Since'] = _submissions_last_modified
    try:
        resp = sec_get(url, headers=headers)
        if resp.status_code == 200:
            _sec_clear_backoff('submissions')
            _record_source('submissions', True)
            state = {
                'etag': resp.headers.get('ETag'),
                'last_modified': resp.headers.get('Last-Modified'),
            }
            data = resp.json()
            return (data, state) if return_state else data
        elif resp.status_code == 304:
            # Index unchanged since the last poll — nothing new
            _record_source('submissions', True)
        else:
            _record_source('submissions', False, f"HTTP {resp.status_code}")
            _register_sec_throttle('submissions', resp.status_code)
    except Exception as e:
        _record_source('submissions', False, e)
        if _should_log_source_error('submissions'):
            print(f"Error fetching SEC JSON: {e}")
    return (None, None) if return_state else None

_atom_shape_logged = False
_atom_empty_since = 0.0

# The company Atom feed reflects EDGAR's live dissemination system and is a
# few KB (vs the multi-MB submissions JSON), so it is the fastest way to
# learn a filing exists. It carries the accession but not the primary
# document name — that is resolved with one small index.json fetch, and
# only when a genuinely new accession shows up.
ATOM_URL = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            "&CIK=0001050446&type=8-K&dateb=&owner=include&count=10&output=atom")

# EDGAR's browse-edgar atom output has long carried the accession under a
# MISSPELLED tag, <accession-nunber>. The parser here used to require the
# correct spelling, so `if not acc: continue` dropped every entry and this
# "fastest signal" silently returned [] on every single poll — while the two
# sources it was introduced to replace were slowed down to make room for it.
# Accessions have a fixed shape (10-2-6 digits), so match the shape and stop
# trusting the tag name at all.
ACCESSION_RE = re.compile(r'\b(\d{10}-\d{2}-\d{6})\b')

def _resolve_primary_document(accession):
    """Map an accession to its primary 8-K document URL via index.json."""
    acc_no_dash = accession.replace('-', '')
    base = f"https://www.sec.gov/Archives/edgar/data/1050446/{acc_no_dash}"
    try:
        resp = sec_get(f"{base}/index.json")
        if resp.status_code != 200:
            return ""
        items = ((resp.json() or {}).get("directory") or {}).get("item") or []
        htm = [i.get("name", "") for i in items
               if i.get("name", "").lower().endswith(('.htm', '.html'))]
        # Skip EDGAR's own index/header pages; the filing document remains
        docs = [n for n in htm
                if 'index' not in n.lower() and not n.lower().endswith('-index.htm')]
        if not docs:
            return ""
        # MSTR names its 8-K body mstr-YYYYMMDD.htm; otherwise take the first
        preferred = next((n for n in docs if n.lower().startswith('mstr')), docs[0])
        return f"{base}/{preferred}"
    except Exception as e:
        print(f"Primary document resolve failed for {accession}: {e}")
        return ""

def fetch_mstr_filings_atom():
    """Fastest new-filing signal: the company's EDGAR Atom feed.

    Returns [{accession, date, url}] for 8-K entries. Every failure mode
    returns [] — the submissions and EFTS paths are unaffected.
    """
    global _atom_shape_logged, _atom_empty_since
    if _sec_blocked('atom'):
        _record_source('atom', False, blocked=True)
        return []
    try:
        resp = sec_get(ATOM_URL, read_timeout=ATOM_READ_TIMEOUT)
        if resp.status_code != 200:
            _record_source('atom', False, f"HTTP {resp.status_code}")
            _register_sec_throttle('atom', resp.status_code)
            return []
        _sec_clear_backoff('atom')
        _record_source('atom', True)
        body = resp.text
        results = []
        for entry in re.findall(r'<entry>(.*?)</entry>', body, re.S):
            # Shape match over the whole entry: covers <accession-number>,
            # EDGAR's misspelled <accession-nunber>, and the accession
            # embedded in <filing-href>.../0001050446-26-000123-index.htm.
            acc = ACCESSION_RE.search(entry)
            ftype = re.search(r'<filing-type>\s*([^<]+?)\s*</filing-type>', entry, re.I)
            fdate = re.search(r'<filing-date>\s*([\d-]+)\s*</filing-date>', entry, re.I)
            if not acc:
                continue
            form = (ftype.group(1) if ftype else '8-K').strip()
            if not form.startswith('8-K'):
                continue
            results.append({
                "accession": acc.group(1).strip(),
                "date": (fdate.group(1) if fdate else now_et().strftime("%Y-%m-%d")),
                "url": "",   # resolved lazily, only for unseen accessions
            })
        if results and not _atom_shape_logged:
            _atom_shape_logged = True
            print(f"EDGAR atom feed OK (one-time log): newest={results[0]['accession']} "
                  f"date={results[0]['date']} entries={len(results)}")
        elif not results:
            # A feed that parses to nothing is how this source died silently
            # before. A 200 with a non-empty body and zero entries is a
            # PARSER failure, not an absence of filings — say so, repeatedly
            # but not on every tick.
            now = time.time()
            if body.strip() and now - _atom_empty_since > 900:
                _atom_empty_since = now
                print(f"WARNING: EDGAR atom feed parsed 0 8-K entries from a "
                      f"{len(body)}-byte 200 response — the feed shape may have "
                      f"changed. Body starts: {body[:200]!r}")
        return results
    except Exception as e:
        _record_source('atom', False, e)
        if _should_log_source_error('atom'):
            print(f"Atom feed query error (non-critical): {e}")
    return []

_efts_shape_logged = False

def fetch_mstr_filings_efts():
    """Query EDGAR Full-Text Search (EFTS) — often indexes before the submissions API.

    Real EFTS hits look like:
      {"_id": "0001193125-26-295586:mstr-20260706.htm",
       "_source": {"ciks": ["0001050446"], "file_date": "2026-07-06", ...}}
    The dashed accession in _id matches the format the submissions path
    stores in processed_filings. Parsing is defensive (also accepts the
    legacy shape previously assumed here) and the first live hit is logged
    once so the real response shape can be verified after deploy. Always
    returns [] on failure — the submissions path is unaffected.
    """
    global _efts_shape_logged
    if _sec_blocked('efts'):
        _record_source('efts', False, blocked=True)
        return []
    # EDGAR dates are US Eastern; datetime.now() is the container's UTC
    # clock, which is a day ahead late in the US evening. And q= is a hard
    # full-text filter: keyed on "bitcoin" this path was blind to every 8-K
    # that did not contain the literal word — dividend declarations, ATM
    # prospectus supplements, officer changes. It is optional, so drop it.
    today = now_et().strftime("%Y-%m-%d")
    url = (f"https://efts.sec.gov/LATEST/search-index?"
           f"forms=8-K&ciks=0001050446&startdt={today}&enddt={today}")
    try:
        resp = sec_get(url)
        if resp.status_code != 200:
            _record_source('efts', False, f"HTTP {resp.status_code}")
            _register_sec_throttle('efts', resp.status_code)
            return []
        _sec_clear_backoff('efts')
        _record_source('efts', True)
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        if hits and not _efts_shape_logged:
            _efts_shape_logged = True
            print(f"EFTS first-hit shape (one-time log): {json.dumps(hits[0])[:800]}")
        results = []
        for hit in hits:
            source = hit.get("_source", {}) or {}
            filing_date = source.get("file_date", today)
            hit_id = hit.get("_id", "")
            if re.match(r'^\d{10}-\d{2}-\d{6}:', hit_id):
                acc, _, filename = hit_id.partition(':')
                acc_no_dash = acc.replace('-', '')
                results.append({
                    "accession": acc,
                    "date": filing_date,
                    "url": f"https://www.sec.gov/Archives/edgar/data/1050446/{acc_no_dash}/{filename}"
                })
                continue
            # Legacy/unknown shape fallback. Only accept something that is
            # actually shaped like an accession: `file_num` is an SEC file
            # number and a bare `_id` still carries its ':filename' suffix,
            # and either one written into processed_filings can never match
            # the dashed form the other sources produce — so the filing gets
            # alerted twice and the junk row is dedup-dead forever.
            filing_url = source.get("file_url", "")
            raw_acc = source.get("adsh") or hit_id
            acc_match = ACCESSION_RE.search(raw_acc or "")
            if filing_url and acc_match:
                results.append({"accession": acc_match.group(1),
                                "date": filing_date, "url": filing_url})
            elif hit_id:
                print(f"EFTS: unrecognized hit shape, _id={hit_id[:120]}")
        return results
    except Exception as e:
        _record_source('efts', False, e)
        if _should_log_source_error('efts'):
            print(f"EFTS query error (non-critical): {e}")
    return []

def fetch_html(url):
    try:
        resp = sec_get(url)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"Error fetching filing HTML: {e}")
    return ""

def clean_row_values(row):
    cleaned = []
    i = 0
    while i < len(row):
        val = row[i].strip()
        if not val:
            i += 1
            continue
        if val == '$':
            i += 1
            if i < len(row):
                next_val = row[i].strip()
                cleaned.append(f"${next_val}")
            else:
                cleaned.append('$')
        elif val == '-' or val == '—':
            cleaned.append('-')
        else:
            cleaned.append(val)
        i += 1
    
    final_cleaned = []
    for item in cleaned:
        if item == '$-' or item == '$':
            final_cleaned.append('-')
        else:
            final_cleaned.append(item)
    return final_cleaned

def extract_filing_tables(html_content):
    """Parse the filing HTML once and return per-table cell data.

    Returns a list of tables; each table is a list of rows; each row is a
    list of non-empty cell strings. Both the BTC parser and the ATM parser
    consume this output, so the HTML is parsed only once on the alert path.
    """
    soup = BeautifulSoup(html_content, HTML_PARSER, parse_only=SoupStrainer('table'))
    all_tables = []
    for table in soup.find_all('table'):
        row_data = []
        for r in table.find_all('tr'):
            cols = [col.get_text().strip().replace('\n', ' ') for col in r.find_all(['td', 'th'])]
            cols = [re.sub(r'\s+', ' ', c) for c in cols if c.strip()]
            if cols:
                row_data.append(cols)
        if row_data:
            all_tables.append(row_data)
    return all_tables

def parse_btc_number(s):
    """Parse a BTC/share count string like '1,363' or '4,818,781' to int.

    '-', '—' and footnote-only cells parse to 0 (no transaction).
    """
    try:
        cleaned = re.sub(r'\(\d+\)', '', str(s)).replace(',', '').replace(' ', '')
        return int(cleaned)
    except (ValueError, AttributeError):
        return 0

def parse_money(s):
    """Parse a money string like '$80.8M' or '$2.01B' to a float in millions."""
    try:
        s = re.sub(r'\(\d+\)', '', str(s)).replace('$', '').replace(',', '').strip()
        multiplier = 1
        if s.endswith('M'):
            s = s[:-1]
        elif s.endswith('B'):
            multiplier = 1000
            s = s[:-1]
        return float(s) * multiplier
    except (ValueError, AttributeError):
        return 0.0

def parse_table_fallback(html_content):
    """Back-compat wrapper: extract tables once, then parse the BTC data."""
    return parse_btc_tables(extract_filing_tables(html_content))

# Column labels, matched loosely: \s covers the non-breaking spaces the
# extractor can leave behind, and the alternations cover MSTR rewording a
# header without changing what the column means.
# An inferred move larger than this fraction of the known balance is treated
# as a parse failure rather than news.
MAX_INFERRED_MOVE = float(os.getenv("MAX_INFERRED_MOVE", "0.25"))

BTC_SOLD_RE = re.compile(r'BTC\s+(?:Sold|Disposed)', re.I)
BTC_ACQUIRED_RE = re.compile(r'BTC\s+(?:Acquired|Purchased|Bought|Added)', re.I)
BTC_HOLDINGS_RE = re.compile(r'Aggregate\s+BTC\s+Holdings', re.I)

def _holdings_column_index(header_row):
    """Where the holdings block starts in the header row, or None."""
    return next((i for i, h in enumerate(header_row or [])
                 if BTC_HOLDINGS_RE.search(h or '')), None)

def parse_btc_tables(tables):
    """Parse BTC activity and holdings tables from pre-extracted table data.

    Event detection is based on the filing's OWN period-activity tables
    ("BTC Acquired" / "BTC Sold"): they state authoritatively what happened
    during the covered period. The holdings delta vs the DB is ONLY a
    consistency check — a stale DB row must never fabricate a buy/sell event
    (that is exactly what produced the false "-2,225 BTC sold" alert on the
    July 13, 2026 filing).
    """
    # Collect all activity entries (purchases/sales) and holdings snapshots
    activities = []      # list of dicts: {type, signed_count, period, btc_count, price, avg_price}
    holdings_snapshots = []  # list of dicts: {as_of, holdings, total_cost, avg_cost}

    for row_data in tables:
        if len(row_data) < 2:
            continue

        table_text = ' '.join(' '.join(r) for r in row_data)
        header_text = ' '.join(row_data[1]) if len(row_data) > 1 else ''
        period_text = row_data[0][0] if row_data[0] else ''

        # Match the labels loosely. A literal 'BTC Acquired' comparison is a
        # single point of failure for the whole parse: if MSTR reworded the
        # column, or the extractor left a non-breaking space in it, the
        # activity table stops being recognised and its columns get read as
        # something else entirely.
        is_sold = bool(BTC_SOLD_RE.search(header_text) or BTC_SOLD_RE.search(table_text))
        is_acquired = bool(BTC_ACQUIRED_RE.search(header_text) or BTC_ACQUIRED_RE.search(table_text))
        is_holdings = bool(BTC_HOLDINGS_RE.search(header_text) or BTC_HOLDINGS_RE.search(table_text))

        if (is_sold or is_acquired) and len(row_data) >= 3:
            try:
                cleaned = clean_row_values(row_data[2])
                if len(cleaned) < 3:
                    cleaned += ['-'] * (3 - len(cleaned))

                # Clean footnote markers like (1) from BTC count
                btc_raw = re.sub(r'\(\d+\)', '', cleaned[0]).strip()

                # Detect price unit from header; strip footnote markers so a
                # cell like '$59,256(2)' doesn't silently break number parsing
                price_header = row_data[1][1].lower() if len(row_data[1]) > 1 else ''
                unit = "M" if "millions" in price_header else ("B" if "billions" in price_header else "")
                price_val = re.sub(r'\(\d+\)', '', cleaned[1]).strip() or '-'
                if price_val != '-' and unit and not price_val.endswith(unit):
                    price_val = f"{price_val}{unit}"

                avg_val = re.sub(r'\(\d+\)', '', cleaned[2]).strip() or '-'

                # Extract period from row 0
                period = period_text.replace("During Period ", "").replace("*", "").strip()

                count = parse_btc_number(btc_raw)
                activities.append({
                    "type": "sale" if is_sold else "purchase",
                    "signed_count": -count if is_sold else count,
                    "period": period,
                    "btc_count": btc_raw,
                    "price": price_val,
                    "avg_price": avg_val
                })

                # Combined format: one table holding both the period activity
                # (columns 0-2) and the cumulative holdings (columns 3-5),
                # e.g. [BTC Acquired, Price(M), Avg Price, Aggregate BTC Holdings, Price(B), Avg Price]
                hi = _holdings_column_index(row_data[1])
                if is_holdings and hi is not None and len(cleaned) >= hi + 3:
                        h_cost_header = row_data[1][hi + 1].lower() if hi + 1 < len(row_data[1]) else ''
                        h_cost_unit = "M" if "millions" in h_cost_header else ("B" if "billions" in h_cost_header else "")
                        # Read from where the header says the holdings block
                        # begins. These indices were hardcoded to 3/4/5, which
                        # is right only for the layout that happened to be in
                        # front of us.
                        h_holdings = re.sub(r'\(\d+\)', '', cleaned[hi]).strip() or '-'
                        h_cost_val = re.sub(r'\(\d+\)', '', cleaned[hi + 1]).strip() or '-'
                        if h_cost_val != '-' and h_cost_unit and not h_cost_val.endswith(h_cost_unit):
                            h_cost_val = f"{h_cost_val}{h_cost_unit}"
                        h_avg_cost = re.sub(r'\(\d+\)', '', cleaned[hi + 2]).strip() or '-'

                        # Extract "As of" date from period header row
                        as_of_parts = [p for p in row_data[0] if 'As of' in p]
                        as_of_date = as_of_parts[0].replace("As of ", "").replace("*", "").strip() if as_of_parts else period

                        holdings_snapshots.append({
                            "as_of": as_of_date,
                            "holdings": h_holdings,
                            "total_cost": h_cost_val,
                            "avg_cost": h_avg_cost
                        })
            except Exception as e:
                print(f"Error parsing activity table: {e}")

        elif is_holdings and len(row_data) >= 3:
            try:
                cleaned = clean_row_values(row_data[2])
                if len(cleaned) < 3:
                    cleaned += ['-'] * (3 - len(cleaned))

                # Where the holdings block actually starts. This branch used
                # to assume column 0, which is only true for a holdings-only
                # table. On a combined table whose activity header we failed
                # to recognise, it read the week's PURCHASE columns as the
                # entire treasury — reporting 4,603 BTC held instead of
                # 4,603 BTC bought, and turning a purchase into a 839,172 BTC
                # "sale" against the previous balance.
                hi = _holdings_column_index(row_data[1]) or 0
                if len(cleaned) < hi + 3:
                    print(f"Holdings table has {len(cleaned)} values but its header puts "
                          f"holdings at column {hi}; skipping rather than guessing.")
                    continue

                cost_header = row_data[1][hi + 1].lower() if hi + 1 < len(row_data[1]) else ''
                cost_unit = "M" if "millions" in cost_header else ("B" if "billions" in cost_header else "")
                cost_val = re.sub(r'\(\d+\)', '', cleaned[hi + 1]).strip() or '-'
                if cost_val != '-' and cost_unit and not cost_val.endswith(cost_unit):
                    cost_val = f"{cost_val}{cost_unit}"

                as_of_parts = [p for p in row_data[0] if 'As of' in p]
                as_of = (as_of_parts[0] if as_of_parts else period_text
                         ).replace("As of ", "").replace("*", "").strip()

                holdings_snapshots.append({
                    "as_of": as_of,
                    "holdings": re.sub(r'\(\d+\)', '', cleaned[hi]).strip() or '-',
                    "total_cost": cost_val,
                    "avg_cost": re.sub(r'\(\d+\)', '', cleaned[hi + 2]).strip() or '-'
                })
            except Exception as e:
                print(f"Error parsing holdings table: {e}")

    # If no activity or holdings tables found, return None
    if not activities and not holdings_snapshots:
        return None

    print(f"Parsed {len(activities)} activity tables and {len(holdings_snapshots)} holdings snapshots.")

    # Use the LAST holdings snapshot (most recent date) — a filing can carry
    # several period tables (e.g. the July 6, 2026 filing had two sale periods)
    latest_holdings = holdings_snapshots[-1] if holdings_snapshots else {}

    # Previous cumulative state from the DB. Debt carries forward (it is
    # cumulative); financing_source does NOT (it must describe THIS filing).
    prev_holdings_num = 0
    last_debt = "$6.7B"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT total_holdings, total_debt FROM purchase_history ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        if last_row:
            last_debt = last_row["total_debt"] or "$6.7B"
            try:
                prev_holdings_num = int(str(last_row["total_holdings"]).replace(',', '').replace(' ', ''))
            except (ValueError, TypeError):
                prev_holdings_num = 0
    except Exception:
        pass

    try:
        current_holdings_num = int(str(latest_holdings.get("holdings", "0")).replace(',', '').replace(' ', ''))
    except (ValueError, TypeError):
        current_holdings_num = 0

    inferred = False
    if activities:
        # PRIMARY: the filing's own activity tables state what happened.
        # "-" / "—" cells parse to 0, so an explicit "no transaction" week
        # yields net 0 regardless of what the DB contains.
        btc_net_signed = sum(a["signed_count"] for a in activities)
        if btc_net_signed > 0:
            event_type = "btc_purchase"
        elif btc_net_signed < 0:
            event_type = "btc_sale"
        else:
            event_type = "no_purchase"

        # CONSISTENCY CHECK ONLY — never changes event_type or amounts.
        # The saved row uses the filing's authoritative snapshot, so the DB
        # self-heals on this very insert and the mismatch cannot recur.
        if prev_holdings_num > 0 and current_holdings_num > 0:
            expected = prev_holdings_num + btc_net_signed
            if expected != current_holdings_num:
                print(
                    f"HOLDINGS CONSISTENCY WARNING: DB previous ({prev_holdings_num:,}) "
                    f"+ filing net ({btc_net_signed:+,}) = {expected:,}, but the filing "
                    f"reports {current_holdings_num:,}. The DB was stale; the filing "
                    f"snapshot is authoritative and will be saved."
                )
    else:
        # FALLBACK (labeled inference): the filing carries only a holdings
        # snapshot, no period-activity table. Only here may the delta vs the
        # DB be used, and the alert must say the amount is an estimate.
        if prev_holdings_num > 0 and current_holdings_num > 0:
            btc_net_signed = current_holdings_num - prev_holdings_num
        else:
            btc_net_signed = 0

        # A sale we did not read in the filing, we do not announce.
        #
        # This path once published "MSTR BTC SATTI: -839,172 BTC" — 99.5% of
        # the treasury — off a misparsed holdings figure, on a week MSTR had
        # in fact bought. Labelling it "(estimated)" is not a safeguard: the
        # headline is what reaches the channel. A real disposal is stated in
        # the filing's own BTC Sold table and goes down the primary path
        # above; a negative delta reached only by subtraction is far more
        # likely to be a parse failure, so treat it as one.
        if btc_net_signed < 0:
            print(f"REFUSING to infer a sale: holdings {prev_holdings_num:,} -> "
                  f"{current_holdings_num:,} ({btc_net_signed:+,}) with no BTC Sold "
                  f"table in the filing. Treating this as a parse failure.")
            return None

        # An inferred purchase is announced, but only when it is credible.
        # A jump larger than this is the same class of parse error pointing
        # the other way.
        if btc_net_signed > 0:
            if prev_holdings_num > 0 and btc_net_signed > prev_holdings_num * MAX_INFERRED_MOVE:
                print(f"REFUSING to infer a purchase of {btc_net_signed:,} BTC against a "
                      f"{prev_holdings_num:,} BTC balance — implausible, treating as a "
                      f"parse failure.")
                return None
            event_type = "btc_purchase"
            inferred = True
        else:
            event_type = "no_purchase"

    btc_signed_str = f"{btc_net_signed:,}"
    btc_abs_str = f"{abs(btc_net_signed):,}"

    if activities:
        periods = [a["period"] for a in activities]
        combined_period = " & ".join(periods)

        # Amounts and weighted average only over activities matching the
        # detected direction — a rare mixed buy+sell filing must not add
        # sale proceeds to purchase cost or blend both price averages.
        if event_type == "btc_sale":
            relevant = [a for a in activities if a["type"] == "sale"]
        elif event_type == "btc_purchase":
            relevant = [a for a in activities if a["type"] == "purchase"]
        else:
            relevant = []

        total_money_m = sum(parse_money(a["price"]) for a in relevant)

        # Weighted average price across the relevant periods
        weighted_sum = 0
        total_btc_for_avg = 0
        for a in relevant:
            btc_n = abs(a["signed_count"])
            try:
                avg_p = float(re.sub(r'\(\d+\)', '', a["avg_price"]).replace('$', '').replace(',', ''))
            except (ValueError, AttributeError):
                avg_p = 0
            weighted_sum += btc_n * avg_p
            total_btc_for_avg += btc_n
        weighted_avg = weighted_sum / total_btc_for_avg if total_btc_for_avg else 0

        # Format money
        if total_money_m >= 1000:
            display_money = f"${total_money_m/1000:.2f}B"
        elif total_money_m > 0:
            display_money = f"${total_money_m:.1f}M"
        else:
            display_money = "-"
    else:
        combined_period = latest_holdings.get("as_of", "-")
        display_money = "-"
        weighted_avg = 0

    result = {
        "event_type": event_type,
        "inferred": inferred,
        "purchase_period": combined_period,
        "btc_net_signed": btc_net_signed,
        "btc_signed_str": btc_signed_str,
        "btc_abs_str": btc_abs_str,
        # Unsigned amount for templates that add their own +/- prefix
        "btc_acquired": btc_abs_str,
        "purchase_price": display_money,
        "avg_price": f"${weighted_avg:,.0f}" if weighted_avg > 0 else "-",
        "total_holdings": latest_holdings.get("holdings", "-"),
        "total_cost": latest_holdings.get("total_cost", "-"),
        "avg_cost": latest_holdings.get("avg_cost", "-"),
        "total_debt": last_debt,
        "financing_details": "-",
        "summary_turkish": None,
    }

    # Per-period breakdown for multi-period filings (display + AI context)
    if activities and any(a["signed_count"] for a in activities):
        if event_type == "btc_sale":
            result["sale_breakdown"] = activities
        elif event_type == "btc_purchase":
            result["purchase_breakdown"] = activities
        else:
            result["mixed_breakdown"] = activities

    return result

ATM_TICKER_RE = re.compile(r'\b(MSTR|STRF|STRC|STRK|STRD)\b')

def parse_atm_table(tables):
    """Parse the at-the-market (ATM) offering table from pre-extracted tables.

    The table lists per-security share sales (MSTR common plus the
    STRF/STRC/STRK/STRD preferred series): Shares Sold, Notional Value,
    Net Proceeds and Available for Issuance. Returns None when the filing
    carries no ATM table.
    """
    for row_data in tables:
        header_idx = None
        for i, row in enumerate(row_data[:4]):
            joined = ' '.join(row)
            if 'Shares Sold' in joined and ('Net Proceeds' in joined or 'Available for Issuance' in joined):
                header_idx = i
                break
        if header_idx is None:
            continue

        # Period, if present in the rows above the column headers
        period = None
        for row in row_data[:header_idx]:
            for cell in row:
                if 'During Period' in cell:
                    period = cell.replace('During Period ', '').replace('*', '').strip()
                    break

        # A genuine WEEKLY table spans ~5-7 days. A cumulative program
        # summary ("July 2025 to May 2026") also matches the same headers
        # but must never be counted as one week's proceeds. Reject any
        # period window wider than 14 days as non-weekly.
        period_days = None
        if period:
            pdates = re.findall(r'([A-Z][a-z]+ \d{1,2}, \d{4})', period)
            if len(pdates) >= 2:
                try:
                    d0 = datetime.strptime(pdates[0], "%B %d, %Y")
                    d1 = datetime.strptime(pdates[-1], "%B %d, %Y")
                    period_days = (d1 - d0).days
                except ValueError:
                    period_days = None
        is_weekly = bool(period) and (period_days is None or period_days <= 14)

        # Column order after the security-name cell, with money units
        value_keys = []
        for h in row_data[header_idx]:
            h = re.sub(r'\(\d+\)', '', h).strip()
            hl = h.lower()
            unit = "M" if "millions" in hl else ("B" if "billions" in hl else "")
            if 'shares sold' in hl:
                value_keys.append(('shares_sold', ''))
            elif 'notional' in hl:
                value_keys.append(('notional', unit))
            elif 'net proceeds' in hl:
                value_keys.append(('net_proceeds', unit))
            elif 'available' in hl:
                value_keys.append(('available', unit))
        if not value_keys:
            continue
        proceeds_unit = dict(value_keys).get('net_proceeds', 'M')

        securities = []
        total_net_proceeds = "-"
        for row in row_data[header_idx + 1:]:
            first = row[0].strip()
            if first.lower().startswith('total'):
                cleaned = clean_row_values(row[1:])
                money = next((c for c in cleaned if c not in ('-', '')), None)
                if money:
                    if proceeds_unit and money.startswith('$') and not money.endswith(proceeds_unit):
                        money = f"{money}{proceeds_unit}"
                    total_net_proceeds = money
                continue

            # A footnote rendered INSIDE the table is still a <tr>, and one
            # of them reads "(4) As previously disclosed, on March 23, 2026,
            # Strategy announced a new $21.0 billion offering of MSTR Stock."
            # The ticker search below happily matched the MSTR in that
            # sentence and produced a second, all-blank MSTR security — which
            # then showed up in the alert as "MSTR: satış yok" on the very
            # week MSTR sold 4,531,421 shares.
            if re.match(r'\s*\(\d+\)', first):
                continue

            m = ATM_TICKER_RE.search(first)
            if m:
                ticker = m.group(1)
            elif 'Common Stock' in first:
                ticker = 'MSTR'
            else:
                # Description-continuation row (e.g. "10.00% Series A ...")
                continue

            cleaned = clean_row_values(row[1:])
            # A real security row always carries at least its remaining
            # capacity, even in a week it sold nothing. A row whose every
            # value cell is blank is prose that happens to name a ticker.
            if not any(v.strip() not in ('-', '') for v in cleaned):
                continue
            if any(sec["ticker"] == ticker for sec in securities):
                print(f"ATM table lists {ticker} more than once; keeping the first row.")
                continue

            while len(cleaned) < len(value_keys):
                cleaned.append('-')

            entry = {"ticker": ticker, "name": re.sub(r'\s+', ' ', first)}
            for (key, unit), val in zip(value_keys, cleaned):
                val = re.sub(r'\(\d+\)', '', val).strip() or '-'
                if val != '-' and unit and val.startswith('$') and not val.endswith(unit):
                    val = f"{val}{unit}"
                entry[key] = val
            entry["shares_sold_num"] = parse_btc_number(entry.get("shares_sold", "-"))
            entry["net_proceeds_num_m"] = parse_money(entry.get("net_proceeds", "-"))

            # --- Sanity guards against column misalignment ---
            # (e.g. the huge "Available for Issuance" capacity number leaking
            # into the Net Proceeds slot and inflating the cash estimate.)
            entry["suspect"] = None
            notional_m = parse_money(entry.get("notional", "-"))
            net_m = entry["net_proceeds_num_m"]
            shares = entry["shares_sold_num"]

            # HARD invariant: net proceeds can never exceed gross notional.
            # If it does, the net cell is corrupt — clamp it to the notional.
            if notional_m > 0 and net_m > notional_m * 1.02:
                entry["net_proceeds_num_m"] = round(notional_m, 4)
                entry["net_proceeds"] = entry.get("notional", "-")
                entry["suspect"] = f"net>notional ({net_m:.0f}M>{notional_m:.0f}M) → nominale sabitlendi"
                net_m = notional_m

            # Implied per-share sanity: preferreds are ~$100-par (trade
            # roughly $50-150); MSTR common is high but bounded. A value far
            # outside these bands means a shifted column — don't count it.
            if shares > 0 and net_m > 0:
                implied = net_m * 1e6 / shares
                lo, hi = (20.0, 5000.0) if ticker == "MSTR" else (5.0, 1000.0)
                if not (lo <= implied <= hi):
                    entry["suspect"] = (entry["suspect"] or "") + \
                        f" | hisse başı ${implied:,.0f} bandın dışında (${lo:.0f}-${hi:.0f})"
                    entry["counts"] = False
            securities.append(entry)

        if not securities:
            continue

        # A security "counts" only if it sold shares and isn't flagged by a
        # sanity guard (counts defaults True; guards set it False).
        sold = [s for s in securities
                if s["shares_sold_num"] > 0 and s.get("counts") is not False]
        # Recompute the badge total from sane, clamped values
        total_m = sum(s["net_proceeds_num_m"] for s in sold)
        if total_m >= 1000:
            total_net_proceeds = f"${total_m/1000:.2f}B"
        elif total_m > 0:
            total_net_proceeds = f"${total_m:.1f}M"

        return {
            # fmt 3 = period_scoped + column-misalignment sanity guards;
            # the backfill re-parses any stored JSON older than this format
            "fmt": 4,
            "period": period,
            "period_days": period_days,
            # Only weekly ("During Period", ≤14 days) tables count as one
            # week's sales. Cumulative program summaries match the same
            # headers but must NEVER be counted — that inflates the cash
            # estimate massively.
            "period_scoped": is_weekly,
            "securities": securities,
            "sold_tickers": [s["ticker"] for s in sold],
            "sold_any": bool(sold),
            "total_net_proceeds": total_net_proceeds,
        }
    return None

def financing_source_from_atm(atm):
    """Dashboard/DB badge text derived from THIS filing's ATM table only."""
    if not atm or not atm.get("sold_any"):
        return "-"
    tickers = " & ".join(atm["sold_tickers"])
    total = atm.get("total_net_proceeds") or "-"
    if total != "-":
        return f"{tickers} ATM ({total})"
    return f"{tickers} ATM"

# ----------------- CASH RESERVES (SEC XBRL) -----------------

# Weekly 8-Ks never disclose the cash balance; the quarterly 10-Q/10-K
# balance sheet — exposed by the free XBRL companyconcept API on the same
# data.sec.gov host we already poll — is the only real source.
CASH_XBRL_URL = ("https://data.sec.gov/api/xbrl/companyconcept/CIK0001050446/"
                 "us-gaap/CashAndCashEquivalentsAtCarryingValue.json")

_cash_shape_logged = False

def fetch_cash_reserves():
    """Fetch the quarterly Cash & Cash Equivalents series from SEC XBRL.

    Entries carrying a `frame` like "CY2026Q1I" are the canonical value for
    that quarter; otherwise the most recently filed entry per period end
    wins (10-K comparatives repeat earlier quarters). Returns a
    chronological list of {end, val, form, filed}; [] on any failure.
    """
    global _cash_shape_logged
    try:
        resp = http_session.get(CASH_XBRL_URL, timeout=5)
        if resp.status_code != 200:
            print(f"Cash XBRL fetch failed: HTTP {resp.status_code}")
            return []
        data = resp.json()
        entries = (data.get("units") or {}).get("USD") or []
        if entries and not _cash_shape_logged:
            _cash_shape_logged = True
            print(f"CASH first-response shape (one-time log): {json.dumps(entries[-1])[:400]}")

        by_end = {}
        for e in entries:
            end = e.get("end")
            val = e.get("val")
            if not end or val is None:
                continue
            frame = e.get("frame") or ""
            candidate = {
                "end": end,
                "val": float(val),
                "form": e.get("form", "-"),
                "filed": e.get("filed", ""),
                "_canonical": bool(re.match(r'^CY\d{4}(Q\d)?I$', frame)),
            }
            current = by_end.get(end)
            if (current is None
                    or (candidate["_canonical"] and not current["_canonical"])
                    or (candidate["_canonical"] == current["_canonical"]
                        and candidate["filed"] > current["filed"])):
                by_end[end] = candidate

        results = sorted(by_end.values(), key=lambda x: x["end"])
        for r in results:
            r.pop("_canonical", None)
        return results
    except Exception as e:
        print(f"Cash XBRL fetch error: {e}")
        return []

def refresh_cash_reserves():
    """Upsert the quarterly cash series into financial_metrics (idempotent)."""
    quarters = fetch_cash_reserves()
    if not quarters:
        return 0
    try:
        conn = get_db_connection()
        for q in quarters:
            conn.execute(
                """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
                   VALUES ('cash_and_equivalents', ?, ?, ?, ?)""",
                (q["end"], q["val"], q["form"], q["filed"])
            )
        conn.commit()
        conn.close()
        latest = quarters[-1]
        print(f"Cash reserves: {len(quarters)} quarter(s) stored "
              f"(latest: {latest['end']} = ${latest['val']:,.0f})")
        return len(quarters)
    except Exception as e:
        print(f"Cash reserves DB update failed: {e}")
        return 0

# --- Strategy's own published figures (strategy.com dashboard) ---
# Strategy publishes its actual USD Reserve, Annual Dividends, total Pref
# outstanding and Debt, updated ~daily — ground truth that beats our
# weekly estimate. We can't scrape their site from every environment, so
# these come from env and/or the password-protected /api/official endpoint.
def _official_env():
    def _f(name):
        v = os.getenv(name, "").strip()
        try:
            return float(v) if v else None
        except ValueError:
            return None
    return {
        "usd_reserve_m": _f("STRATEGY_USD_RESERVE_M"),
        "annual_dividends_m": _f("STRATEGY_ANNUAL_DIVIDENDS_M"),
        "pref_m": _f("STRATEGY_PREF_M"),
        "debt_m": _f("STRATEGY_DEBT_M"),
        "asof": os.getenv("STRATEGY_ASOF", "").strip() or None,
    }

def store_official_figures(usd_reserve_m=None, annual_dividends_m=None,
                           pref_m=None, debt_m=None, asof=None):
    """Persist Strategy's official figures. The USD reserve is stored as a
    cash_and_equivalents actual (form 'strategy.com') so it becomes the most
    recent anchor for the estimate, chart and runway automatically."""
    if not asof:
        return 0
    stored = 0
    try:
        conn = get_db_connection()
        if usd_reserve_m is not None:
            conn.execute(
                """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
                   VALUES ('cash_and_equivalents', ?, ?, 'strategy.com', ?)""",
                (asof, usd_reserve_m * 1e6, asof))
            stored += 1
        for metric, val in (("official_annual_dividends", annual_dividends_m),
                            ("official_pref", pref_m),
                            ("official_debt", debt_m)):
            if val is not None:
                conn.execute(
                    """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
                       VALUES (?, ?, ?, 'strategy.com', ?)""",
                    (metric, asof, val * 1e6, asof))
                stored += 1
        conn.commit()
        conn.close()
        if usd_reserve_m is not None:
            print(f"Official figures stored (strategy.com, {asof}): "
                  f"USD reserve ${usd_reserve_m:,.0f}M")
        return stored
    except Exception as e:
        print(f"store_official_figures failed: {e}")
        return 0

def sync_official_figures_from_env():
    o = _official_env()
    if o["asof"] and any(o[k] is not None for k in
                         ("usd_reserve_m", "annual_dividends_m", "pref_m", "debt_m")):
        store_official_figures(o["usd_reserve_m"], o["annual_dividends_m"],
                               o["pref_m"], o["debt_m"], o["asof"])

def get_official_metric(metric):
    """Latest stored official metric value in $M, or None."""
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT period_end, value FROM financial_metrics WHERE metric = ? "
            "ORDER BY period_end DESC LIMIT 1", (metric,)).fetchone()
        conn.close()
        if row:
            return {"period_end": row["period_end"], "value_m": row["value"] / 1e6}
    except Exception:
        pass
    return None

# MSTR discloses its USD Reserve (cash held to fund preferred dividends and
# debt interest) in the text of every weekly 8-K, e.g. "a USD Reserve of
# $3.0 billion" / "increased its USD Reserve to $3.0 billion". We already
# fetch that filing — parse the figure straight from the text.
_usd_reserve_logged = False
_RESERVE_PATTERNS = [
    re.compile(r'(?:USD Reserve|U\.?\s*S\.?\s*dollar reserve|cash reserve|dollar reserve)'
               r'[^.$]{0,90}?\$\s*([\d][\d,.]*)\s*(billion|million)', re.IGNORECASE),
    re.compile(r'\$\s*([\d][\d,.]*)\s*(billion|million)[^.]{0,60}?'
               r'(?:USD\s*)?(?:dollar\s*)?reserve', re.IGNORECASE),
]

def parse_usd_reserve(text):
    """Extract the disclosed USD Reserve from filing text, in $M. None if absent."""
    global _usd_reserve_logged
    if not text:
        return None
    for pat in _RESERVE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        try:
            num = float(m.group(1).replace(',', ''))
        except (ValueError, AttributeError):
            continue
        unit = m.group(2).lower()
        val_m = num * 1000.0 if unit.startswith('b') else num
        # Sanity band: a reserve between $100M and $50B
        if not (100.0 <= val_m <= 50000.0):
            continue
        if not _usd_reserve_logged:
            _usd_reserve_logged = True
            snippet = text[max(0, m.start() - 40):m.end() + 40].strip()
            print(f"USD reserve parsed (one-time log): '...{snippet}...' → ${val_m:,.0f}M")
        return round(val_m, 1)
    return None

MAX_RESERVE_WINDOWS = int(os.getenv("MAX_RESERVE_WINDOWS", "24"))

def parse_usd_reserve_fast(html):
    """Sub-millisecond reserve extraction for the alert-critical path.

    Scans the raw HTML for 'reserve', strips tags only in a local window and
    runs the text patterns on it — avoids a full clean_html parse before the
    first Telegram message goes out.
    """
    if not html:
        return None
    # Cost is linear in the number of 'reserve' hits, and each hit rebuilds a
    # 4KB window with three regex passes. A filing full of boilerplate
    # ("reserves the right to", "reserve requirements") drove this past the
    # full-text parse it exists to avoid — 137ms measured at 600 hits, on the
    # path ahead of the first Telegram byte. Skip windows already covered and
    # stop after a bounded number of misses; the background full-text parse
    # still runs when this returns None, so nothing is lost but the tail.
    scanned_to = -1
    windows = 0
    for m in re.finditer(r'[Rr]eserve', html):
        if m.start() <= scanned_to:
            continue
        start = max(0, m.start() - 2000)
        end = m.start() + 2000
        scanned_to = end - 500
        windows += 1
        if windows > MAX_RESERVE_WINDOWS:
            break
        text = re.sub(r'<[^>]+>', ' ', html[start:end])
        text = re.sub(r'&nbsp;|&#160;|&amp;', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        val = parse_usd_reserve(text)
        if val is not None:
            return val
    return None

def _fmt_musd(m):
    """Format a $M amount: $450.0M / $3.00B."""
    if m is None:
        return "-"
    return f"${m/1000:.2f}B" if abs(m) >= 1000 else f"${m:.1f}M"

# Short-TTL memos for the two derived figures the alert decorates itself
# with. Quarterly inputs, so staleness is measured in minutes at worst.
DERIVED_TTL = float(os.getenv("DERIVED_TTL", "600"))
_derived_cache = {}
_derived_lock = threading.Lock()

def _memo(key, fn):
    now = time.time()
    hit = _derived_cache.get(key)
    if hit and now - hit[0] < DERIVED_TTL:
        return hit[1]
    with _derived_lock:
        hit = _derived_cache.get(key)
        if hit and time.time() - hit[0] < DERIVED_TTL:
            return hit[1]
        val = fn()
        _derived_cache[key] = (time.time(), val)
        return val

def _cached_annual_dividends():
    return _memo("annual_dividends", compute_annual_dividends)

def _cached_cash_estimate():
    return _memo("cash_estimate", compute_cash_estimate)

def invalidate_derived_cache():
    _derived_cache.clear()

def build_reserve_context(filing_date, html_content):
    """Parse this filing's USD Reserve, store it, and compute the runway.

    Returns alert-template fields (reserve, change vs previous week, months
    of coverage) or None when the filing has no reserve statement. Built for
    the alert path: windowed raw-HTML parse + math over a ~20 row table.
    """
    reserve_m = parse_usd_reserve_fast(html_content)
    if reserve_m is None:
        return None

    prev_m = None
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT value FROM financial_metrics WHERE metric='usd_reserve' "
            "AND period_end < ? ORDER BY period_end DESC LIMIT 1",
            (filing_date,)).fetchone()
        conn.close()
        if row:
            prev_m = row["value"] / 1e6
    except Exception:
        pass

    # The INSERT+commit used to run here, ahead of the alert. On a
    # network-backed volume that is several fsyncs, and behind another
    # writer it could block for the full SQLite busy timeout — seconds of
    # delay on the alert, to persist a number the alert does not need.
    threading.Thread(target=store_usd_reserve, args=(filing_date, reserve_m),
                     daemon=True).start()

    ctx = {
        "usd_reserve_m": reserve_m,
        "reserve_prev_m": round(prev_m, 1) if prev_m is not None else None,
        "reserve_change_m": round(reserve_m - prev_m, 1) if prev_m is not None else None,
        "runway_weeks": None,
        "runway_months": None,
        "runway_infinite": False,
        "annual_div_m": None,
        "div_source": None,
    }
    try:
        # Months of coverage = reserve ÷ (official annual dividends / 12) —
        # MSTR's own framing for the reserve ("at least twelve months of
        # dividends"), using strategy.com's Annual Dividends figure derived
        # automatically from SEC data.
        #
        # Both of these walk the whole purchase history with a json.loads per
        # row (twice, and a third time via compute_cash_estimate), which grows
        # with every filing and used to run inline before the alert. The
        # inputs are 10-Q/XBRL figures that move quarterly, so a short TTL
        # cache keeps the alert path reading a number instead of deriving one.
        annual = _cached_annual_dividends()
        if annual["annual_m"] > 0:
            ctx["annual_div_m"] = annual["annual_m"]
            ctx["div_source"] = annual["source"]
            ctx["runway_months"] = round(reserve_m / (annual["annual_m"] / 12.0), 1)
            ctx["runway_weeks"] = round(reserve_m / (annual["annual_m"] / 52.0), 1)
        else:
            # No dividend data at all — fall back to the calibrated runway
            flow = _cached_cash_estimate() or {}
            r = flow.get("runway") or {}
            if r.get("infinite"):
                ctx["runway_infinite"] = True
            elif r.get("weeks") is not None:
                ctx["runway_weeks"] = r["weeks"]
                ctx["runway_months"] = round(r["weeks"] / 4.345, 1)
    except Exception as e:
        print(f"Reserve runway computation failed: {e}")
    return ctx

def store_usd_reserve(filing_date, value_m):
    """Upsert a weekly USD Reserve datapoint (form 'sec-8k')."""
    if value_m is None or not filing_date:
        return False
    try:
        conn = get_db_connection()
        conn.execute(
            """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
               VALUES ('usd_reserve', ?, ?, 'sec-8k', ?)""",
            (filing_date, value_m * 1e6, filing_date))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"store_usd_reserve failed: {e}")
        return False

def fetch_xbrl_concept(tag):
    """Fetch a raw us-gaap companyconcept payload; None on failure."""
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK0001050446/us-gaap/{tag}.json"
    try:
        resp = http_session.get(url, timeout=5)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as e:
        print(f"XBRL fetch error for {tag}: {e}")
        return None

def _quarterly_duration_series(entries):
    """Convert XBRL duration entries (quarterly + FY) into quarterly values.

    Entries with quarterly frames ("CY2026Q1") are canonical. A missing Q4
    is derived from FY − (Q1+Q2+Q3) when all three are present (10-Ks only
    report the annual total).
    """
    quarters = {}
    fiscal_years = {}
    for e in entries:
        val = e.get("val")
        end = e.get("end")
        if val is None or not end:
            continue
        frame = e.get("frame") or ""
        m = re.match(r'^CY(\d{4})Q(\d)$', frame)
        if m:
            quarters[(int(m.group(1)), int(m.group(2)))] = {
                "end": end, "val": float(val), "form": e.get("form", "-")}
            continue
        m = re.match(r'^CY(\d{4})$', frame)
        if m:
            fiscal_years[int(m.group(1))] = float(val)

    for year, total in fiscal_years.items():
        if (year, 4) not in quarters and all((year, q) in quarters for q in (1, 2, 3)):
            q123 = sum(quarters[(year, q)]["val"] for q in (1, 2, 3))
            quarters[(year, 4)] = {"end": f"{year}-12-31", "val": total - q123, "form": "10-K (derived)"}

    return [v for _, v in sorted(quarters.items())]

# Preferred dividends actually PAID per quarter (cash-flow statement).
# Tag names vary between filers; try candidates in order.
DIVIDEND_TAG_CANDIDATES = [
    "PaymentsOfDividendsPreferredStockAndPreferenceStock",
    "PaymentsOfDividends",
    "DividendsPreferredStock",
]

def refresh_dividends():
    """Upsert the quarterly dividends-paid series from SEC XBRL."""
    for tag in DIVIDEND_TAG_CANDIDATES:
        data = fetch_xbrl_concept(tag)
        entries = ((data or {}).get("units") or {}).get("USD") or []
        series = _quarterly_duration_series(entries)
        if not series:
            continue
        try:
            conn = get_db_connection()
            for s in series:
                conn.execute(
                    """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
                       VALUES ('dividends_paid', ?, ?, ?, ?)""",
                    (s["end"], s["val"], s["form"], tag)
                )
            conn.commit()
            conn.close()
            print(f"Dividends: {len(series)} quarter(s) stored from {tag} "
                  f"(latest: {series[-1]['end']} = ${series[-1]['val']:,.0f})")
            return len(series)
        except Exception as e:
            print(f"Dividends DB update failed: {e}")
            return 0
    print("Dividends: no usable XBRL tag returned data")
    return 0

# The weekly 8-K carries the BTC and ATM tables and nothing about debt — I
# checked every fixture for debt/notes/convertible/indebtedness and found
# none. So the figure came from nowhere: "$6.7B" was seeded, then carried
# forward filing after filing (the Groq prompt even instructs the model to
# keep the previous value), which made the debt chart a flat wall by
# construction. Take it from the same XBRL source the cash series uses.
DEBT_TAG_CANDIDATES = [
    "DebtLongtermAndShorttermCombinedAmount",
    "LongTermDebtNoncurrent",
    "LongTermDebt",
    "ConvertibleNotesPayable",
    "ConvertibleLongTermNotesPayable",
]

def _instant_series(entries):
    """Latest value per period end for an instant-type XBRL concept.

    Balance-sheet concepts are instants, not durations, so
    _quarterly_duration_series (which keys on start+end) does not apply. A
    period end appears in several filings as it is restated; the most
    recently FILED wins.
    """
    by_end = {}
    for e in entries:
        end = e.get("end")
        val = e.get("val")
        if not end or val is None:
            continue
        prev = by_end.get(end)
        if prev is None or (e.get("filed") or "") >= (prev.get("filed") or ""):
            by_end[end] = e
    return [{"end": k, "val": float(v["val"]), "form": v.get("form", ""),
             "filed": v.get("filed", "")}
            for k, v in sorted(by_end.items())]

def refresh_total_debt():
    """Upsert the quarterly total-debt series from SEC XBRL."""
    for tag in DEBT_TAG_CANDIDATES:
        data = fetch_xbrl_concept(tag)
        entries = ((data or {}).get("units") or {}).get("USD") or []
        series = _instant_series(entries)
        if not series:
            continue
        try:
            conn = get_db_connection()
            for s in series:
                conn.execute(
                    """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
                       VALUES ('total_debt', ?, ?, ?, ?)""",
                    (s["end"], s["val"], s["form"], tag))
            conn.commit()
            conn.close()
            print(f"Total debt: {len(series)} quarter(s) stored from {tag} "
                  f"(latest: {series[-1]['end']} = ${series[-1]['val']:,.0f})")
            return len(series)
        except Exception as e:
            print(f"Total debt DB update failed: {e}")
            return 0
    print("Total debt: no usable XBRL tag returned data")
    return 0

def latest_total_debt():
    """(value_usd, period_end) from XBRL, or (None, None).

    Callers must label the period_end: this is a QUARTERLY balance-sheet
    figure sitting on a page of weekly numbers, and an unlabelled stale
    figure is exactly how "$6.7B" went unquestioned for months.
    """
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT value, period_end FROM financial_metrics "
            "WHERE metric = 'total_debt' ORDER BY period_end DESC LIMIT 1").fetchone()
        conn.close()
        return (row["value"], row["period_end"]) if row else (None, None)
    except Exception as e:
        print(f"latest_total_debt error: {e}")
        return (None, None)

# ----------------- PREFERRED BASELINES (SEC 10-Q) -----------------

# strategy.com's "Annual Dividends" (~$1,763M) is the FORWARD obligation:
# Σ outstanding preferred notional × dividend rate. Trailing paid dividends
# badly lag it while the stack grows (Q1-2026 paid $229.5M ×4 ≈ $0.9B).
# The per-series notional and rates are disclosed in every 10-Q/10-K
# preferred stock table; the weekly 8-K ATM tables carry them forward.

EURUSD_RATE = float(os.getenv("EURUSD_RATE", "1.08"))

def parse_preferred_stock_table(tables):
    """Extract per-series preferred notional ($M) and dividend rate from a
    10-Q/10-K preferred stock summary table.

    Generic across series (STRF/STRK/STRD/STRC/STRE/future ones): a row
    names one series and carries a shares/notional pair whose ratio is ~100
    (the $100 stated liquidation preference per share) — that also reveals
    the number scale. Euro-denominated series are converted at EURUSD_RATE.
    ATM-activity tables are excluded (they say "net proceeds"/"available").
    Returns {ticker: {"notional_m": .., "rate": ..}}, best table wins.
    """
    best = {}
    for row_data in tables:
        table_text = ' '.join(' '.join(r) for r in row_data)
        if len([t for t in ('STRF', 'STRK', 'STRD', 'STRC', 'STRE') if t in table_text]) < 2:
            continue
        lower = table_text.lower()
        # The summary table lists notional/liquidation value of OUTSTANDING
        # shares; skip ATM offering tables which also name every series.
        if 'notional' not in lower and 'liquidation' not in lower:
            continue
        if 'net proceeds' in lower or 'available' in lower:
            continue
        found = {}
        for row in row_data:
            row_text = ' '.join(row)
            m = re.search(r'\b(STR[A-Z])\b', row_text)
            if not m:
                continue
            ticker = m.group(1)
            rate = None
            rm = re.search(r'(\d+(?:\.\d+)?)\s*%', row_text)
            if rm:
                r = float(rm.group(1)) / 100.0
                if 0.02 <= r <= 0.25:
                    rate = r
            nums = []
            for cell in row:
                # Percentages are rates, not amounts
                cell = re.sub(r'\d+(?:\.\d+)?\s*%', ' ', cell)
                for n in re.findall(r'\d[\d,]*(?:\.\d+)?', cell):
                    try:
                        nums.append(float(n.replace(',', '')))
                    except ValueError:
                        pass
            # shares/notional pair at the ~$100 stated value per share
            pair = None
            for a in nums:
                for b in nums:
                    if a > 0 and b > a and 95.0 <= b / a <= 105.0:
                        if pair is None or b > pair[1]:
                            pair = (a, b)
            if not pair:
                continue
            notional = pair[1]
            if notional >= 1e8:        # raw dollars
                notional_m = notional / 1e6
            elif notional >= 1e4:      # thousands (the usual 10-Q unit)
                notional_m = notional / 1e3
            else:                      # already millions
                notional_m = notional
            if '€' in row_text or 'EUR' in row_text.upper() or 'uro' in row_text:
                notional_m *= EURUSD_RATE
            if not (50.0 <= notional_m <= 50000.0):
                continue
            found[ticker] = {"notional_m": round(notional_m, 1), "rate": rate}
        if len(found) > len(best):
            best = found
    # Rows without an in-row rate fall back to the known series defaults
    for t, e in best.items():
        if e["rate"] is None:
            e["rate"] = STRC_ANNUAL_RATE if t == 'STRC' else PREFERRED_RATE_DEFAULTS.get(t)
    return {t: e for t, e in best.items() if e["rate"]}

def refresh_preferred_baselines():
    """Store per-series preferred notional + rate from the latest 10-Q/10-K.

    Effectively quarterly: skips when the newest quarterly report's period
    is already stored. On any failure the annual-dividend figure simply
    falls back to the XBRL paid-×4 tier — no regression.
    """
    data = fetch_mstr_filings(use_conditional=False)
    recent = ((data or {}).get('filings') or {}).get('recent') or {}
    forms = recent.get('form', [])
    accs = recent.get('accessionNumber', [])
    dates = recent.get('filingDate', [])
    docs = recent.get('primaryDocument', [])
    reports = recent.get('reportDate', [])
    idx = next((i for i, f in enumerate(forms) if f in ('10-Q', '10-K')), None)
    if idx is None:
        return 0
    period_end = reports[idx] if idx < len(reports) and reports[idx] else dates[idx]
    try:
        conn = get_db_connection()
        have = conn.execute(
            "SELECT 1 FROM financial_metrics WHERE metric LIKE 'pref_notional_%' "
            "AND period_end = ? LIMIT 1", (period_end,)).fetchone()
        conn.close()
        if have:
            return 0
    except Exception:
        pass

    url = (f"https://www.sec.gov/Archives/edgar/data/1050446/"
           f"{accs[idx].replace('-', '')}/{docs[idx]}")
    html = fetch_html(url)
    if not html:
        print(f"Preferred baselines: could not fetch {url}")
        return 0
    series = parse_preferred_stock_table(extract_filing_tables(html))
    if not series:
        print(f"Preferred baselines: no preferred table parsed in {docs[idx]} — "
              f"annual dividends stay on the XBRL paid-×4 fallback")
        return 0
    try:
        conn = get_db_connection()
        for t, e in series.items():
            conn.execute(
                """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
                   VALUES (?, ?, ?, ?, ?)""",
                (f'pref_notional_{t}', period_end, e['notional_m'] * 1e6, forms[idx], dates[idx]))
            conn.execute(
                """INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed)
                   VALUES (?, ?, ?, ?, ?)""",
                (f'pref_rate_{t}', period_end, e['rate'], forms[idx], dates[idx]))
        conn.commit()
        conn.close()
        total = sum(e['notional_m'] * e['rate'] for e in series.values())
        print(f"Preferred baselines from {forms[idx]} {period_end}: " +
              ", ".join(f"{t} ${e['notional_m']:,.0f}M @{e['rate'] * 100:.2f}%"
                        for t, e in sorted(series.items())) +
              f" → forward annual ≈ ${total:,.0f}M (+ATM since)")
        return len(series)
    except Exception as e:
        print(f"Preferred baselines DB write failed: {e}")
        return 0

# Don't start a job that runs for minutes right before the window opens.
ULTRA_LEAD_IN = float(os.getenv("ULTRA_LEAD_IN", "600"))

def _wait_out_ultra_window(label):
    """Hold heavy background work out of the ultra window only.

    These loops parse multi-MB documents with BeautifulSoup, which holds the
    GIL; a parse overlapping the alert path was measured inflating its
    network round trips several-fold. cash_refresh_loop in particular slept a
    flat 12h anchored to process start, so its phase was fixed by deploy time
    and could land on the filing window every single day.

    Gating on the whole fast band was too blunt: that band is twelve hours,
    so a weekday deploy at 10:00 ET postponed the historical backfill until
    evening and left the dashboard half-populated all day. Contention only
    matters where ticks are 250ms apart and a filing may actually land, so
    the gate is the ultra window plus a lead-in long enough that a job which
    runs for minutes cannot spill into it.
    """
    announced = False
    while running:
        mode, _, to_boundary = poll_schedule(now_et())
        opening_soon = mode == "Fast Mode" and to_boundary <= ULTRA_LEAD_IN
        if mode != "Ultra High-Speed Mode" and not opening_soon:
            return
        if not announced:
            announced = True
            print(f"Deferring {label} until the ultra window closes.")
        time.sleep(60)

def cash_refresh_loop():
    """Refresh the quarterly cash + dividend data at startup and every 12 hours."""
    while running:
        _wait_out_ultra_window("quarterly cash/dividend refresh")
        try:
            refresh_cash_reserves()
            refresh_dividends()
            refresh_total_debt()
            refresh_preferred_baselines()
            sync_official_figures_from_env()
            invalidate_derived_cache()
        except Exception as e:
            print(f"Cash refresh loop error: {e}")
        time.sleep(12 * 3600)

# ----------------- DIVIDEND MODEL & CASH ESTIMATE -----------------

# Dividend model configuration. Baselines = outstanding face value ($M) of
# each preferred series BEFORE our ATM data window begins — set them from
# the latest 10-Q via env; 0 means the model only counts the ATM sales we
# observed ourselves. STRC's rate is variable (announced monthly by MSTR),
# so it comes from config; the fixed-rate series' rates are parsed from the
# security names stored in atm_sales (e.g. "10.00% Series A ... Strife").
PREFERRED_BASELINE_AS_OF = os.getenv("PREFERRED_BASELINE_AS_OF", "2026-02-01")
PREFERRED_BASELINE_NOTIONAL_M = {
    "STRF": float(os.getenv("STRF_BASELINE_M", "0")),
    "STRK": float(os.getenv("STRK_BASELINE_M", "0")),
    "STRD": float(os.getenv("STRD_BASELINE_M", "0")),
    "STRC": float(os.getenv("STRC_BASELINE_M", "0")),
}
STRC_ANNUAL_RATE = float(os.getenv("STRC_ANNUAL_RATE", "0.10"))
PREFERRED_RATE_DEFAULTS = {"STRF": 0.10, "STRK": 0.08, "STRD": 0.10}

def compute_dividend_model():
    """Per-series dividend cost model + comparison to actual paid dividends.

    Outstanding face value per series = the latest 10-Q preferred table's
    notional (parsed automatically into pref_notional_*/pref_rate_*
    metrics) + ATM notional sold since that quarter end — the same official
    building blocks the annual figure uses. Legacy fallback when no 10-Q
    has been parsed yet: env baselines + tracked ATM sales since
    PREFERRED_BASELINE_AS_OF. MSTR common pays no dividend and is excluded.
    """
    latest_actual = None
    rows = []
    pref_rows = []
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT filing_date, atm_sales FROM purchase_history "
            "WHERE atm_sales IS NOT NULL AND atm_sales <> '' ORDER BY filing_date").fetchall()
        actual = conn.execute(
            "SELECT period_end, value FROM financial_metrics "
            "WHERE metric='dividends_paid' ORDER BY period_end DESC LIMIT 1").fetchone()
        pref_rows = conn.execute(
            "SELECT metric, period_end, value FROM financial_metrics "
            "WHERE metric LIKE 'pref_%'").fetchall()
        conn.close()
        if actual:
            latest_actual = {"period_end": actual["period_end"], "paid_usd": actual["value"]}
    except Exception as e:
        print(f"compute_dividend_model DB error: {e}")

    # Automatic baselines: the latest 10-Q preferred table
    pref_rows = [r for r in pref_rows
                 if r["metric"].startswith(("pref_notional_", "pref_rate_"))]
    tenq = {}
    tenq_pe = None
    if pref_rows:
        tenq_pe = max(r["period_end"] for r in pref_rows)
        for r in pref_rows:
            if r["period_end"] != tenq_pe:
                continue
            if r["metric"].startswith("pref_notional_"):
                tenq.setdefault(r["metric"][len("pref_notional_"):], {})["notional_m"] = r["value"] / 1e6
            else:
                tenq.setdefault(r["metric"][len("pref_rate_"):], {})["rate"] = r["value"]

    tickers = ["STRF", "STRK", "STRD", "STRC"]
    tickers += sorted(t for t in tenq if t not in tickers)
    series = {t: {"ticker": t, "rate": None, "rate_source": None, "atm_notional_m": 0.0}
              for t in tickers}

    for row in rows:
        atm = _safe_json_loads(row["atm_sales"]) or {}
        period_scoped = atm.get("period_scoped") is not False
        for s in atm.get("securities", []):
            t = s.get("ticker")
            if t not in series:
                continue
            e = series[t]
            if e["rate"] is None:
                m = re.search(r'(\d+(?:\.\d+)?)\s*%', s.get("name") or "")
                if m:
                    e["rate"] = float(m.group(1)) / 100.0
                    e["rate_source"] = "filing_name"
            # Issuance counts on top of the baseline: strictly after the
            # 10-Q quarter end (it is already inside that table otherwise),
            # or the env window when no 10-Q has been parsed yet. Cumulative
            # tables and sanity-flagged rows are never added.
            counted = (row["filing_date"] > tenq_pe) if tenq_pe else \
                      (row["filing_date"] >= PREFERRED_BASELINE_AS_OF)
            if (period_scoped and s.get("counts") is not False
                    and (s.get("shares_sold_num") or 0) > 0 and counted):
                notional_m = parse_money(s.get("notional", "-"))
                if not notional_m:
                    # Some rows only carry net proceeds — close approximation
                    notional_m = parse_money(s.get("net_proceeds", "-"))
                e["atm_notional_m"] += notional_m

    out = []
    total_monthly_m = 0.0
    for t in tickers:
        e = series[t]
        rate = e["rate"]
        rate_source = e["rate_source"]
        if tenq.get(t, {}).get("rate"):
            rate = tenq[t]["rate"]          # the 10-Q's stated rate wins
            rate_source = "10-Q"
        if rate is None:
            if t == "STRC":
                rate = STRC_ANNUAL_RATE
                rate_source = "config (variable)"
            else:
                rate = PREFERRED_RATE_DEFAULTS.get(t, 0.0)
                rate_source = "default"
        baseline_m = tenq.get(t, {}).get("notional_m")
        if baseline_m is None:
            baseline_m = PREFERRED_BASELINE_NOTIONAL_M.get(t, 0.0)
        outstanding_m = baseline_m + e["atm_notional_m"]
        monthly_m = outstanding_m * rate / 12.0
        total_monthly_m += monthly_m
        out.append({
            "ticker": t,
            "rate": rate,
            "rate_source": rate_source,
            "frequency": "aylık" if t == "STRC" else "çeyreklik",
            "baseline_notional_m": round(baseline_m, 1),
            "atm_notional_m": round(e["atm_notional_m"], 1),
            "outstanding_notional_m": round(outstanding_m, 1),
            "monthly_cost_m": round(monthly_m, 2),
        })

    result = {
        "series": out,
        "model_monthly_total_m": round(total_monthly_m, 2),
        "baselines_configured": bool(tenq) or any(v > 0 for v in PREFERRED_BASELINE_NOTIONAL_M.values()),
        "baseline_source": f"10-Q ({tenq_pe})" if tenq else "env",
        "actual_last_quarter": None,
        "model_vs_actual_pct": None,
        "official": None,
    }
    # Strategy's own published Annual Dividends + total Pref (ground truth)
    off_div = get_official_metric("official_annual_dividends")
    off_pref = get_official_metric("official_pref")
    if off_div or off_pref:
        result["official"] = {
            "asof": (off_div or off_pref).get("period_end"),
            "annual_dividends_m": round(off_div["value_m"], 1) if off_div else None,
            "monthly_dividends_m": round(off_div["value_m"] / 12.0, 1) if off_div else None,
            "pref_outstanding_m": round(off_pref["value_m"], 1) if off_pref else None,
            "source": "strategy.com",
        }
    if latest_actual:
        result["actual_last_quarter"] = {
            "period_end": latest_actual["period_end"],
            "paid_usd": latest_actual["paid_usd"],
            "monthly_avg_usd": latest_actual["paid_usd"] / 3.0,
        }
        if latest_actual["paid_usd"]:
            model_quarter_usd = total_monthly_m * 3 * 1e6
            result["model_vs_actual_pct"] = round(
                (model_quarter_usd - latest_actual["paid_usd"]) / latest_actual["paid_usd"] * 100, 1)
    return result

def _preferred_atm_added_annual(since_date, rates):
    """Preferred ATM issuance after a given date: returns
    (added annual dividends $M/yr, added notional $M)."""
    added_m = 0.0
    added_notional_m = 0.0
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT filing_date, atm_sales FROM purchase_history "
            "WHERE atm_sales IS NOT NULL AND atm_sales <> '' AND filing_date > ? "
            "ORDER BY filing_date", (since_date,)).fetchall()
        conn.close()
    except Exception as e:
        print(f"_preferred_atm_added_annual DB error: {e}")
        return 0.0, 0.0
    for row in rows:
        atm = _safe_json_loads(row["atm_sales"]) or {}
        if atm.get("period_scoped") is False:
            continue
        for s in atm.get("securities", []):
            t = s.get("ticker")
            if t not in rates or s.get("counts") is False:
                continue
            if (s.get("shares_sold_num") or 0) <= 0:
                continue
            notional_m = parse_money(s.get("notional", "-"))
            if not notional_m:
                notional_m = parse_money(s.get("net_proceeds", "-"))
            added_m += (notional_m or 0.0) * (rates[t] or 0.0)
            added_notional_m += (notional_m or 0.0)
    return added_m, added_notional_m

def compute_annual_dividends():
    """Annual dividend obligation — the figure strategy.com publishes as
    "Annual Dividends" (~$1,763M), derived automatically from official SEC
    data (no manual entry).

    That figure is the FORWARD obligation, Σ outstanding preferred notional
    × rate — NOT trailing payments (Q1-2026 actually paid $229.5M, ×4 ≈
    $0.9B, because the stack grows too fast for trailing numbers). Priority:
      1. strategy.com override (env/POST, optional)
      2. 10-Q preferred table (notional × rate per series) + preferred ATM
         issuance since that quarter — reproduces the official figure
      3. XBRL dividends actually paid ×4 + ATM top-up (understates while
         the stack grows, but is real and always available)
      4. per-series model
    """
    off = get_official_metric("official_annual_dividends")
    if off:
        return {"annual_m": round(off["value_m"], 1), "source": "strategy.com",
                "asof": off.get("period_end"), "detail": None}

    model_rates = {s["ticker"]: s["rate"] for s in compute_dividend_model()["series"]}

    # --- Tier 2: 10-Q per-series notional × rate (forward obligation) ---
    pref_rows = []
    try:
        conn = get_db_connection()
        pref_rows = conn.execute(
            "SELECT metric, period_end, value FROM financial_metrics "
            "WHERE metric LIKE 'pref_%'").fetchall()
        conn.close()
    except Exception as e:
        print(f"compute_annual_dividends pref DB error: {e}")
    pref_rows = [r for r in pref_rows
                 if r["metric"].startswith(("pref_notional_", "pref_rate_"))]
    if pref_rows:
        latest_pe = max(r["period_end"] for r in pref_rows)
        notionals, rates_10q = {}, {}
        for r in pref_rows:
            if r["period_end"] != latest_pe:
                continue
            if r["metric"].startswith("pref_notional_"):
                notionals[r["metric"][len("pref_notional_"):]] = r["value"] / 1e6
            else:
                rates_10q[r["metric"][len("pref_rate_"):]] = r["value"]
        base_m = 0.0
        per_series = {}
        for t, n in notionals.items():
            rate = rates_10q.get(t) or model_rates.get(t) or 0.0
            base_m += n * rate
            per_series[t] = {"notional_m": round(n, 1), "rate": rate,
                             "annual_m": round(n * rate, 1)}
        if base_m > 0:
            added_m, added_notional_m = _preferred_atm_added_annual(
                latest_pe, {**model_rates, **rates_10q})
            return {"annual_m": round(base_m + added_m, 1), "source": "sec-10q",
                    "asof": latest_pe,
                    "detail": {"baseline_annual_m": round(base_m, 1),
                               "atm_added_annual_m": round(added_m, 1),
                               "atm_added_notional_m": round(added_notional_m, 1),
                               "series": per_series}}

    # --- Tier 3: XBRL dividends actually paid ×4 + ATM top-up ---
    latest_q = None
    try:
        conn = get_db_connection()
        latest_q = conn.execute(
            "SELECT period_end, value FROM financial_metrics "
            "WHERE metric='dividends_paid' ORDER BY period_end DESC LIMIT 1").fetchone()
        conn.close()
    except Exception as e:
        print(f"compute_annual_dividends DB error: {e}")

    if latest_q:
        base_annual_m = (latest_q["value"] / 1e6) * 4.0
        added_m, _ = _preferred_atm_added_annual(latest_q["period_end"], model_rates)
        return {"annual_m": round(base_annual_m + added_m, 1),
                "source": "xbrl_actual", "asof": latest_q["period_end"],
                "detail": {"xbrl_quarter_paid_m": round(latest_q["value"] / 1e6, 1),
                           "xbrl_annualized_m": round(base_annual_m, 1),
                           "atm_added_annual_m": round(added_m, 1)}}

    model = compute_dividend_model()
    return {"annual_m": round(model["model_monthly_total_m"] * 12.0, 1),
            "source": "model", "asof": None, "detail": None}

def compute_cash_estimate():
    """Weekly estimated cash series, backtested against reported quarters.

    Weekly flow = ATM net proceeds + BTC sale proceeds − BTC purchase cost
    − dividend burn − calibrated other outflows. The dividend burn comes
    from the latest ACTUAL quarter (XBRL) when available, else the model.
    The estimate re-anchors at every reported quarterly balance; the raw
    (uncalibrated) prediction error per past quarter is reported as the
    backtest, and its average residual becomes the "other outflows" term —
    the user's requested calibrate-against-10-K loop.
    """
    try:
        conn = get_db_connection()
        hist = conn.execute(
            "SELECT filing_date, btc_acquired, purchase_price, atm_sales "
            "FROM purchase_history ORDER BY filing_date, id").fetchall()
        # USD Reserve parsed weekly from the 8-Ks is the primary, most
        # current real cash series; XBRL quarterly cash is the fallback.
        reserve_rows = conn.execute(
            "SELECT period_end, value, form, filed FROM financial_metrics "
            "WHERE metric='usd_reserve' ORDER BY period_end").fetchall()
        cash_rows = conn.execute(
            "SELECT period_end, value, form, filed FROM financial_metrics "
            "WHERE metric='cash_and_equivalents' ORDER BY period_end").fetchall()
        conn.close()
    except Exception as e:
        print(f"compute_cash_estimate DB error: {e}")
        return None

    flows = []
    for r in hist:
        atm = _safe_json_loads(r["atm_sales"]) or {}
        # Cumulative program tables (period_scoped False) are NOT one
        # week's proceeds — never count them as cash inflow
        if atm.get("period_scoped") is False:
            atm = {}
        atm_detail = [
            {"ticker": s.get("ticker"), "net_m": round(s.get("net_proceeds_num_m") or 0.0, 1),
             "shares": s.get("shares_sold_num") or 0}
            for s in atm.get("securities", [])
            if (s.get("shares_sold_num") or 0) > 0 and (s.get("net_proceeds_num_m") or 0) > 0
            and s.get("counts") is not False
        ]
        atm_m = sum(d["net_m"] for d in atm_detail)
        btc_signed = parse_btc_number(r["btc_acquired"])
        money_m = parse_money(r["purchase_price"])
        if btc_signed > 0:
            btc_m = -money_m   # cash spent buying BTC
        elif btc_signed < 0:
            btc_m = money_m    # BTC sale proceeds
        else:
            btc_m = 0.0
        flows.append({"date": r["filing_date"], "flow_m": atm_m + btc_m,
                      "atm_m": atm_m, "btc_m": btc_m, "atm_detail": atm_detail})

    # Dividend burn = the official ANNUAL figure (strategy.com's "Annual
    # Dividends" ≈ $1.76B), derived automatically from SEC data — see
    # compute_annual_dividends for the priority chain.
    annual_div = compute_annual_dividends()
    annual_div_m = annual_div["annual_m"]
    weekly_div_m = annual_div_m / 52.0
    dividend_source = annual_div["source"]

    # Primary cash series = weekly USD Reserve parsed from the 8-Ks (real,
    # current). Fall back to XBRL quarterly cash only when no reserve exists.
    if reserve_rows:
        actuals = [{"period_end": r["period_end"], "cash_m": r["value"] / 1e6,
                    "form": "sec-8k"} for r in reserve_rows]
        cash_source = "sec-8k"
    else:
        actuals = [{"period_end": r["period_end"], "cash_m": r["value"] / 1e6,
                    "form": (r["form"] if "form" in r.keys() else "10-Q")} for r in cash_rows]
        cash_source = "xbrl"

    # Backtest the RAW model between consecutive reported quarters
    backtest = []
    residuals_per_week = []
    for a0, a1 in zip(actuals, actuals[1:]):
        seg = [f for f in flows if a0["period_end"] < f["date"] <= a1["period_end"]]
        if not seg:
            continue
        predicted = a0["cash_m"] + sum(f["flow_m"] for f in seg) - weekly_div_m * len(seg)
        error_m = predicted - a1["cash_m"]
        backtest.append({
            "quarter_end": a1["period_end"],
            "predicted_m": round(predicted, 1),
            "actual_m": round(a1["cash_m"], 1),
            "error_m": round(error_m, 1),
            "error_pct": round(error_m / a1["cash_m"] * 100, 1) if a1["cash_m"] else None,
            "weeks": len(seg),
        })
        residuals_per_week.append((a1["cash_m"] - predicted) / len(seg))

    # Calibration: the average historical residual (dividends/opex/interest
    # we can't see weekly) becomes a constant weekly outflow term
    other_per_week_m = (-sum(residuals_per_week) / len(residuals_per_week)) if residuals_per_week else 0.0

    # Walk forward weekly, tracking WHY the cash moved since the last
    # reported balance so the chart can explain its own rises and falls.
    estimate = []
    change = None
    if actuals and flows:
        anchor_idx = 0
        cash = None
        seg_since = None
        seg_from = None
        seg_form = None
        acc = {"atm_by_ticker": {}, "btc_buys_m": 0.0, "btc_sales_m": 0.0, "weeks": 0}
        for f in flows:
            while anchor_idx < len(actuals) and actuals[anchor_idx]["period_end"] < f["date"]:
                cash = actuals[anchor_idx]["cash_m"]   # re-anchor at each reported balance
                seg_since = actuals[anchor_idx]["period_end"]
                seg_from = cash
                seg_form = actuals[anchor_idx].get("form", "10-Q")
                acc = {"atm_by_ticker": {}, "btc_buys_m": 0.0, "btc_sales_m": 0.0, "weeks": 0}
                anchor_idx += 1
            if cash is None:
                continue   # no reported balance before our data window yet
            cash += f["flow_m"] - weekly_div_m - other_per_week_m
            estimate.append({
                "date": f["date"], "cash_m": round(cash, 1),
                "atm_m": round(f["atm_m"], 1), "btc_m": round(f["btc_m"], 1),
                "div_m": round(weekly_div_m, 2), "other_m": round(other_per_week_m, 2),
                "atm_detail": f["atm_detail"],
            })
            acc["weeks"] += 1
            for d in f["atm_detail"]:
                acc["atm_by_ticker"][d["ticker"]] = round(
                    acc["atm_by_ticker"].get(d["ticker"], 0.0) + d["net_m"], 1)
            if f["btc_m"] > 0:
                acc["btc_sales_m"] += f["btc_m"]
            elif f["btc_m"] < 0:
                acc["btc_buys_m"] += -f["btc_m"]

        if estimate and seg_since is not None:
            change = {
                "since": seg_since,
                "since_form": seg_form,
                "from_cash_m": round(seg_from, 1),
                "to_cash_m": estimate[-1]["cash_m"],
                "delta_m": round(estimate[-1]["cash_m"] - seg_from, 1),
                "atm_by_ticker": acc["atm_by_ticker"],
                "atm_total_m": round(sum(acc["atm_by_ticker"].values()), 1),
                "btc_buys_m": round(acc["btc_buys_m"], 1),
                "btc_sales_m": round(acc["btc_sales_m"], 1),
                "dividends_m": round(weekly_div_m * acc["weeks"], 1),
                "other_m": round(other_per_week_m * acc["weeks"], 1),
                "weeks": acc["weeks"],
            }

    # Runway: how many weeks the cash lasts if MSTR sells NO BTC and NO
    # securities (all financing inflows zeroed) — only the weekly dividend
    # burn and the calibrated other net flows remain. Prefer Strategy's
    # official published reserve (ground truth) as the basis; else the
    # latest walked estimate; else the last reported balance.
    # Prefer the most recent REAL cash datapoint (weekly USD Reserve from the
    # 8-Ks, or a strategy.com override) as the runway basis over the walked
    # estimate.
    latest_real_cash = next((a for a in reversed(actuals)
                             if a.get("form") in ("sec-8k", "strategy.com")), None)
    basis_source = None
    if latest_real_cash:
        basis_cash_m = latest_real_cash["cash_m"]
        basis_date = latest_real_cash["period_end"]
        basis_source = latest_real_cash["form"]
    elif estimate:
        basis_cash_m = estimate[-1]["cash_m"]
        basis_date = estimate[-1]["date"]
        basis_source = "estimate"
    elif actuals:
        basis_cash_m = actuals[-1]["cash_m"]
        basis_date = actuals[-1]["period_end"]
        basis_source = "actual"
    else:
        basis_cash_m = None
        basis_date = None

    net_burn_m = weekly_div_m + other_per_week_m
    runway = None
    projection = []
    if basis_cash_m is not None:
        runway = {
            "basis_cash_m": round(basis_cash_m, 1),
            "basis_date": basis_date,
            "basis_source": basis_source,
            "net_burn_per_week_m": round(net_burn_m, 2),
            "annual_dividend_m": round(annual_div_m, 1),
            "dividend_source": dividend_source,
            "weeks": None,
            "depletion_date": None,
            "infinite": net_burn_m <= 0,
        }
        if net_burn_m > 0 and basis_cash_m <= 0:
            # Estimate already at/below zero: no runway left
            runway["weeks"] = 0.0
            runway["depletion_date"] = basis_date
        if net_burn_m > 0 and basis_cash_m > 0:
            weeks = basis_cash_m / net_burn_m
            runway["weeks"] = round(weeks, 1)
            try:
                base_dt = datetime.strptime(basis_date, "%Y-%m-%d")
                runway["depletion_date"] = (base_dt + timedelta(weeks=weeks)).strftime("%Y-%m-%d")
                # Weekly linear decline for the chart (display-capped)
                display_weeks = min(int(weeks) + 1, 120)
                for w in range(1, display_weeks + 1):
                    projection.append({
                        "date": (base_dt + timedelta(weeks=w)).strftime("%Y-%m-%d"),
                        "cash_m": round(max(basis_cash_m - net_burn_m * w, 0.0), 1),
                    })
            except (ValueError, TypeError) as e:
                print(f"Runway date computation failed: {e}")

    # 10-Q calendar: when the last balance-sheet report arrived and when the
    # next one is expected (next calendar quarter end + the filer's own
    # average filing lag over recent quarters)
    filing_info = None
    # Only real SEC balance-sheet reports drive the 10-Q calendar —
    # strategy.com anchors are excluded.
    dated = [(r["period_end"], r["filed"], r["form"]) for r in cash_rows
             if r["filed"] and (r["form"] or "").startswith("10-")]
    if dated:
        lags = []
        for pe, filed, _ in dated[-4:]:
            try:
                lags.append((datetime.strptime(filed, "%Y-%m-%d")
                             - datetime.strptime(pe, "%Y-%m-%d")).days)
            except (ValueError, TypeError):
                pass
        avg_lag = round(sum(lags) / len(lags)) if lags else 40
        last_pe, last_filed, last_form = dated[-1]
        try:
            nq = _next_quarter_end(last_pe)
            filing_info = {
                "last_period_end": last_pe,
                "last_filed": last_filed,
                "last_form": last_form or "10-Q",
                "next_quarter_end": nq.strftime("%Y-%m-%d"),
                "expected_next_filed": (nq + timedelta(days=avg_lag)).strftime("%Y-%m-%d"),
                "avg_lag_days": avg_lag,
            }
        except (ValueError, TypeError) as e:
            print(f"Filing calendar computation failed: {e}")

    # Strategy's own published figures (ground truth) + how our pure model
    # compares to the latest official cash number
    official = None
    latest_official_cash = next((a for a in reversed(actuals)
                                 if a.get("form") == "strategy.com"), None)
    off_div = get_official_metric("official_annual_dividends")
    off_pref = get_official_metric("official_pref")
    off_debt = get_official_metric("official_debt")
    if latest_official_cash or off_div or off_pref or off_debt:
        official = {
            "asof": (latest_official_cash or off_div or off_pref or off_debt).get("period_end"),
            "usd_reserve_m": round(latest_official_cash["cash_m"], 1) if latest_official_cash else None,
            "annual_dividends_m": round(off_div["value_m"], 1) if off_div else None,
            "pref_m": round(off_pref["value_m"], 1) if off_pref else None,
            "debt_m": round(off_debt["value_m"], 1) if off_debt else None,
            "source": "strategy.com",
        }

    # Total preferred stock outstanding (nominal) — NOT debt (perpetual
    # equity, so it stays out of the bond figure): 10-Q per-series notional
    # + preferred ATM issuance since that quarter. strategy.com override
    # only if the automatic derivation is unavailable.
    pref_total = None
    ad_detail = annual_div.get("detail") or {}
    if ad_detail.get("series"):
        pref_total = {
            "total_m": round(sum(s["notional_m"] for s in ad_detail["series"].values())
                             + (ad_detail.get("atm_added_notional_m") or 0.0), 1),
            "asof": annual_div.get("asof"),
            "source": "sec-10q",
        }
    elif off_pref:
        pref_total = {
            "total_m": round(off_pref["value_m"], 1),
            "asof": off_pref.get("period_end"),
            "source": "strategy.com",
        }

    return {
        "estimate": estimate,
        "actuals": [{"period_end": a["period_end"], "cash_m": round(a["cash_m"], 1),
                     "form": a.get("form", "10-Q")} for a in actuals],
        "backtest": backtest,
        "calibration": {
            "weekly_dividend_m": round(weekly_div_m, 2),
            "monthly_dividend_m": round(weekly_div_m * 52.0 / 12.0, 2),
            "annual_dividend_m": round(annual_div_m, 1),
            "other_outflow_per_week_m": round(other_per_week_m, 2),
            "dividend_source": dividend_source,
            "dividend_asof": annual_div.get("asof"),
            "dividend_detail": annual_div.get("detail"),
        },
        "current_estimate": estimate[-1] if estimate else None,
        "runway": runway,
        "projection": projection,
        "change_summary": change,
        "filing_info": filing_info,
        "official": official,
        "pref_total": pref_total,
        "cash_source": cash_source,
    }

def _next_quarter_end(period_end):
    """First calendar quarter end strictly after the given date."""
    dt = datetime.strptime(period_end, "%Y-%m-%d")
    for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
        cand = datetime(dt.year, month, day)
        if cand > dt:
            return cand
    return datetime(dt.year + 1, 3, 31)

# ----------------- HISTORICAL ATM BACKFILL -----------------

ATM_SENTINEL_NO_TABLE = {"fmt": 4, "sold_any": False, "securities": [], "note": "no_atm_table"}
ATM_SENTINEL_NO_DOC = {"fmt": 4, "sold_any": False, "securities": [], "note": "no_fetchable_doc"}

RECONCILE_MAX = int(os.getenv("RECONCILE_MAX", "30"))

def reconcile_missing_history(sleep_seconds=1.5):
    """Re-parse filings that were marked processed but never recorded.

    A fresh database used to mark every 8-K in the EDGAR index as processed
    without parsing any of it, so the poller then skipped them forever as
    "not new" — and neither existing backfill could recover them, because
    both iterate purchase_history and the row was never created. Production
    froze at the seed's newest date while the page kept showing a ticking
    "Son sorgu" above it.

    mark_current_filings_processed no longer opens that hole, but this
    repairs the databases that already have it. Alerts are never sent: these
    weeks are long past, and _record_without_alert exists for exactly this.
    """
    conn = get_db_connection()
    try:
        # Only weeks after the seed's own history: the seed rows are already
        # recorded, and re-fetching them would be pointless traffic.
        floor = conn.execute(
            "SELECT MAX(filing_date) FROM purchase_history").fetchone()[0] or ""
        seed_floor = max((row[0] for row in SEED_HISTORY), default="")
        floor = min(floor, seed_floor) if floor and seed_floor else (floor or seed_floor)

        missing = conn.execute(
            "SELECT p.accession_number, p.filing_date, p.form, p.url "
            "FROM processed_filings p "
            "LEFT JOIN purchase_history h ON h.filing_date = p.filing_date "
            "WHERE h.id IS NULL AND p.filing_date > ? AND p.url <> '' "
            "ORDER BY p.filing_date",
            (floor,)).fetchall()
    finally:
        conn.close()

    if not missing:
        return 0

    print(f"Reconciling {len(missing)} filing(s) marked processed but absent "
          f"from the history: {', '.join(r['filing_date'] for r in missing[:8])}"
          f"{' …' if len(missing) > 8 else ''}")

    repaired = 0
    for row in missing[:RECONCILE_MAX]:
        try:
            _record_without_alert(row["accession_number"], row["filing_date"],
                                  row["form"] or "8-K", row["url"])
            repaired += 1
        except Exception as e:
            print(f"Reconcile of {row['filing_date']} failed: {e}")
        time.sleep(sleep_seconds)

    print(f"Reconcile complete: {repaired}/{len(missing)} week(s) recovered.")
    return repaired

def backfill_atm_history(sleep_seconds=1.5):
    """Re-read historical filings and fill missing per-security ATM data.

    Runs in a background daemon thread at startup so deploys are never
    blocked. Only rows with empty atm_sales are touched; fetch failures stay
    NULL and are retried on the next boot, while filings without an ATM
    table get a sentinel so they are never fetched again. Requests are
    spaced by sleep_seconds to respect the SEC fair-use limit.
    """
    try:
        conn = get_db_connection()
        # Also re-parse rows stored before fmt 3 (adds the period_scoped
        # guard and column-misalignment sanity checks)
        rows = conn.execute(
            "SELECT id, url, financing_source, filing_date FROM purchase_history "
            "WHERE atm_sales IS NULL OR atm_sales = '' "
            "   OR atm_sales NOT LIKE '%\"fmt\": 4%'"
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"ATM backfill: could not list rows: {e}")
        return

    if not rows:
        return

    print(f"ATM backfill: {len(rows)} historical row(s) without per-security data — starting...")
    filled = no_table = failed = 0
    for row in rows:
        url = row["url"] or ""
        atm_json = None
        financing = None

        if '/Archives/edgar/data/' not in url:
            # Placeholder/non-document URL: nothing to fetch, ever
            atm_json = json.dumps(ATM_SENTINEL_NO_DOC)
            no_table += 1
        else:
            html = fetch_html(url)
            if not html:
                failed += 1
                time.sleep(sleep_seconds)
                continue
            # Opportunistically extract the USD Reserve from the same fetch
            store_usd_reserve(row["filing_date"], parse_usd_reserve(clean_html(html)))
            atm = parse_atm_table(extract_filing_tables(html))
            if atm:
                atm_json = json.dumps(atm, ensure_ascii=False)
                filled += 1
                # Fill the badge only when the row has no description yet —
                # existing Turkish notes (e.g. convertible debt) carry info
                # the ATM table doesn't and must be preserved.
                if ((row["financing_source"] or "-").strip() in ("-", "")
                        and atm.get("sold_any") and atm.get("period_scoped", True)):
                    financing = financing_source_from_atm(atm)
            else:
                atm_json = json.dumps(ATM_SENTINEL_NO_TABLE)
                no_table += 1
            time.sleep(sleep_seconds)

        try:
            conn = get_db_connection()
            if financing:
                conn.execute(
                    "UPDATE purchase_history SET atm_sales = ?, financing_source = ? WHERE id = ?",
                    (atm_json, financing, row["id"])
                )
            else:
                conn.execute(
                    "UPDATE purchase_history SET atm_sales = ? WHERE id = ?",
                    (atm_json, row["id"])
                )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ATM backfill: DB update failed for row {row['id']}: {e}")

    print(f"ATM backfill done: {filled} filled, {no_table} without ATM data, {failed} fetch failure(s)"
          + (" — failures retry on next boot" if failed else ""))

def backfill_usd_reserves(sleep_seconds=1.5):
    """Build the weekly USD Reserve series from historical filings.

    Fetches each real 8-K whose date has no usd_reserve datapoint yet and
    extracts the disclosed reserve. Runs once per new filing; a filing with
    no reserve statement gets a sentinel row so it isn't re-fetched forever.
    """
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT DISTINCT filing_date, url FROM purchase_history "
            "WHERE url LIKE '%/Archives/edgar/data/%' "
            "AND filing_date NOT IN (SELECT period_end FROM financial_metrics WHERE metric='usd_reserve') "
            "AND filing_date NOT IN (SELECT period_end FROM financial_metrics WHERE metric='usd_reserve_none') "
            "ORDER BY filing_date DESC").fetchall()
        conn.close()
    except Exception as e:
        print(f"USD reserve backfill: could not list rows: {e}")
        return
    if not rows:
        return
    print(f"USD reserve backfill: {len(rows)} filing(s) to scan...")
    found = 0
    for row in rows:
        html = fetch_html(row["url"])
        if html:
            val_m = parse_usd_reserve(clean_html(html))
            if val_m is not None:
                store_usd_reserve(row["filing_date"], val_m)
                found += 1
            else:
                # Mark as scanned-but-absent so we don't re-fetch endlessly
                try:
                    conn = get_db_connection()
                    conn.execute(
                        "INSERT OR REPLACE INTO financial_metrics (metric, period_end, value, form, filed) "
                        "VALUES ('usd_reserve_none', ?, 0, 'sec-8k', ?)",
                        (row["filing_date"], row["filing_date"]))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
        time.sleep(sleep_seconds)
    print(f"USD reserve backfill done: {found} reserve figure(s) extracted.")

# ----------------- GROQ API INTEGRATION -----------------

# Groq API Keys Rotation Support
groq_keys = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
current_key_idx = 0

# Groq retired llama-3.1-8b-instant in August 2026. A decommissioned model
# id answers 400, which this code treated like any other error: rotate the
# key and retry, then give up silently — so the AI follow-up message simply
# stopped being delivered, with nothing in the alert to show it. Keep the id
# in config so the next deprecation is an env change, not a redeploy.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

def get_groq_client():
    global current_key_idx
    if not groq_keys:
        return None
    return groq_keys[current_key_idx % len(groq_keys)]

def rotate_groq_key():
    global current_key_idx
    if len(groq_keys) > 1:
        current_key_idx = (current_key_idx + 1) % len(groq_keys)
        print(f"Rotated to next Groq API key (index: {current_key_idx % len(groq_keys)})")

def analyze_filing_with_groq(text, url):
    if not groq_keys:
        print("Groq API Key is not configured.")
        return None
        
    truncated_text = text[:15000]
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT total_debt, financing_source FROM purchase_history ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        conn.close()
        last_debt = last_row["total_debt"] if last_row else "$6.7B"
        last_source = last_row["financing_source"] if last_row else "ATM Hisse Satışı"
    except Exception:
        last_debt = "$6.7B"
        last_source = "ATM Hisse Satışı"
    
    prompt = f"""You are an expert financial analyst. Analyze the following SEC Form 8-K filing from MicroStrategy (Strategy Inc.).
Extract the Bitcoin purchase or sale details, financing details (ATM share sales, convertible debt, STRC/STRF preferred stock issuance), or corporate updates.

Return a JSON object with the following fields:
- "event_type": "btc_purchase", "no_purchase" (explicitly stated they didn't buy), "btc_sale", "financing" (raised cash, didn't buy BTC), or "corporate_update" (routine, meetings, dividends)
- "purchase_period": (string, e.g., "June 15, 2026 to June 21, 2026" or null)
- "btc_acquired": (string/integer, number of BTC bought/sold, e.g., "520", or null)
- "purchase_price_usd": (string, total transaction amount, e.g., "$34.9M" or "$2.01B", or null)
- "avg_purchase_price": (string, average price per BTC, e.g., "$67,068", or null)
- "total_btc_holdings": (string, total cumulative BTC holdings after this filing, e.g., "847,363", or null)
- "total_cost_usd": (string, cumulative cost of all BTC, e.g., "$64.10B", or null)
- "avg_cost_per_btc": (string, cumulative average cost per BTC, e.g., "$75,651", or null)
- "total_debt_usd": (string, total outstanding convertible debt principal in billions of USD, e.g., "$6.7B". Note: If no new convertible debt offering is announced in this filing, keep it at the previous value: "{last_debt}")
- "financing_details": (string, details of cash raised, notes issued, ATM sales, STRC/STRF preferred stock pricing/issuance, or null)
- "financing_source_turkish": (string, brief summary of financing source in Turkish, e.g. "ATM Hisse Satışı", "Konvertibl Tahvil İhracı", "STRC/STRF Tercihli Hisse İhracı", or combining them if multiple. If not mentioned and no purchase occurred, write "-". Keep it short for a table badge)
- "summary_turkish": (string, 2-3 sentences in Turkish summarizing the event/corporate action)

Filing URL: {url}

Filing text:
{truncated_text}

You must return ONLY the raw JSON object. Do not include markdown code block markers or any preamble.
"""

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    # Rotation attempt loop
    for attempt in range(len(groq_keys)):
        api_key = get_groq_client()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            print(f"Trying Groq API with key index {current_key_idx % len(groq_keys)}...")
            response = http_session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                return json.loads(content)
            elif response.status_code == 429:
                print(f"Groq API key at index {current_key_idx % len(groq_keys)} rate limited (429). Rotating key...")
                rotate_groq_key()
            else:
                print(f"Groq API error status {response.status_code}: {response.text}. Rotating key...")
                rotate_groq_key()
        except Exception as e:
            print(f"Groq API exception with key index {current_key_idx % len(groq_keys)}: {e}. Rotating key...")
            rotate_groq_key()
            
    print("All available Groq API keys failed or were rate limited.")
    return None

def groq_api_call(prompt, temperature=0.1, max_retries=None):
    """Low-level Groq API call with key rotation. Returns parsed JSON or None."""
    if not groq_keys:
        return None
    retries = max_retries or len(groq_keys)
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": temperature
    }
    for attempt in range(retries):
        api_key = get_groq_client()
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            response = http_session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                return json.loads(response.json()['choices'][0]['message']['content'].strip())
            elif response.status_code == 429:
                print(f"Groq key {current_key_idx % len(groq_keys)} rate limited. Rotating...")
                rotate_groq_key()
                time.sleep(2)
            elif response.status_code == 400:
                # Almost always a bad/retired model id. Rotating keys cannot
                # fix it, so say what is wrong instead of failing quietly.
                print(f"Groq rejected the request (400) for model {GROQ_MODEL!r}: "
                      f"{response.text[:300]} — set GROQ_MODEL to a current model.")
                return None
            else:
                print(f"Groq error {response.status_code}: {response.text[:200]}. Rotating...")
                rotate_groq_key()
        except Exception as e:
            print(f"Groq exception: {e}. Rotating...")
            rotate_groq_key()
    return None

def analyze_filing_deep_groq(text, url, table_data=None):
    """Multi-pass Groq analysis for high-quality Turkish summary.
    
    Pass 1: Extract key facts and data points from the filing
    Pass 2: Generate a rich Turkish analysis using the extracted facts + table data
    Pass 3 (optional): Refine and add market context
    """
    if not groq_keys:
        return None
    
    truncated_text = text[:15000]
    
    # --- PASS 1: Extract key facts ---
    print("Deep analysis Pass 1: Extracting key facts...")
    pass1_prompt = f"""You are a financial analyst. Read this SEC Form 8-K filing from Strategy Inc. (formerly MicroStrategy).
Extract ALL key facts as a JSON object:
- "btc_activity": Describe ALL bitcoin purchase or sale activities mentioned (there may be multiple periods)
- "share_repurchase": Any share repurchase program updates
- "preferred_stock": Any STRC/STRF preferred stock updates (dividends, distributions, issuance)
- "financing": Any new debt, ATM share sales, convertible notes
- "other_events": Any other material events
- "key_numbers": List of ALL important numbers mentioned (BTC counts, dollar amounts, prices, holdings)
- "proceeds_usage": How were any sale proceeds used?

Filing text:
{truncated_text}

Return ONLY the raw JSON object."""

    pass1_result = groq_api_call(pass1_prompt, temperature=0.05)
    if not pass1_result:
        print("Deep analysis Pass 1 failed.")
        return None
    
    # --- PASS 2: Generate rich Turkish analysis ---
    print("Deep analysis Pass 2: Generating Turkish analysis...")
    
    # Include table_data context if available
    table_context = ""
    if table_data:
        event = table_data.get("event_type", "unknown")
        btc = table_data.get("btc_signed_str") or table_data.get("btc_acquired", "-")
        price = table_data.get("purchase_price", "-")
        avg = table_data.get("avg_price", "-")
        holdings = table_data.get("total_holdings", "-")
        breakdown = (table_data.get("sale_breakdown")
                     or table_data.get("purchase_breakdown")
                     or table_data.get("mixed_breakdown") or [])

        table_context = f"""
Parsed table data (authoritative — from the filing's own tables):
- Event type: {event}
- Net BTC change during the period: {btc}
- Total amount: {price}
- Weighted avg price: {avg}
- Current holdings: {holdings} BTC
"""
        if table_data.get("inferred"):
            table_context += "- NOTE: the amount was INFERRED from the holdings delta (no activity table in the filing) — present it as an estimate.\n"
        if breakdown:
            table_context += "Period breakdown:\n"
            for b in breakdown:
                table_context += f"  - {b['period']}: {b['btc_count']} BTC @ {b['avg_price']} (total: {b['price']})\n"

        atm = table_data.get("atm")
        if atm:
            table_context += "ATM offering activity this period (per security):\n"
            g_sold, g_flagged, g_unsold = partition_atm_securities(atm)
            for s in g_sold:
                table_context += (f"  - {s['ticker']}: {s.get('shares_sold', '-')} shares sold, "
                                  f"net proceeds {s.get('net_proceeds', '-')}, "
                                  f"remaining capacity {s.get('available', '-')}\n")
            for s in g_flagged:
                table_context += (f"  - {s['ticker']}: shares sold but the figures failed a "
                                  f"sanity check — do not quote them\n")
            for s in g_unsold:
                table_context += f"  - {s['ticker']}: no shares sold (remaining capacity {s.get('available', '-')})\n"
            table_context += f"  Total net proceeds: {atm.get('total_net_proceeds', '-')}\n"

        if table_data.get("usd_reserve_m") is not None:
            table_context += (f"USD Reserve (cash) disclosed in this filing: "
                              f"{_fmt_musd(table_data['usd_reserve_m'])}")
            if table_data.get("reserve_change_m"):
                chg = table_data["reserve_change_m"]
                table_context += f" ({'+' if chg > 0 else ''}{_fmt_musd(chg)} vs previous week)"
            if table_data.get("runway_months") is not None and table_data.get("annual_div_m"):
                table_context += (f" — covers ~{table_data['runway_months']:.0f} months of the "
                                  f"official annual dividend obligation "
                                  f"(~{_fmt_musd(table_data['annual_div_m'])}/yr). "
                                  f"Comment on this coverage in the analysis.")
            table_context += "\n"

    pass2_prompt = f"""Sen bir uzman finans analistsin. Aşağıdaki verileri kullanarak MicroStrategy (Strategy Inc.) hakkında kapsamlı bir Türkçe analiz yaz.

Çıkarılan veriler (Pass 1):
{json.dumps(pass1_result, indent=2, ensure_ascii=False)}
{table_context}

SEC Bildirimi URL: {url}

Şu JSON formatında yanıt ver:
- "summary_turkish": (string) 4-6 cümlelik detaylı Türkçe analiz. Şunları içermeli:
  1. Ne oldu? (BTC alım/satım/değişiklik yok) - Eğer birden fazla dönem varsa HEPSİNİ belirt
  2. Neden oldu? (Temettü ödemesi, fon oluşturma, tercihli hisse dağıtımı vs.) - Eğer BTC alınmadıysa ama ATM hisse satışı varsa bunu mutlaka vurgula (örn: "BTC almadı; MSTR hissesi satarak $466.7M nakit topladı"). Alım ATM satışıyla finanse edildiyse hangi menkul kıymetle olduğunu belirt (örn: "STRC satışıyla finanse edilen alım")
  3. Portföy etkisi (toplam BTC, maliyet değişimi)
  4. Yatırımcı için ne anlama geliyor?
- "market_impact": (string) 1-2 cümle, bu haberin piyasaya potansiyel etkisi
- "risk_note": (string) 1 cümle, dikkat edilmesi gereken risk veya önemli not

ÖNEMLİ: "Parsed table data" bölümündeki rakamlar filing tablolarından doğrudan alınmıştır ve KESİNDİR — bu rakamlarla çelişme. Event type "no_purchase" ise BTC satıldı/alındı DEME.
Sadece ham JSON döndür, markdown veya açıklama ekleme."""

    pass2_result = groq_api_call(pass2_prompt, temperature=0.3)
    if not pass2_result:
        print("Deep analysis Pass 2 failed.")
        # Fallback: use pass1 data to build a basic summary
        return {"summary_turkish": str(pass1_result.get("btc_activity", "Analiz tamamlanamadı."))}
    
    # --- PASS 3: Refine with market context (optional, best-effort) ---
    print("Deep analysis Pass 3: Refining analysis...")
    pass3_prompt = f"""Sen bir finans editörüsün. Aşağıdaki analizi gözden geçir ve iyileştir.
Gereksiz tekrarları kaldır, dili akıcı ve profesyonel yap. Maksimum 5-6 cümle olsun.

Mevcut analiz:
{pass2_result.get('summary_turkish', '')}

Piyasa etkisi: {pass2_result.get('market_impact', '')}
Risk notu: {pass2_result.get('risk_note', '')}

JSON olarak döndür:
- "summary_turkish": (string) İyileştirilmiş ve birleştirilmiş nihai Türkçe analiz metni (piyasa etkisi ve risk notunu da içersin, tek paragraf halinde akıcı şekilde). Metin kısa ve öz olmalı ama tüm kritik bilgileri kapsamalı.

Sadece ham JSON döndür."""

    pass3_result = groq_api_call(pass3_prompt, temperature=0.2)
    if pass3_result and pass3_result.get("summary_turkish"):
        print("Deep analysis Pass 3 succeeded — using refined summary.")
        return pass3_result
    else:
        print("Deep analysis Pass 3 failed — using Pass 2 result.")
        return pass2_result

# ----------------- POLYMARKET INSIDER DIGEST -----------------
# Tracks a handful of Polymarket wallets and posts what CHANGED since the
# last digest. The mechanism is a snapshot diff of /positions rather than a
# replay of /activity: it needs five fields understood correctly instead of a
# dozen, it self-heals after a failed day (the next diff runs against the last
# SUCCESSFUL snapshot, so a movement is reported late rather than lost), and
# many small fills collapse into one net move instead of a wall of rows.

# Case-insensitive on the 0x prefix too: a pasted "0XABC…" is the same
# wallet, and dropping it silently for the sake of one character would be a
# poor way to learn the list was misconfigured.
_ADDR_RE = re.compile(r'0[xX][0-9a-fA-F]{40}\b')
_polymarket_shape_logged = False
_pm_failure_streak = 0

def parse_insider_addresses(raw):
    """Extract (address, label) pairs from POLYMARKET_INSIDERS.

    Accepts, comma- or newline-separated and freely mixed:
        0xa0c37cb0587b0dd1542f794bcfa345762bba5b9a
        Balina=0xa0c3...
        https://polymarket.com/profile/0xa0c3...?via=betmoar

    The address is located by regex FIRST and the label taken from whatever
    precedes it, and only when that prefix is not itself a URL. The ordering
    matters: a pasted profile link ends in "?via=betmoar", so splitting on
    "=" to find a label would name the wallet "betmoar" — or worse, take the
    URL as the address.

    Addresses are lowercased. A checksummed address and its lowercase form
    are the same wallet, and storing both would create two snapshot rows that
    diff against each other forever.
    """
    out, seen = [], set()
    for token in re.split(r'[,\n;]+', raw or ''):
        token = token.strip()
        if not token:
            continue
        m = _ADDR_RE.search(token)
        if not m:
            print(f"POLYMARKET_INSIDERS: ignoring {token[:60]!r} — no 0x address in it.")
            continue
        addr = m.group(0).lower()
        # "Balina=https://polymarket.com/profile/0x…" — the label is the part
        # before the first '=', so a named wallet keeps its name even when the
        # value is a pasted URL. Anything that still looks like a URL is not a
        # name.
        candidate = token[:m.start()].split('=', 1)[0].strip()
        label = candidate if candidate and '/' not in candidate and ':' not in candidate else ''
        if addr in seen:
            continue
        seen.add(addr)
        out.append((addr, label or f"{addr[:6]}…{addr[-4:]}"))
        if len(out) >= POLYMARKET_MAX_INSIDERS:
            break
    return out

INSIDER_WALLETS = parse_insider_addresses(POLYMARKET_INSIDERS_RAW)
POLYMARKET_ENABLED = bool(INSIDER_WALLETS)

def _pm_num(row, *names, default=0.0):
    """First present key as a float, tolerating numeric strings."""
    for n in names:
        v = row.get(n)
        if v is None or v == '':
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return default

def _pm_str(row, *names, default=""):
    for n in names:
        v = row.get(n)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if v not in (None, ''):
            return str(v)
    return default

def _as_rows(payload):
    """Coerce a decoded response into a list of dicts, defensively.

    The docs imply a bare array, but other Polymarket surfaces wrap the list
    in an object, and this could not be verified against a live response. A
    shape we do not recognise must degrade to "no data", never to an
    exception on a background thread.
    """
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "positions", "results", "items"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return [r for r in inner if isinstance(r, dict)]
    return []

def _normalise_position(row):
    """One /positions entry reduced to the fields the diff needs."""
    return {
        "condition_id": _pm_str(row, "conditionId", "condition_id"),
        "asset": _pm_str(row, "asset", "tokenId", "asset_id"),
        "outcome": _pm_str(row, "outcome", default="?"),
        "title": _pm_str(row, "title", default="(başlıksız market)"),
        "event_slug": _pm_str(row, "eventSlug", "event_slug"),
        "size": _pm_num(row, "size", "tokens"),
        "avg_price": _pm_num(row, "avgPrice", "avg_price"),
        "cur_price": _pm_num(row, "curPrice", "cur_price"),
        "redeemable": 1 if row.get("redeemable") else 0,
        "end_date": _pm_str(row, "endDate", "end_date"),
    }

def _pm_get(path, params, deadline):
    """GET a data-api path within the run's wall-clock budget.

    Returns a Response or None. Not wired into _sec_backoff: that machinery
    assumes a source polled several times a second, and an exponential
    backoff measured in minutes is meaningless for a job that runs once a
    day.
    """
    if time.time() >= deadline:
        return None
    try:
        return polymarket_session.get(
            f"{POLYMARKET_DATA_API}{path}", params=params,
            timeout=(POLYMARKET_CONNECT_TIMEOUT, POLYMARKET_READ_TIMEOUT))
    except requests.exceptions.ConnectionError:
        if time.time() >= deadline:
            return None
        try:
            return polymarket_session.get(
                f"{POLYMARKET_DATA_API}{path}", params=params,
                timeout=(POLYMARKET_CONNECT_TIMEOUT, POLYMARKET_READ_TIMEOUT))
        except Exception:
            return None
    except Exception:
        return None

def fetch_polymarket_positions(address, deadline):
    """One wallet's open positions, normalised.

    Returns (rows, truncated), or (None, False) on ANY failure — non-200,
    timeout, unparseable body.

    None and [] mean different things and the caller depends on it: [] is
    "this wallet genuinely holds nothing", None is "we do not know". A 200
    with an empty array is also what a well-formed but wrong address returns,
    which is why the guard for that lives in the diff, not here.

    sortBy=CURRENT descending so that if the page cap is hit, what survives
    is the largest positions. sizeThreshold is passed explicitly because the
    documented default of 1.0 hides dust — and a position drifting across
    that line would otherwise flap between "opened" and "closed" daily.
    """
    global _polymarket_shape_logged
    rows, truncated = [], False
    for page in range(max(1, POLYMARKET_MAX_PAGES)):
        resp = _pm_get("/positions", {
            "user": address,
            "limit": POLYMARKET_PAGE_LIMIT,
            "offset": page * POLYMARKET_PAGE_LIMIT,
            "sizeThreshold": 0,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        }, deadline)
        if resp is None:
            _record_source('polymarket', False, "connection/timeout")
            if _should_log_source_error('polymarket'):
                print(f"Polymarket fetch failed for {address} (connection/timeout).")
            return None, False
        if resp.status_code != 200:
            _record_source('polymarket', False, f"HTTP {resp.status_code}")
            if _should_log_source_error('polymarket'):
                # Datacenter egress draws bot challenges on this host; a 403
                # with an HTML body is the expected shape of that, not JSON.
                print(f"Polymarket returned {resp.status_code} for {address}: "
                      f"{resp.text[:200]!r}")
            return None, False
        try:
            page_rows = _as_rows(resp.json())
        except Exception as e:
            _record_source('polymarket', False, e)
            if _should_log_source_error('polymarket'):
                print(f"Polymarket response was not JSON for {address}: {resp.text[:200]!r}")
            return None, False

        _record_source('polymarket', True)
        if page_rows and not _polymarket_shape_logged:
            _polymarket_shape_logged = True
            first = page_rows[0]
            print(f"POLYMARKET /positions first-response shape (one-time log): "
                  f"{json.dumps(first)[:600]}")
            # If the profile address is not what ?user= keys on, this line is
            # where the mismatch becomes visible.
            print(f"POLYMARKET requested user={address} proxyWallet="
                  f"{first.get('proxyWallet')!r}")

        rows.extend(_normalise_position(r) for r in page_rows)
        if len(page_rows) < POLYMARKET_PAGE_LIMIT:
            break
        if page + 1 == POLYMARKET_MAX_PAGES:
            truncated = True
    return rows, truncated

def load_position_snapshot(conn, address):
    """{(condition_id, asset): row} for one wallet."""
    cur = conn.execute(
        "SELECT condition_id, asset, outcome, title, event_slug, size, "
        "avg_price, cur_price, redeemable, end_date "
        "FROM polymarket_positions WHERE address = ?", (address,))
    return {(r["condition_id"], r["asset"]): dict(r) for r in cur.fetchall()}

def _position_resolved(row):
    """Did this market resolve, rather than the wallet trading out of it?

    A resolved market's position simply vanishes from the next snapshot.
    Reporting that as "closed" is the largest single source of false
    movements in a snapshot diff, so it is suppressed by default.
    """
    if row.get("redeemable"):
        return True
    end = (row.get("end_date") or "")[:10]
    if len(end) == 10:
        try:
            return datetime.strptime(end, "%Y-%m-%d").date() < now_trt().date()
        except ValueError:
            return False
    return False

def diff_positions(prev, cur, truncated=False):
    """Classify what moved between two snapshots of one wallet.

    kind is opened / closed / increased / decreased. Three filters keep noise
    out: a USD floor, a percentage floor on resizes, and the resolved-market
    suppression above. When the fetch was truncated, closes are dropped
    entirely for that wallet — a position missing from a capped page set has
    not been closed, we just did not look far enough.
    """
    moves = []
    for key, new in cur.items():
        old = prev.get(key)
        prev_size = float(old["size"]) if old else 0.0
        new_size = float(new["size"])
        delta = new_size - prev_size
        if abs(delta) < 1e-9:
            continue
        price = new.get("avg_price") or new.get("cur_price") or 0.0
        usd = abs(delta) * price
        if usd < POLYMARKET_MIN_USD:
            continue
        if old and prev_size > 0:
            pct = abs(delta) / prev_size * 100.0
            if pct < POLYMARKET_MIN_DELTA_PCT:
                continue
        else:
            pct = 100.0
        moves.append({
            "kind": "opened" if not old or prev_size <= 0 else
                    ("increased" if delta > 0 else "decreased"),
            "title": new["title"], "outcome": new["outcome"],
            "event_slug": new.get("event_slug", ""),
            "delta": delta, "new_size": new_size, "prev_size": prev_size,
            "usd": usd, "pct": pct, "price": price,
        })

    if not truncated:
        for key, old in prev.items():
            if key in cur:
                continue
            prev_size = float(old["size"] or 0)
            if prev_size <= 0:
                continue
            if _position_resolved(old) and not POLYMARKET_REPORT_RESOLVED:
                continue
            price = old.get("avg_price") or old.get("cur_price") or 0.0
            usd = prev_size * price
            if usd < POLYMARKET_MIN_USD:
                continue
            moves.append({
                "kind": "closed", "title": old["title"], "outcome": old["outcome"],
                "event_slug": old.get("event_slug", ""),
                "delta": -prev_size, "new_size": 0.0, "prev_size": prev_size,
                "usd": usd, "pct": 100.0, "price": price,
            })

    moves.sort(key=lambda m: m["usd"], reverse=True)
    return moves

def store_position_snapshot(conn, address, rows):
    """Replace one wallet's snapshot. Called only after a successful send."""
    conn.execute("DELETE FROM polymarket_positions WHERE address = ?", (address,))
    conn.executemany(
        "INSERT OR REPLACE INTO polymarket_positions "
        "(address, condition_id, asset, outcome, title, event_slug, size, "
        " avg_price, cur_price, redeemable, end_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(address, r["condition_id"], r["asset"], r["outcome"], r["title"],
          r["event_slug"], r["size"], r["avg_price"], r["cur_price"],
          r["redeemable"], r["end_date"]) for r in rows])

# ----------------- POLYMARKET DIGEST RENDERING -----------------

TELEGRAM_TEXT_LIMIT = 4096

def _tg_len(text):
    """Telegram counts UTF-16 code units, not Python characters.

    Every emoji is two units while len() reports one, so a Python-len budget
    undercounts an emoji-led digest badly enough to sail past 4096 and have
    the whole message rejected.
    """
    return len(text.encode('utf-16-le')) // 2

def _md_strip(text):
    """Neutralise legacy-Markdown metacharacters in untrusted text.

    Market titles are written by third parties and routinely contain * _ ` [
    ]. send_telegram_alert hardcodes parse_mode='Markdown', so a single
    unbalanced * in one title makes Telegram reject the ENTIRE digest and
    drop it to the plain-text fallback, losing every bold in it. Titles are
    the only untrusted input here, so strip rather than escape — legacy
    Markdown escaping is unreliable, and moving the shared sender to
    MarkdownV2 would touch the latency-critical alert path.
    """
    return re.sub(r'[*_`\[\]]', '', text or '')

def _short_title(title):
    clean = _md_strip(title).strip()
    if len(clean) <= POLYMARKET_TITLE_MAX:
        return clean
    return clean[:POLYMARKET_TITLE_MAX - 1].rstrip() + "…"

def _tr_num(x):
    """Turkish thousands separator: 15400 -> '15.400'."""
    return f"{int(round(x)):,}".replace(",", ".")

def _usd(x):
    return f"${x:,.0f}" if abs(x) >= 1 else f"${x:.2f}"

_KIND_STYLE = {
    "opened":    ("🟢", "YENİ"),
    "increased": ("🔼", "ARTIRDI"),
    "decreased": ("🔽", "AZALTTI"),
    "closed":    ("⚪️", "KAPANDI"),
}

def format_movement(m):
    emoji, word = _KIND_STYLE.get(m["kind"], ("•", m["kind"].upper()))
    head = f"{emoji} {word}: {_short_title(m['title'])} — {_md_strip(m['outcome'])}"
    if m["kind"] == "opened":
        detail = f"{_tr_num(m['new_size'])} adet @ ${m['price']:.2f} → **{_usd(m['usd'])}**"
    elif m["kind"] == "closed":
        detail = f"{_tr_num(m['prev_size'])} adet · **{_usd(m['usd'])}**"
    else:
        sign = "+" if m["delta"] > 0 else "−"
        detail = (f"{sign}{_tr_num(abs(m['delta']))} adet (%{m['pct']:.0f}) → "
                  f"toplam {_tr_num(m['new_size'])} · **{_usd(m['usd'])}**")
    return f"{head}\n   {detail}"

def format_wallet_block(label, address, moves, seeded=None):
    short = f"{address[:6]}…{address[-4:]}"
    clean = _md_strip(label)
    # An unnamed wallet is labelled with its own short address; printing that
    # twice on one line reads like a mistake.
    head = f"🐋 **{clean}**" if clean == short else f"🐋 **{clean}** (`{short}`)"
    if seeded is not None:
        return f"{head}\n📌 Takibe alındı: {seeded} açık pozisyon"
    shown = moves[:POLYMARKET_MAX_MOVES_PER_ADDR]
    body = "\n".join(format_movement(m) for m in shown)
    if len(moves) > len(shown):
        body += f"\n   ↳ +{len(moves) - len(shown)} hareket daha"
    return f"{head}\n{body}"

def split_telegram_blocks(header, blocks, footer, limit=None):
    """Pack pre-rendered blocks into messages that fit Telegram's limit.

    A block is never split internally — that is what guarantees a Markdown
    entity cannot be cut in half, which would have Telegram reject the part.
    The header repeats on every part with a counter; the footer lands on the
    last one only. A single oversized block is truncated rather than dropped:
    a clipped movement beats a silently missing one.
    """
    limit = limit or POLYMARKET_MSG_LIMIT
    limit = min(limit, TELEGRAM_TEXT_LIMIT - 64)
    room = limit - _tg_len(header) - 8          # 8 ≈ the " (2/3)" counter
    packed, current = [], []
    for block in blocks:
        if _tg_len(block) > room:
            block = block[:max(0, room - 1)].rstrip() + "…"
        if current and _tg_len("\n\n".join(current + [block])) > room:
            packed.append(current)
            current = []
        current.append(block)
    if current:
        packed.append(current)
    if not packed:
        packed = [[]]

    parts, total = [], len(packed)
    for i, group in enumerate(packed, 1):
        head = header if total == 1 else f"{header} ({i}/{total})"
        body = "\n\n".join(group)
        text = f"{head}\n\n{body}" if body else head
        if i == total and footer:
            text += f"\n\n{footer}"
        parts.append(text)
    return parts

def format_polymarket_digest(result):
    """Render the digest parts from a build_polymarket_digest() result."""
    header = (f"🎯 **İçeriden Takip — Polymarket**\n"
              f"📅 {now_trt().strftime('%d.%m.%Y')} · son özetten bu yana")
    blocks = []
    for entry in result["wallets"]:
        blocks.append(format_wallet_block(
            entry["label"], entry["address"], entry["moves"],
            seeded=entry.get("seeded")))

    bits = [f"📊 {result['movements']} hareket · {result['addresses_ok']} cüzdan"]
    for err in result["errors"]:
        bits.append(f"⚠️ {err}")
    footer = "\n".join(bits)
    return split_telegram_blocks(header, blocks, footer)

def send_telegram_digest(parts):
    """Send the parts in order, threading them under the first.

    A delay between parts because Telegram's per-chat ceiling is roughly 20
    messages a minute and _telegram_post does not handle a 429.
    """
    sent, first_id = [], None
    for i, text in enumerate(parts):
        msg_id = send_telegram_alert(text, reply_to_message_id=first_id)
        if msg_id is None:
            print(f"Polymarket digest part {i+1}/{len(parts)} failed to send.")
            break
        sent.append(msg_id)
        if first_id is None:
            first_id = msg_id
        if i + 1 < len(parts):
            time.sleep(POLYMARKET_PART_DELAY_S)
    return sent

# ----------------- POLYMARKET DIGEST ORCHESTRATION -----------------

def build_polymarket_digest():
    """Fetch, diff and render. Writes nothing, sends nothing.

    The pending snapshots are deliberately returned rather than stored — see
    run_polymarket_digest for why the commit must follow the send.
    """
    deadline = time.time() + POLYMARKET_BUDGET_S
    conn = get_db_connection()
    wallets, errors, pending = [], [], {}
    movements = addresses_ok = 0
    try:
        for address, label in INSIDER_WALLETS:
            rows, truncated = fetch_polymarket_positions(address, deadline)
            if rows is None:
                errors.append(f"{label}: veri alınamadı")
                continue
            addresses_ok += 1
            prev = load_position_snapshot(conn, address)
            cur = {(r["condition_id"], r["asset"]): r for r in rows}

            # HTTP 200 with an empty list is exactly what a well-formed but
            # wrong address returns, and what some edge failures return. A
            # wallet we have positions for coming back empty is a fetch
            # problem, not a liquidation: skip it and keep the old snapshot.
            if prev and not cur:
                errors.append(f"{label}: boş cevap, atlandı")
                continue

            pending[address] = rows
            if not prev:
                # First sight of this wallet: every position would look
                # "opened". Record it and say so in one line.
                wallets.append({"address": address, "label": label,
                                "moves": [], "seeded": len(rows)})
                continue
            moves = diff_positions(prev, cur, truncated=truncated)
            if truncated:
                errors.append(f"{label}: pozisyon listesi kırpıldı")
            if moves:
                movements += len(moves)
                wallets.append({"address": address, "label": label, "moves": moves})
    finally:
        conn.close()

    result = {"wallets": wallets, "movements": movements,
              "addresses_ok": addresses_ok, "errors": errors,
              "pending": pending}
    result["parts"] = format_polymarket_digest(result) if wallets else []
    return result

def _digest_status(conn, day):
    row = conn.execute("SELECT status FROM polymarket_digests WHERE digest_date = ?",
                       (day,)).fetchone()
    return row["status"] if row else None

def run_polymarket_digest(force=False, dry_run=False):
    """Fetch, render, send, and only then commit.

    Deliberately the inverse of refresh_cash_reserves, which writes first.
    If the snapshot were stored before the send and the process died in
    between, the next run would diff new-against-new, see nothing, and the
    day's movements would be gone for good. Sending first means the worst
    case is a repeated digest, not a lost one.

    dry_run renders and returns the text without posting or committing — the
    only way to check the response shape against production without spending
    the day's diff or posting to the channel.
    """
    global _pm_failure_streak
    if not POLYMARKET_ENABLED:
        return {"status": "disabled", "parts": []}

    day = now_trt().strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        if not force and not dry_run and _digest_status(conn, day):
            return {"status": "already_posted", "parts": []}
    finally:
        conn.close()

    result = build_polymarket_digest()

    if result["addresses_ok"] == 0 and INSIDER_WALLETS:
        # A digest made entirely of error lines is noise; stay quiet, but do
        # not stay quiet forever.
        _pm_failure_streak += 1
        print(f"Polymarket digest: every wallet failed "
              f"({_pm_failure_streak} day(s) in a row).")
        if not dry_run:
            conn = get_db_connection()
            conn.execute("INSERT OR REPLACE INTO polymarket_digests "
                         "(digest_date, posted_at, status, movements, addresses, note) "
                         "VALUES (?, CURRENT_TIMESTAMP, 'failed', 0, 0, ?)",
                         (day, "; ".join(result["errors"])[:400]))
            conn.commit()
            conn.close()
            if _pm_failure_streak >= 3:
                send_telegram_alert(
                    f"⚠️ **Polymarket takibi {_pm_failure_streak} gündür veri alamıyor.**\n"
                    f"{'; '.join(result['errors'])[:300]}")
                _pm_failure_streak = 0
        return {"status": "failed", "parts": [], "errors": result["errors"]}

    _pm_failure_streak = 0
    if dry_run:
        return {"status": "dry", "parts": result["parts"],
                "movements": result["movements"], "errors": result["errors"]}

    if not result["parts"]:
        # Nothing moved. Still record the day so a restart does not re-fetch,
        # and still commit the snapshot so tomorrow diffs against today.
        conn = get_db_connection()
        for address, rows in result["pending"].items():
            store_position_snapshot(conn, address, rows)
        conn.execute("INSERT OR REPLACE INTO polymarket_digests "
                     "(digest_date, posted_at, status, movements, addresses, note) "
                     "VALUES (?, CURRENT_TIMESTAMP, 'empty', 0, ?, ?)",
                     (day, result["addresses_ok"], "; ".join(result["errors"])[:400]))
        conn.commit()
        conn.close()
        print(f"Polymarket digest: no movements ({result['addresses_ok']} wallet(s)).")
        return {"status": "empty", "parts": []}

    # Mark the attempt BEFORE sending. A 'sending' row found on the next run
    # means a crash mid-send: do not re-send (a duplicated digest is worse
    # than a truncated one), but do commit, and say so loudly.
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO polymarket_digests "
                 "(digest_date, posted_at, status, movements, addresses, note) "
                 "VALUES (?, CURRENT_TIMESTAMP, 'sending', ?, ?, NULL)",
                 (day, result["movements"], result["addresses_ok"]))
    conn.commit()
    conn.close()

    sent = send_telegram_digest(result["parts"])

    conn = get_db_connection()
    try:
        if sent:
            for address, rows in result["pending"].items():
                store_position_snapshot(conn, address, rows)
            status = "posted" if len(sent) == len(result["parts"]) else "partial"
        else:
            # Nothing reached the channel: leave the snapshots alone so the
            # same movements are reported again next run.
            status = "send_failed"
        conn.execute("UPDATE polymarket_digests SET status = ?, note = ? "
                     "WHERE digest_date = ?",
                     (status, "; ".join(result["errors"])[:400], day))
        conn.commit()
    finally:
        conn.close()

    print(f"Polymarket digest {status}: {result['movements']} movement(s), "
          f"{len(sent)}/{len(result['parts'])} message(s).")
    return {"status": status, "parts": result["parts"],
            "movements": result["movements"], "errors": result["errors"]}

def seconds_until_digest(now):
    """Seconds until the next weekday digest slot, in TRT.

    Recomputed from the clock every time rather than accumulated from a
    start time. cash_refresh_loop's flat sleep(12*3600) is anchored to
    process start, so a redeploy pins it to whatever wall clock it happened
    to boot at — its own docstring admits as much.
    """
    minute = now.hour * 60 + now.minute
    if now.weekday() < 5 and minute < POLYMARKET_DIGEST_MINUTE:
        target_day = 0
    else:
        target_day = 1
        while (now.weekday() + target_day) % 7 >= 5:
            target_day += 1
    secs = (target_day * 24 * 60 + POLYMARKET_DIGEST_MINUTE - minute) * 60 - now.second
    return max(secs, 1)

def describe_polymarket_config():
    hh, mm = divmod(POLYMARKET_DIGEST_MINUTE, 60)
    if not POLYMARKET_ENABLED:
        return "Polymarket digest: disabled (POLYMARKET_INSIDERS not set)."
    try:
        conn = get_db_connection()
        counts = {a: conn.execute(
            "SELECT COUNT(*) FROM polymarket_positions WHERE address = ?",
            (a,)).fetchone()[0] for a, _ in INSIDER_WALLETS}
        conn.close()
    except Exception:
        counts = {}
    # The stored count is how a permanently-empty (i.e. wrong) address
    # becomes visible without a dedicated alert.
    who = ", ".join(f"{label} {a[:6]}…{a[-4:]} ({counts.get(a, '?')} stored)"
                    for a, label in INSIDER_WALLETS)
    return (f"Polymarket digest: weekdays {hh:02d}:{mm:02d} TRT | "
            f"{len(INSIDER_WALLETS)} wallet(s): {who} | "
            f"min ${POLYMARKET_MIN_USD:.0f} / {POLYMARKET_MIN_DELTA_PCT:.0f}%")

def polymarket_digest_loop():
    """Post the insider digest on weekdays at POLYMARKET_DIGEST_AT_TRT."""
    print(describe_polymarket_config())
    while running:
        try:
            wait = seconds_until_digest(now_trt())
            # Sleep in slices so a clock step, an NTP correction or shutdown
            # is noticed within a minute.
            time.sleep(min(wait, 60))
            now = now_trt()
            minute = now.hour * 60 + now.minute
            due = (now.weekday() < 5
                   and POLYMARKET_DIGEST_MINUTE <= minute
                   < POLYMARKET_DIGEST_MINUTE + POLYMARKET_CATCHUP_MIN)
            if not due:
                continue
            if POLYMARKET_ULTRA_GATE:
                _wait_out_ultra_window("Polymarket insider digest")
            run_polymarket_digest()
        except Exception as e:
            print(f"Polymarket digest loop error: {e}")
            time.sleep(60)

# ----------------- TELEGRAM ALERTS -----------------

def _telegram_post(url, payload):
    """POST to Telegram, surviving a keep-alive socket the peer has closed.

    The pooled connection to api.telegram.org can sit idle for hours between
    filings. If the peer sends its FIN after we have already written the
    request, urllib3 cannot transparently recover it and raises
    ConnectionError — which the caller's bare `except Exception` swallowed,
    losing the alert entirely with nothing but a line on stdout. One
    immediate retry on a *connection* error only (never on a response) costs
    nothing in the happy path and turns a lost alert into one extra RTT.
    Timeouts are a (connect, read) tuple: a bare float applies the value to
    each phase separately, so `timeout=5` was really a 10s worst case.
    """
    try:
        return http_session.post(url, json=payload, timeout=(2, 5))
    except requests.exceptions.ConnectionError as e:
        print(f"Telegram connection dropped ({e}); retrying once on a fresh socket.")
        return http_session.post(url, json=payload, timeout=(2, 5))

def send_telegram_alert(message_text, reply_to_message_id=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot not configured.")
        return None
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown",
        # Telegram builds the link preview by fetching the SEC page ITSELF
        # before it answers sendMessage, and every filing URL is a fresh
        # cache miss for it. That fetch was being waited out on the alert
        # path. Set TELEGRAM_LINK_PREVIEW=true to trade the latency back for
        # the preview card.
        "disable_web_page_preview": not TELEGRAM_LINK_PREVIEW
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        # Optimization: Use http_session for Keep-Alive connection reuse
        resp = _telegram_post(url, payload)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("ok"):
                return result.get("result", {}).get("message_id")
            return None
        else:
            print(f"Telegram Markdown send failed (Status {resp.status_code}): {resp.text}. Retrying as plain text...")
            # Fallback: strip markdown formatting to guarantee delivery
            plain_text = message_text.replace("**", "").replace("`", "").replace("🔗 ", "").replace("[", "").replace("]", "")
            plain_text = re.sub(r'\((https?://.*?)\)', r': \1', plain_text)
            
            payload_plain = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": plain_text
            }
            if reply_to_message_id:
                payload_plain["reply_to_message_id"] = reply_to_message_id
                
            resp_plain = _telegram_post(url, payload_plain)
            if resp_plain.status_code == 200:
                print("Fallback plain text send succeeded.")
                result = resp_plain.json()
                if result.get("ok"):
                    return result.get("result", {}).get("message_id")
                return None
            else:
                print(f"Telegram fallback send failed (Status {resp_plain.status_code}): {resp_plain.text}")
                return None
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")
        return None

def _abs_amount(parsed_data):
    """Unsigned display amount; templates add their own +/- prefix."""
    val = parsed_data.get("btc_abs_str")
    if val:
        return val
    raw = str(parsed_data.get("btc_acquired") or "-")
    return raw.lstrip('+-') or "-"

def partition_atm_securities(atm):
    """Split the parsed securities into (sold, flagged, unsold).

    One place decides which bucket a security belongs to, so the sold line,
    the "satış yok" line and the Groq context can never disagree:

    - sold    — shares moved and no sanity guard objected
    - flagged — shares moved but a guard doubts the numbers (counts=False),
                which financing_source_from_atm already excludes. These used
                to be printed as fact on the sold line while being absent
                from the unsold line.
    - unsold  — everything else, deduped, and never a ticker that appears in
                one of the other two buckets.
    """
    sold, flagged, unsold = [], [], []
    for s in atm.get("securities", []) if atm else []:
        if s.get("shares_sold_num", 0) > 0:
            (flagged if s.get("counts") is False else sold).append(s)
        else:
            unsold.append(s)
    moved = {s["ticker"] for s in sold} | {s["ticker"] for s in flagged}
    seen = set()
    quiet = []
    for s in unsold:
        if s["ticker"] in moved or s["ticker"] in seen:
            continue
        seen.add(s["ticker"])
        quiet.append(s)
    return sold, flagged, quiet

def _atm_sold_lines(parsed_data):
    """Per-security ATM sale lines for Telegram (tickers only).

    Returns None when the filing had no ATM table, [] when the table exists
    but nothing was sold, otherwise one line per sold security.
    """
    atm = parsed_data.get("atm")
    if not atm:
        return None
    sold, _, _ = partition_atm_securities(atm)
    return [f"{s['ticker']}: {s.get('shares_sold', '-')} adet → **{s.get('net_proceeds', '-')}** net"
            for s in sold]

def _atm_block(parsed_data, emoji="💸"):
    """Compact ATM section shared by the alert templates."""
    atm = parsed_data.get("atm")
    if not atm:
        source = parsed_data.get("financing_source_turkish") or parsed_data.get("financing_details")
        if source and source != "-":
            return f"{emoji} Finansman: {source}"
        return f"{emoji} ATM Satışı: Yok"

    sold, flagged, unsold = partition_atm_securities(atm)
    if not sold and not flagged:
        return f"{emoji} ATM Satışı: Yok"

    lines = [f"{s['ticker']}: {s.get('shares_sold', '-')} adet → **{s.get('net_proceeds', '-')}** net"
             for s in sold]
    block = f"{emoji} **ATM Satışı VAR:** " + "\n   ".join(lines) if lines else f"{emoji} **ATM Satışı VAR:**"
    for s in flagged:
        # Say that something moved without stating a number we do not trust.
        block += f"\n   ⚠️ {s['ticker']}: satış var, rakam doğrulanamadı"
    if unsold:
        block += f"\n   {' / '.join(s['ticker'] for s in unsold)}: satış yok"
    return block

def _breakdown_lines(parsed_data):
    """Per-period activity lines for multi-period filings."""
    breakdown = (parsed_data.get("sale_breakdown")
                 or parsed_data.get("purchase_breakdown")
                 or parsed_data.get("mixed_breakdown")
                 or [])
    if len(breakdown) < 2:
        return ""
    text = ""
    for b in breakdown:
        count = parse_btc_number(b.get('btc_count'))
        if count == 0:
            # Explicit "-" cell: a period with no transaction
            text += f"\n  ↳ {b['period']}: 0 BTC (işlem yok)"
            continue
        sign = "-" if b.get("type") == "sale" else "+"
        text += f"\n  ↳ {b['period']}: {sign}{count:,} BTC @ {b['avg_price']} ({b['price']})"
    return text

def _reserve_line(parsed_data):
    """One-line USD Reserve + runway summary for the Telegram templates."""
    reserve = parsed_data.get("usd_reserve_m")
    if reserve is None:
        return ""
    line = f"\n💵 Nakit (USD Reserve): **{_fmt_musd(reserve)}**"
    change = parsed_data.get("reserve_change_m")
    if change:
        line += f" ({'+' if change > 0 else '−'}{_fmt_musd(abs(change))})"
    if parsed_data.get("runway_infinite"):
        line += " → girişler gideri karşılıyor, tükenmiyor"
    elif parsed_data.get("runway_months") is not None:
        annual = parsed_data.get("annual_div_m")
        if annual:
            line += (f" → yıllık ~{_fmt_musd(annual)} temettü gideriyle "
                     f"~{parsed_data['runway_months']:.0f} ay yeter")
        else:
            line += f" → mevcut giderle ~{parsed_data['runway_months']:.0f} ay yeter"
    return line

def format_alert(parsed_data, url):
    event_type = parsed_data.get("event_type")
    abs_amount = _abs_amount(parsed_data)
    price = parsed_data.get('purchase_price') or parsed_data.get('purchase_price_usd') or '-'
    avg = parsed_data.get('avg_price') or parsed_data.get('avg_purchase_price') or '-'
    holdings = parsed_data.get('total_holdings') or parsed_data.get('total_btc_holdings') or '-'
    total_cost = parsed_data.get('total_cost') or parsed_data.get('total_cost_usd') or '-'
    avg_cost = parsed_data.get('avg_cost') or parsed_data.get('avg_cost_per_btc') or '-'
    debt = parsed_data.get('total_debt') or parsed_data.get('total_debt_usd') or '-'
    period = parsed_data.get('purchase_period') or 'Belirtilmemiş'
    inferred_note = " (bilanço farkından tahmini)" if parsed_data.get("inferred") else ""

    # Guard against "+-" when the amount is unknown (LLM-only data)
    plus_amt = f"+{abs_amount}" if abs_amount not in ("-", "0") else abs_amount
    minus_amt = f"-{abs_amount}" if abs_amount not in ("-", "0") else abs_amount

    if event_type == "btc_purchase":
        return f"""🚀 **MSTR BTC ALDI: {plus_amt} BTC!**{inferred_note} (Tutar: {price} | Ort: {avg}){_breakdown_lines(parsed_data)}
📊 Portföy: {holdings} BTC | Maliyet: {total_cost} (Ort: {avg_cost})
{_atm_block(parsed_data)}{_reserve_line(parsed_data)}
🏦 Toplam Borç (Tahvil): {debt}
📅 Dönem: {period}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "btc_sale":
        return f"""🚨 **MSTR BTC SATTI: {minus_amt} BTC!**{inferred_note} (Elde Edilen: {price} | Ort: {avg}){_breakdown_lines(parsed_data)}
📊 Kalan Portföy: {holdings} BTC | Maliyet: {total_cost} (Ort: {avg_cost})
{_atm_block(parsed_data)}{_reserve_line(parsed_data)}
🏦 Toplam Borç (Tahvil): {debt}
📅 Dönem: {period}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "no_purchase":
        return f"""⏸️ **MSTR BTC ALMADI / SATMADI (0 BTC)** — Portföy: {holdings} BTC sabit{_breakdown_lines(parsed_data)}
{_atm_block(parsed_data, emoji="💵")}{_reserve_line(parsed_data)}
📊 Maliyet: {total_cost} (Ort: {avg_cost}) | Borç: {debt}
📅 Dönem: {period}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "financing":
        atm_lines = _atm_sold_lines(parsed_data)
        if atm_lines:
            source_block = "💵 **ATM Satışı VAR:** " + "\n   ".join(atm_lines)
        else:
            source = parsed_data.get('financing_source_turkish') or parsed_data.get('financing_details') or 'Finansman Bildirimi'
            source_block = f"💵 **MSTR Yeni Finansman/Hisse İhraç:** {source}"
        summary = parsed_data.get('summary_turkish')
        summary_block = f"\n**Özet (Analist Yorumu):**\n{summary}\n" if summary else ""
        return f"""{source_block}{_reserve_line(parsed_data)}
{summary_block}
🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "corporate_update":
        summary = parsed_data.get('summary_turkish') or 'Rutin kurumsal güncelleme.'
        return f"""ℹ️ **MSTR Kurumsal Güncelleme (Form 8-K)**
ℹ️ Analiz: {summary[:120]}...

**Detaylar:**
{summary}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    else:
        summary = parsed_data.get('summary_turkish') or 'Detaylar için bildirimi inceleyin.'
        return f"""ℹ️ **MSTR Yeni SEC Bildirimi (Form 8-K)**
ℹ️ Analiz: {summary[:120]}...

**Özet:**
{summary}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

# ----------------- MONITORS ENGINE -----------------

def save_to_database(date, parsed_data, url, accession, form):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR IGNORE INTO processed_filings (accession_number, filing_date, form, url) VALUES (?, ?, ?, ?)",
            (accession, date, form, url)
        )

        # A filing document maps to exactly one history row. If the row is
        # already present (e.g. the filing gets re-processed after a cache
        # loss or a seed/live overlap), don't duplicate it.
        cursor.execute("SELECT 1 FROM purchase_history WHERE url = ? LIMIT 1", (url,))
        if cursor.fetchone():
            print(f"purchase_history already has a row for {url} — skipping duplicate insert.")
            conn.commit()
            conn.close()
            return

        # Signed amount: negative for sales ("-3,588"), positive for buys,
        # "0" for no transaction — the dashboard badge colors by sign.
        # The Groq-only no-table path may still supply legacy unsigned fields.
        btc_value = parsed_data.get("btc_signed_str")
        if btc_value is None:
            btc_value = str(parsed_data.get("btc_acquired") or "-")

        atm = parsed_data.get("atm")
        atm_json = json.dumps(atm, ensure_ascii=False) if atm else None

        cursor.execute(
            """INSERT INTO purchase_history
               (filing_date, period, btc_acquired, purchase_price, avg_price, total_holdings, total_cost, avg_cost, url, total_debt, financing_source, atm_sales, event_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                date,
                parsed_data.get("purchase_period"),
                btc_value,
                str(parsed_data.get("purchase_price") or parsed_data.get("purchase_price_usd") or "-"),
                str(parsed_data.get("avg_price") or parsed_data.get("avg_purchase_price") or "-"),
                str(parsed_data.get("total_holdings") or parsed_data.get("total_btc_holdings") or "-"),
                str(parsed_data.get("total_cost") or parsed_data.get("total_cost_usd") or "-"),
                str(parsed_data.get("avg_cost") or parsed_data.get("avg_cost_per_btc") or "-"),
                url,
                str(parsed_data.get("total_debt") or parsed_data.get("total_debt_usd") or "-"),
                str(parsed_data.get("financing_source_turkish") or parsed_data.get("financing_details") or "-"),
                atm_json,
                parsed_data.get("event_type")
            )
        )
        conn.commit()
        conn.close()
        # A new history row changes both derived figures.
        invalidate_derived_cache()
    except Exception as e:
        print(f"Error saving to database: {e}")

def async_groq_analysis(cleaned_text, url, reply_to_id, table_data=None):
    print("Running async deep Groq analysis (3-pass) in background thread...")
    parsed_data = analyze_filing_deep_groq(cleaned_text, url, table_data=table_data)
    if parsed_data and parsed_data.get("summary_turkish"):
        summary = parsed_data["summary_turkish"]

        # Merge stats for the second detailed report
        table_data = table_data or {}
        acquired = _abs_amount(table_data)
        price = table_data.get("purchase_price") or "-"
        avg = table_data.get("avg_price") or "-"
        holdings = table_data.get("total_holdings") or "-"
        cost = table_data.get("total_cost") or "-"
        avg_cost = table_data.get("avg_cost") or "-"
        debt = table_data.get("total_debt") or "-"
        source = table_data.get("financing_details") or table_data.get("financing_source") or "-"
        period = table_data.get("purchase_period") or "-"

        atm = table_data.get("atm") or {}
        sold_lines = _atm_sold_lines(table_data)
        if sold_lines:
            atm_summary = "; ".join(l.replace("**", "") for l in sold_lines)
        elif sold_lines is not None:
            atm_summary = "Yok"
        else:
            atm_summary = source if source != "-" else "Yok"

        event_type = table_data.get("event_type") or "no_purchase"

        # Guard against "+-" when the amount is unknown
        plus_amt = f"+{acquired}" if acquired not in ("-", "0") else acquired
        minus_amt = f"-{acquired}" if acquired not in ("-", "0") else acquired

        if event_type == "btc_purchase":
            title = f"💡 **[AI Analizi] MSTR BTC ALDI: {plus_amt} BTC!**"
            stats_block = f"""**Finansal Detaylar:**
- 📅 **Dönem**: {period}
- 🪙 **Satın Alınan**: {plus_amt} BTC
- 💰 **Ödenen Tutar**: {price}
- 🏷️ **Ortalama Fiyat**: {avg}
- 📊 **Toplam Portföy**: {holdings} BTC
- 📉 **Kümülatif Maliyet**: {cost}
- 🎯 **Ortalama Maliyet**: {avg_cost}
- 🏦 **Toplam Borç (Tahvil)**: {debt}
- 💵 **ATM Satışları**: {atm_summary}"""
        elif event_type == "btc_sale":
            title = f"💡 **[AI Analizi] MSTR BTC SATTI: {minus_amt} BTC!**"
            stats_block = f"""**Finansal Detaylar:**
- 📅 **Dönem**: {period}
- 🪙 **Satılan Miktar**: {minus_amt} BTC
- 💰 **Elde Edilen Tutar**: {price}
- 🏷️ **Ortalama Satış Fiyatı**: {avg}
- 📊 **Kalan Toplam Portföy**: {holdings} BTC
- 📉 **Kümülatif Maliyet**: {cost}
- 🏦 **Toplam Borç (Tahvil)**: {debt}
- 💵 **ATM Satışları**: {atm_summary}"""
        elif event_type == "financing":
            title = f"💡 **[AI Analizi] MSTR Finansman: {atm.get('total_net_proceeds') or source}**"
            stats_block = f"""**Finansal Detaylar:**
- 📅 **Dönem**: {period}
- 💵 **ATM Satışları**: {atm_summary}"""
        else:
            if atm.get("sold_any"):
                title = f"💡 **[AI Analizi] MSTR Alım Yapmadı — {atm.get('total_net_proceeds', '-')} ATM Geliri**"
            else:
                title = "💡 **[AI Analizi] MSTR Bu Hafta Alım Yapmadı**"
            stats_block = f"""**Finansal Detaylar:**
- 📅 **Dönem**: {period}
- 📊 **Toplam Portföy**: {holdings} BTC
- 📉 **Toplam Maliyet**: {cost}
- 🎯 **Ortalama Maliyet**: {avg_cost}
- 🏦 **Toplam Borç (Tahvil)**: {debt}
- 💵 **ATM Satışları**: {atm_summary}"""

        analysis_text = f"""{title}

{summary}

{stats_block}{_reserve_line(table_data)}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""
        
        send_telegram_alert(analysis_text, reply_to_message_id=reply_to_id)
        print("Async Groq analysis completed and sent.")
    else:
        print("Async Groq analysis finished with no summary output.")

FETCH_RETRIES = int(os.getenv("FETCH_RETRIES", "3"))
FETCH_RETRY_DELAY = float(os.getenv("FETCH_RETRY_DELAY", "0.35"))

def fetch_filing_html(url):
    """Fetch the filing document, tolerating EDGAR's publication race.

    EDGAR routinely lists an accession before the Archives front end serves
    its document, so the first GET can 404 for a second or two. fetch_html
    returns "" for that, process_filing returned False, and the retry was
    gated on the POLL INTERVAL — the next attempt came 2s later in the fast
    window but a full 60s (previously 300s) otherwise. A handful of
    sub-second retries here turns a routine race into a non-event instead of
    a minutes-late alert.
    """
    for attempt in range(max(1, FETCH_RETRIES)):
        html = fetch_html(url)
        if html:
            return html
        if attempt + 1 < FETCH_RETRIES:
            time.sleep(FETCH_RETRY_DELAY)
    return ""

def _record_without_alert(accession, date, form, url):
    """Backfill a stale filing's history row, off the poll thread."""
    try:
        html_content = fetch_filing_html(url)
        if not html_content:
            return
        tables = extract_filing_tables(html_content)
        data = parse_btc_tables(tables)
        if not data:
            return
        atm_data = parse_atm_table(tables)
        if atm_data and atm_data.get("period_scoped", True):
            data["atm"] = atm_data
            data["financing_details"] = financing_source_from_atm(atm_data)
        save_to_database(date, data, url, accession, form)
    except Exception as e:
        print(f"Background record of stale filing {accession} failed: {e}")

def process_filing(accession, date, form, url):
    detected = time.time()
    print(f"Processing new filing: {accession} | Date: {date} | Form: {form} | "
          f"detected {now_trt().strftime('%H:%M:%S')} TRT")

    # Anti-Spam Safeguard: only alert on filings from today or yesterday. The
    # history row is still worth having, so the work still happens — but on a
    # background thread. It used to run inline, so a backlog of stale filings
    # (after a DB wipe, say) blocked the poll loop for ~0.7s each while
    # producing no alert at all.
    try:
        filing_dt = datetime.strptime(date, "%Y-%m-%d").date()
        stale = filing_dt < now_et().date() - timedelta(days=1)
    except Exception as e:
        print(f"Error parsing filing date for spam check: {e}")
        stale = True
    if stale:
        print(f"Filing date {date} is older than yesterday. Recording it in the "
              f"background without a Telegram alert.")
        threading.Thread(target=_record_without_alert,
                         args=(accession, date, form, url), daemon=True).start()
        return True

    t_start = time.time()
    html_content = fetch_filing_html(url)
    if not html_content:
        print(f"Could not load HTML for {url}")
        return False
    t_fetch = time.time()

    # Everything from here to the send is wrapped: an exception used to
    # propagate out of process_filing, leaving the filing unmarked, and
    # because a parse or format failure is DETERMINISTIC on the same
    # document, the poll loop retried it forever and never alerted at all.
    # A broken parse must cost the alert its detail, never its existence.
    try:
        # Local table parsers (offline, instant, no LLM): one HTML parse
        # feeds both the BTC parser and the ATM parser.
        tables = extract_filing_tables(html_content)
        fallback_data = parse_btc_tables(tables)
        atm_data = parse_atm_table(tables)
        t_parse = time.time()

        # The disclosed USD Reserve, from a bounded windowed parse, so the
        # first Telegram message can state cash + months of coverage.
        reserve_ctx = build_reserve_context(date, html_content)
        t_enrich = time.time()
    except Exception as e:
        print(f"Parsing failed for {accession} ({e}); sending the bare alert.")
        main_msg_id = send_telegram_alert(
            f"📋 **MSTR Yeni SEC Bildirimi (Form 8-K)**\n\n"
            f"📅 Tarih: {date}\n"
            f"📄 Bildirim ayrıştırılamadı, içerik analiz ediliyor...\n\n"
            f"🔗 [SEC Bildirimi]({url})")
        if main_msg_id is None:
            return False
        threading.Thread(target=_deferred_analysis,
                         args=(html_content, url, main_msg_id, date, accession, form),
                         daemon=True).start()
        return True

    if reserve_ctx is not None:
        print(f"USD reserve for {date}: ${reserve_ctx['usd_reserve_m']:,.0f}M "
              f"(~{reserve_ctx.get('runway_months')} ay temettü karşılığı)")

    if fallback_data:
        # Table is present! We can determine event and statistics instantly
        # without Groq.
        print("BTC update table found in filing! Bypassing synchronous Groq call for instant alert.")

        if atm_data and atm_data.get("period_scoped", True):
            fallback_data["atm"] = atm_data
            fallback_data["financing_details"] = financing_source_from_atm(atm_data)
        if reserve_ctx:
            fallback_data.update(reserve_ctx)

        # SPEED: Send Telegram FIRST, then save to DB async
        alert_text = format_alert(fallback_data, url)
        main_msg_id = send_telegram_alert(alert_text)
        sent = time.time()
        print(f"Alert latency: fetch {(t_fetch-t_start)*1000:.0f}ms | "
              f"parse {(t_parse-t_fetch)*1000:.0f}ms | "
              f"enrich {(t_enrich-t_parse)*1000:.0f}ms | "
              f"telegram {(sent-t_enrich)*1000:.0f}ms | "
              f"detect→sent {(sent-detected)*1000:.0f}ms | "
              f"sent {now_trt().strftime('%H:%M:%S')} TRT")
        if main_msg_id is None:
            # The alert never landed. Returning True here marked the filing
            # processed and the message was lost for good.
            print(f"Telegram send failed for {accession} — will retry.")
            return False

        # Save to DB in background — don't block the alert pipeline
        threading.Thread(
            target=save_to_database,
            args=(date, fallback_data, url, accession, form),
            daemon=True
        ).start()

        _start_background_enrichment(html_content, url, main_msg_id, date,
                                     fallback_data, reserve_ctx)

    elif atm_data and atm_data.get("sold_any") and atm_data.get("period_scoped", True):
        # ATM-only filing: shares were sold but there is no BTC table.
        # Send an instant financing alert from the parsed ATM data; do NOT
        # add a purchase_history row (no holdings snapshot → would corrupt
        # the charts), only mark the filing as processed.
        print("ATM table found (no BTC table). Sending instant financing alert...")

        atm_parsed = {
            "event_type": "financing",
            "atm": atm_data,
            "financing_details": financing_source_from_atm(atm_data),
            "purchase_period": atm_data.get("period"),
        }
        if reserve_ctx:
            atm_parsed.update(reserve_ctx)

        # clean_html used to run HERE, before the send, purely to feed the
        # background Groq thread — a full second parse of the document on
        # the alert path.
        main_msg_id = send_telegram_alert(format_alert(atm_parsed, url))
        if main_msg_id is None:
            print(f"Telegram send failed for {accession} — will retry.")
            return False
        print(f"Alert latency: detect→sent {(time.time()-detected)*1000:.0f}ms | "
              f"sent {now_trt().strftime('%H:%M:%S')} TRT")

        _start_background_enrichment(html_content, url, main_msg_id, date,
                                     atm_parsed, reserve_ctx)

    else:
        # No table found — but we MUST still send an immediate alert, then
        # analyze async.
        print("No BTC table found. Sending immediate alert, then running async Groq analysis...")

        instant_alert = (
            f"📋 **MSTR Yeni SEC Bildirimi (Form 8-K)**\n\n"
            f"📅 Tarih: {date}\n"
            f"📄 Yeni bir Form 8-K bildirimi tespit edildi. İçerik analiz ediliyor...\n\n"
            f"🔗 [SEC Bildirimi]({url})"
        )
        main_msg_id = send_telegram_alert(instant_alert)
        if main_msg_id is None:
            print(f"Telegram send failed for {accession} — will retry.")
            return False
        print(f"Alert latency: detect→sent {(time.time()-detected)*1000:.0f}ms | "
              f"sent {now_trt().strftime('%H:%M:%S')} TRT")

        threading.Thread(target=_deferred_analysis,
                         args=(html_content, url, main_msg_id, date, accession, form),
                         daemon=True).start()

    return True

def _start_background_enrichment(html_content, url, main_msg_id, date,
                                 parsed_data, reserve_ctx):
    """Post-alert work: the full-text reserve repair and the Groq summary.

    Both parse the whole document again. Started only AFTER the send, since
    clean_html holds the GIL and a parse overlapping the Telegram POST was
    measured inflating that request's round trip several-fold.
    """
    def run():
        cleaned_text = None
        if reserve_ctx is None:
            try:
                cleaned_text = clean_html(html_content)
                val_m = parse_usd_reserve(cleaned_text)
                if val_m is not None:
                    store_usd_reserve(date, val_m)
                    print(f"USD reserve for {date}: ${val_m:,.0f}M (from 8-K, full-text parse)")
            except Exception as e:
                print(f"Background reserve parse failed: {e}")
        if groq_keys:
            try:
                if cleaned_text is None:
                    cleaned_text = clean_html(html_content)
                async_groq_analysis(cleaned_text, url, main_msg_id, parsed_data)
            except Exception as e:
                print(f"Background Groq analysis failed: {e}")
    threading.Thread(target=run, daemon=True).start()

def _deferred_analysis(html_content, url, main_msg_id, date, accession, form):
    """Full analysis for a filing we could not parse into a table."""
    try:
        cleaned_text = clean_html(html_content)
    except Exception as e:
        print(f"Deferred clean_html failed: {e}")
        return

    parsed_data = None
    if groq_keys:
        parsed_data = analyze_filing_deep_groq(cleaned_text, url)

    if not parsed_data:
        try:
            conn2 = get_db_connection()
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT total_debt FROM purchase_history ORDER BY id DESC LIMIT 1")
            last_row = cursor2.fetchone()
            conn2.close()
            last_debt = last_row["total_debt"] if last_row else "$6.7B"
        except Exception:
            last_debt = "$6.7B"

        # Debt carries forward (cumulative); financing_source must describe
        # THIS filing, so it is never carried forward.
        parsed_data = {
            "event_type": "corporate_update",
            "summary_turkish": "Filtrelenemeyen veya tablo içermeyen yeni 8-K bildirimi.",
            "total_debt_usd": last_debt,
            "financing_source_turkish": "-"
        }

    save_to_database(date, parsed_data, url, accession, form)

    summary = parsed_data.get("summary_turkish", "")
    if summary and main_msg_id:
        detail_text = f"💡 **[AI Analizi — Detaylı Rapor]**\n\n{summary}\n\n🔗 [SEC Bildirimi]({url})"
        send_telegram_alert(detail_text, reply_to_message_id=main_msg_id)
        print("Async no-table Groq analysis completed and sent.")

# Cache for processed filings — avoid a DB query on every 250ms tick
_processed_cache = set()
_processed_cache_time = 0

# Per-source stagger clocks and in-flight guards. A fetch that outlives its
# join must not have a second copy started on top of it.
_last_efts_time = 0.0
_last_atom_time = 0.0
_inflight = {"submissions": False, "atom": False, "efts": False}
# Mailbox the fetch threads publish into, drained by whichever tick gets
# there next — so a fetch slower than the tick still delivers.
_pending_lock = threading.Lock()
_pending = {"submissions": None, "atom": [], "efts": []}
_inflight_since = {"submissions": 0.0, "atom": 0.0, "efts": 0.0}
# A socket that wedges past its own timeouts must not retire a source for
# good; after this long the guard is dropped and the source is retried.
INFLIGHT_MAX_AGE = float(os.getenv("INFLIGHT_MAX_AGE", "30"))

# check_for_new_filings mutates module-global conditional-GET and stagger
# state, and is reachable from the poll loop, the Flask admin route and the
# Telegram /check handler. Without this lock two concurrent scans both see an
# accession as unprocessed and both alert on it.
_scan_lock = threading.Lock()

def _refresh_processed_cache():
    """Refresh the processed filings cache from DB. Called sparingly."""
    global _processed_cache, _processed_cache_time
    # Stamp the attempt first: on a DB error the old code left the timestamp
    # untouched, so the >30s guard stayed true and every subsequent tick
    # retried — turning one lock event into a stall on every tick.
    _processed_cache_time = time.time()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT accession_number FROM processed_filings")
        rows = set(row['accession_number'] for row in cursor.fetchall())
        conn.close()
        # Union, never replace: an accession added in-memory after a
        # successful alert may not have reached the DB yet (save_to_database
        # runs in a background thread), and dropping it re-alerts the filing.
        _processed_cache |= rows
    except Exception as e:
        print(f"Error refreshing processed cache: {e}")

def _mark_processed(accession, date, form, url):
    """Record the filing as handled, in memory and on disk, right away."""
    _processed_cache.add(accession)
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT OR IGNORE INTO processed_filings "
            "(accession_number, filing_date, form, url) VALUES (?, ?, ?, ?)",
            (accession, date, form, url))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error marking {accession} processed: {e}")

def check_for_new_filings():
    global last_checked_time, _last_tick_time
    global _last_efts_time, _last_atom_time
    global _submissions_etag, _submissions_last_modified

    if not _scan_lock.acquire(blocking=False):
        # Another scan is already in flight (manual /check or /api/trigger).
        return 0
    try:
        last_checked_time = now_trt().strftime("%d.%m.%Y %H:%M:%S")
        _last_tick_time = time.time()

        # Refresh cache every 30 seconds (not every poll cycle)
        if time.time() - _processed_cache_time > 30:
            _refresh_processed_cache()

        processed = _processed_cache

        # Source cadence. data.sec.gov/submissions is the only endpoint the
        # SEC publishes a latency figure for ("typical processing delay of
        # less than a second"), it supports conditional GET so an unchanged
        # index is a tiny 304, and it carries primaryDocument inline — no
        # follow-up request needed to learn the document name. It runs every
        # tick. The atom feed is a corroborator on the aggressively
        # rate-limited browse-edgar CGI, and EFTS is a full-text index built
        # downstream of dissemination, so it is a backstop, not a trigger.
        now = time.time()
        run_atom = now - _last_atom_time >= 1.0
        run_efts = now - _last_efts_time >= 5.0


        def _guarded(name, fn):
            def run():
                try:
                    fn()
                finally:
                    _inflight[name] = False
            return run

        def _busy(name):
            if not _inflight[name]:
                return False
            if now - _inflight_since[name] > INFLIGHT_MAX_AGE:
                print(f"SEC {name} fetch has been in flight for "
                      f"{now - _inflight_since[name]:.0f}s — retrying it.")
                return False
            return True

        def _spawn(name, fn):
            _inflight[name] = True
            _inflight_since[name] = now
            t = threading.Thread(target=_guarded(name, fn), daemon=True)
            t.start()
            return t

        # Fetches publish into a module-level mailbox rather than a per-tick
        # cell. A fetch that outruns the join deadline is then delivered on
        # the NEXT tick (250ms later) instead of being discarded — which
        # matters now that SEC reads are allowed longer than the tick.
        def _fetch_submissions():
            data, state = fetch_mstr_filings(return_state=True)
            if data is not None:
                with _pending_lock:
                    # Single-tuple assignment keeps (data, state) atomic: a
                    # reader must never see the payload without its
                    # conditional-GET state, or vice versa.
                    _pending["submissions"] = (data, state)
        def _fetch_efts():
            res = fetch_mstr_filings_efts()
            if res:
                with _pending_lock:
                    _pending["efts"] = res
        def _fetch_atom():
            res = fetch_mstr_filings_atom()
            if res:
                with _pending_lock:
                    _pending["atom"] = res

        threads = []
        if not _busy("submissions"):
            threads.append(_spawn("submissions", _fetch_submissions))
        if run_atom and not _busy("atom"):
            _last_atom_time = now
            threads.append(_spawn("atom", _fetch_atom))
        if run_efts and not _busy("efts"):
            _last_efts_time = now
            threads.append(_spawn("efts", _fetch_efts))

        # ONE shared deadline, not one timeout per thread. Three sequential
        # join(timeout=4) calls stacked to a 12s stall inside a window that
        # asks for a tick every 250ms. Results are read from the cells below
        # whether or not their thread finished, so a slow source costs only
        # its own signal for this tick — it can no longer withhold the two
        # that already came back.
        deadline = time.time() + max(1.5, min(4.0, POLL_INTERVAL_CRITICAL * 8))
        for t in threads:
            t.join(timeout=max(0.0, deadline - time.time()))

        # Drain whatever has arrived, from this tick or a slow earlier one.
        with _pending_lock:
            submissions_result = _pending["submissions"]
            atom_result = _pending["atom"]
            efts_result = _pending["efts"]
            _pending["submissions"] = None
            _pending["atom"] = []
            _pending["efts"] = []

        # Collect candidates keyed by accession. The submissions index is
        # authoritative for the document URL, so it always wins over the
        # atom path's index.json guess; previously whichever source was
        # scanned first claimed the accession and shadowed the others, which
        # could livelock a filing on a wrong URL forever.
        candidates = {}

        def _offer(acc, date, form, url, source, authoritative=False):
            if not acc or acc in processed:
                return
            cur = candidates.get(acc)
            if cur is None:
                # `seen_by` records every source that saw it, in arrival
                # order, so the logs answer which endpoint is actually
                # winning the race instead of naming a pair of candidates.
                candidates[acc] = {"date": date, "form": form, "url": url,
                                   "authoritative": authoritative,
                                   "seen_by": [source]}
                return
            if source not in cur["seen_by"]:
                cur["seen_by"].append(source)
            if (authoritative and not cur["authoritative"]) or (url and not cur["url"]):
                cur["url"] = url or cur["url"]
                cur["authoritative"] = cur["authoritative"] or authoritative
            if date and not cur["date"]:
                cur["date"] = date

        # Submissions (authoritative URL, every tick)
        data, sub_state = submissions_result or (None, None)
        if data:
            recent = data.get('filings', {}).get('recent', {})
            if recent:
                forms = recent.get('form', [])
                accession_numbers = recent.get('accessionNumber', [])
                filing_dates = recent.get('filingDate', [])
                primary_docs = recent.get('primaryDocument', [])
                # EDGAR updates these parallel arrays as a filing is indexed,
                # so they can be momentarily uneven. Never index past the
                # shortest — an IndexError here used to abort the whole poll.
                usable = min(len(forms), len(accession_numbers),
                             len(filing_dates), len(primary_docs))
                if usable < len(forms):
                    print(f"Submissions index arrays uneven ({len(forms)} forms vs "
                          f"{usable} usable) — scanning the consistent prefix.")

                for idx in range(usable):
                    if forms[idx] == '8-K':
                        acc_num = accession_numbers[idx]
                        doc = primary_docs[idx]
                        acc_num_no_dash = acc_num.replace('-', '')
                        url = (f"https://www.sec.gov/Archives/edgar/data/1050446/"
                               f"{acc_num_no_dash}/{doc}") if doc else ""
                        _offer(acc_num, filing_dates[idx], forms[idx], url,
                               "submissions", authoritative=bool(doc))
            # The payload has been scanned — only NOW is it safe to remember
            # the validators. A timed-out fetch leaves data None, nothing is
            # committed, and the next poll re-fetches with the OLD ETag.
            _commit_submissions_state(sub_state)

        # Atom (fastest to publish, but carries no document name)
        for result in atom_result:
            _offer(result["accession"], result["date"], "8-K",
                   result.get("url") or "", "atom")

        # EFTS (lagging full-text index, backstop only)
        for result in efts_result:
            _offer(result["accession"], result["date"], "8-K", result["url"], "efts")

        if not candidates:
            return 0

        # Newest first. The sources hand back newest-first lists and the old
        # code reversed them, so on any multi-filing batch the just-landed
        # filing was alerted LAST, behind every stale one.
        ordered = sorted(candidates.items(),
                         key=lambda kv: (kv[1]["date"] or "", kv[0]), reverse=True)

        for acc, info in ordered:
            url = info["url"]
            if not url:
                # Only the atom path can be URL-less. One extra round trip,
                # and only for an accession no other source has resolved.
                url = _resolve_primary_document(acc)
            if not url:
                print(f"Saw new filing {acc} but no document URL yet — "
                      f"retrying on the next tick.")
                continue
            print(f"New 8-K {acc} ({info['date']}) first seen via "
                  f"{'+'.join(info['seen_by'])}.")
            ok = False
            try:
                ok = process_filing(acc, info["date"], info["form"], url)
            except Exception as e:
                print(f"Error processing filing {acc}: {e}")
            if ok:
                # Persist immediately so a cache refresh landing before the
                # background save cannot resurrect the filing.
                _mark_processed(acc, info["date"], info["form"], url)
            else:
                # Invalidate the conditional-GET state: without this, the
                # next polls would get 304 (index unchanged) and never retry
                # this filing until the index changes again.
                _submissions_etag = None
                _submissions_last_modified = None
                print(f"Filing {acc} not fully processed — will retry on the next poll.")

        return len(candidates)
    finally:
        _scan_lock.release()

def connection_warmer_loop():
    """Keep TCP/TLS connections hot across the whole fast band.

    A cold connection costs a DNS lookup plus 2-3 round trips before the
    first request byte. The previous version warmed only www.sec.gov and
    Telegram, only inside the ultra window, and only every 50s — long
    enough for a NAT/proxy idle reaper to have closed the socket again, and
    starting too late to help the run-up. It now covers every host on the
    detection and alert paths for the whole fast band.
    """
    warm_targets = [
        "https://www.sec.gov/robots.txt",
        "https://data.sec.gov/submissions/CIK0001050446.json",
        "https://efts.sec.gov/LATEST/search-index?forms=8-K&ciks=0001050446",
    ]
    while running:
        try:
            mode, _, _ = poll_schedule(now_et())
            if mode == "Normal Mode":
                time.sleep(30)
                continue
            for url in warm_targets:
                try:
                    http_session.head(url, timeout=3)
                except Exception:
                    pass
            if TELEGRAM_BOT_TOKEN:
                try:
                    http_session.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=3)
                except Exception:
                    pass
            time.sleep(20)
        except Exception:
            time.sleep(30)

def polling_loop():
    global current_mode, running, _source_report_time
    print("Starting SEC Polling Loop...")
    print(describe_poll_config())
    # Anchor the first health report a full interval out; otherwise it fires
    # on the first tick and reports "over 0min" with a two-request sample.
    _source_report_time = time.time()

    while running:
        # The cadence is derived from the US Eastern clock BEFORE the scan,
        # so a failed scan can never demote the fast windows, and the sleep
        # is capped at the distance to the next window boundary so the loop
        # can never sleep through one.
        interval = POLL_INTERVAL_NORMAL
        budget = interval
        try:
            et = now_et()
            mode, interval, to_boundary = poll_schedule(et)
            budget = min(interval, to_boundary)
            if current_mode != mode:
                print(f"Entering {mode.upper()} at {et.strftime('%H:%M:%S')} ET "
                      f"({now_trt().strftime('%H:%M:%S')} TRT), interval={interval}s")
                current_mode = mode
        except Exception as e:
            print(f"Polling schedule computation failed: {e}")

        try:
            check_for_new_filings()
            report_source_health()
        except Exception as e:
            # Keep the cadence the clock asked for; only back off a little in
            # normal mode so a persistent failure doesn't spin.
            print(f"Exception in polling loop: {e}")
            if interval >= POLL_INTERVAL_NORMAL:
                budget = POLL_INTERVAL_NORMAL

        try:
            time.sleep(max(0.05, budget))
        except ValueError as e:
            # A hostile POLL_INTERVAL_* env value must not crash-loop the bot.
            print(f"Bad poll interval ({e}); falling back to 1s.")
            time.sleep(1)

# ----------------- FLASK WEB ROUTES & APIS -----------------

@app.route('/')
def dashboard_index():
    return render_template('index.html')

@app.route('/api/status')
def get_bot_status():
    et = now_et()
    mode, interval, to_boundary = poll_schedule(et)
    return jsonify({
        "mode": current_mode,
        "scheduled_mode": mode,
        "interval_seconds": interval,
        "seconds_to_next_window_change": to_boundary,
        "et_time": et.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "trt_time": now_trt().strftime("%Y-%m-%d %H:%M:%S"),
        "intervals": {
            "critical": POLL_INTERVAL_CRITICAL,
            "fast": POLL_INTERVAL_FAST,
            "normal": POLL_INTERVAL_NORMAL,
        },
        "config_warning": ("POLL_INTERVAL_CRITICAL is slower than 1s/tick"
                           if POLL_INTERVAL_CRITICAL > 1.0 else None),
        "ultra_window_et": f"{ULTRA_WINDOW_ET[0]//60:02d}:{ULTRA_WINDOW_ET[0]%60:02d}"
                           f"-{ULTRA_WINDOW_ET[1]//60:02d}:{ULTRA_WINDOW_ET[1]%60:02d}",
        "fast_window_et": f"{FAST_WINDOW_ET[0]//60:02d}:{FAST_WINDOW_ET[0]%60:02d}"
                          f"-{FAST_WINDOW_ET[1]//60:02d}:{FAST_WINDOW_ET[1]%60:02d}",
        "last_checked": last_checked_time,
        "seconds_since_last_poll": (round(time.time() - _last_tick_time, 1)
                                    if _last_tick_time else None),
        # "Son sorgu" tracks the POLLER, not the data. It ticked every second
        # while the history sat frozen on 2026-07-13 for seven weeks — the one
        # indicator on the page actively hid the problem. These describe the
        # DATA.
        **data_freshness(),
        "sources": source_health_snapshot(),
        "db_path": DB_PATH
    })

def data_freshness():
    """How old the numbers on the page actually are."""
    out = {"latest_filing_date": None, "data_age_days": None,
           "total_debt_asof": None, "polymarket_asof": None}
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"data_freshness error: {e}")
        return out

    # Each lookup is guarded on its own: one missing table must not blank the
    # whole report. The point of this endpoint is to make staleness visible,
    # so it failing quietly would defeat itself.
    def one(sql, key):
        try:
            row = conn.execute(sql).fetchone()
            out[key] = row[0] if row else None
        except Exception:
            pass

    try:
        one("SELECT MAX(filing_date) FROM purchase_history", "latest_filing_date")
        one("SELECT MAX(period_end) FROM financial_metrics WHERE metric = 'total_debt'",
            "total_debt_asof")
        one("SELECT MAX(fetched_at) FROM polymarket_live", "polymarket_asof")
    finally:
        conn.close()

    if out["latest_filing_date"]:
        try:
            latest = datetime.strptime(out["latest_filing_date"][:10], "%Y-%m-%d").date()
            out["data_age_days"] = (now_et().date() - latest).days
        except ValueError:
            pass
    return out

@app.route('/health')
def health_check():
    """Liveness probe: fails when the poll loop has stopped ticking.

    Point Railway's healthcheckPath here so a wedged poller is restarted
    instead of sitting silent until someone notices no alerts arrived.
    """
    mode, interval, _ = poll_schedule(now_et())
    # Generous multiple of the cadence, floored so a 0.25s window doesn't
    # trip on one slow tick.
    stale_after = max(120.0, interval * 20)
    age = None
    if _last_tick_time:
        age = time.time() - _last_tick_time
    ok = age is not None and age < stale_after
    return jsonify({
        "ok": ok,
        "mode": mode,
        "seconds_since_last_poll": round(age, 1) if age is not None else None,
        "stale_after_seconds": stale_after,
    }), (200 if ok else 503)

@app.route('/api/history')
def get_purchase_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchase_history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    history_list = []
    for r in rows:
        history_list.append({
            "id": r["id"],
            "filing_date": r["filing_date"],
            "period": r["period"],
            "btc_acquired": r["btc_acquired"],
            "purchase_price": r["purchase_price"],
            "avg_price": r["avg_price"],
            "total_holdings": r["total_holdings"],
            "total_cost": r["total_cost"],
            "avg_cost": r["avg_cost"],
            "total_debt": r["total_debt"] if "total_debt" in r.keys() else "$6.7B",
            "financing_source": r["financing_source"] if "financing_source" in r.keys() else "ATM Hisse Satışı",
            "atm_sales": _safe_json_loads(r["atm_sales"]) if "atm_sales" in r.keys() else None,
            "event_type": r["event_type"] if "event_type" in r.keys() else None,
            "url": r["url"]
        })
    return jsonify(history_list)

def _safe_json_loads(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None

@app.route('/api/cash')
def get_cash_reserves():
    try:
        conn = get_db_connection()
        # Primary: weekly USD Reserve parsed from the 8-Ks. Fallback: XBRL
        # quarterly cash & equivalents.
        rows = conn.execute(
            "SELECT period_end, value, form FROM financial_metrics "
            "WHERE metric = 'usd_reserve' ORDER BY period_end"
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT period_end, value, form FROM financial_metrics "
                "WHERE metric = 'cash_and_equivalents' ORDER BY period_end"
            ).fetchall()
        conn.close()
        return jsonify([
            {"period_end": r["period_end"], "value": r["value"], "form": r["form"]}
            for r in rows
        ])
    except Exception as e:
        print(f"/api/cash error: {e}")
        return jsonify([])

@app.route('/api/official', methods=['GET', 'POST'])
def official_figures():
    """Read or (password-protected) set Strategy's own published figures
    from strategy.com (USD Reserve, Annual Dividends, total Pref, Debt).
    These are ground truth — the USD reserve becomes the newest cash anchor.
    POST params: password, asof (YYYY-MM-DD), usd_reserve_m, annual_dividends_m,
    pref_m, debt_m (all $M)."""
    if request.method == 'GET':
        usd = None
        try:
            conn = get_db_connection()
            row = conn.execute(
                "SELECT period_end, value FROM financial_metrics "
                "WHERE metric='cash_and_equivalents' AND form='strategy.com' "
                "ORDER BY period_end DESC LIMIT 1").fetchone()
            conn.close()
            if row:
                usd = {"asof": row["period_end"], "value_m": row["value"] / 1e6}
        except Exception:
            pass
        return jsonify({
            "usd_reserve": usd,
            "annual_dividends_m": (get_official_metric("official_annual_dividends") or {}).get("value_m"),
            "pref_m": (get_official_metric("official_pref") or {}).get("value_m"),
            "debt_m": (get_official_metric("official_debt") or {}).get("value_m"),
        })

    if ADMIN_PASSWORD:
        req_pass = request.args.get("password") or request.headers.get("X-Admin-Password")
        if req_pass != ADMIN_PASSWORD:
            return jsonify({"status": "error", "message": "Yetkisiz işlem: Şifre hatalı."}), 401

    def _num(name):
        v = request.args.get(name)
        try:
            return float(v) if v not in (None, "") else None
        except ValueError:
            return None

    asof = request.args.get("asof")
    if not asof:
        return jsonify({"status": "error", "message": "asof (YYYY-MM-DD) gerekli."}), 400
    n = store_official_figures(
        usd_reserve_m=_num("usd_reserve_m"), annual_dividends_m=_num("annual_dividends_m"),
        pref_m=_num("pref_m"), debt_m=_num("debt_m"), asof=asof)
    return jsonify({"status": "success", "message": f"{n} resmi değer kaydedildi ({asof})."})

@app.route('/api/cashflow')
def get_cashflow():
    try:
        return jsonify(compute_cash_estimate() or {})
    except Exception as e:
        print(f"/api/cashflow error: {e}")
        return jsonify({})

@app.route('/api/atm_audit')
def get_atm_audit():
    """Week-by-week ATM audit trail: every parsed sale with its filing URL,
    implied per-share price, and whether it is counted in the cash estimate
    — so any suspicious number can be verified against the source filing."""
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT filing_date, url, atm_sales FROM purchase_history "
            "WHERE atm_sales IS NOT NULL AND atm_sales <> '' ORDER BY filing_date DESC").fetchall()
        conn.close()

        out = []
        totals = {}
        for r in rows:
            atm = _safe_json_loads(r["atm_sales"]) or {}
            counted = atm.get("period_scoped") is not False
            secs = []
            for s in atm.get("securities", []):
                shares = s.get("shares_sold_num") or 0
                if shares <= 0:
                    continue
                net_usd = (s.get("net_proceeds_num_m") or 0.0) * 1e6
                row_counts = counted and s.get("counts") is not False
                secs.append({
                    "ticker": s.get("ticker"),
                    "shares_sold": s.get("shares_sold"),
                    "notional": s.get("notional"),
                    "net_proceeds": s.get("net_proceeds"),
                    "available": s.get("available"),
                    "implied_price_usd": round(net_usd / shares, 2) if shares and net_usd else None,
                    "counts": row_counts,
                    "suspect": s.get("suspect"),
                })
                if row_counts:
                    totals[s.get("ticker")] = round(
                        totals.get(s.get("ticker"), 0.0) + (s.get("net_proceeds_num_m") or 0.0), 1)
            if secs or atm.get("note"):
                out.append({
                    "filing_date": r["filing_date"],
                    "url": r["url"],
                    "period": atm.get("period"),
                    "period_scoped": atm.get("period_scoped"),
                    "counted_in_estimate": counted,
                    "note": atm.get("note"),
                    "securities": secs,
                })
        return jsonify({"weeks": out, "counted_totals_by_ticker_m": totals})
    except Exception as e:
        print(f"/api/atm_audit error: {e}")
        return jsonify({"weeks": [], "counted_totals_by_ticker_m": {}})

@app.route('/audit')
def atm_audit_page():
    """Human-readable ATM audit: every parsed weekly sale with its raw
    stored values, implied per-share price, and filing link — open this to
    trace any suspicious total (e.g. STRC) to the exact week and filing."""
    data = get_atm_audit().get_json()
    weeks = data.get("weeks", [])
    totals = data.get("counted_totals_by_ticker_m", {})

    def esc(x):
        return (str(x) if x is not None else "-").replace("&", "&amp;").replace("<", "&lt;")

    total_rows = "".join(
        f"<li><b>{esc(t)}</b>: ${v:,.1f}M (${v/1000:,.2f}B)</li>"
        for t, v in sorted(totals.items(), key=lambda kv: -kv[1]))

    def period_span_days(period):
        # A weekly table spans ~5-7 days; a cumulative one spans months.
        if not period:
            return None
        try:
            import datetime as _dt
            dates = re.findall(r'([A-Z][a-z]+ \d{1,2}, \d{4})', period)
            if len(dates) >= 2:
                d0 = _dt.datetime.strptime(dates[0], "%B %d, %Y")
                d1 = _dt.datetime.strptime(dates[-1], "%B %d, %Y")
                return (d1 - d0).days
        except Exception:
            return None
        return None

    body = []
    for w in weeks:
        span = period_span_days(w.get("period"))
        long_period = span is not None and span > 14
        for s in w.get("securities", []):
            implied = s.get("implied_price_usd")
            suspect = s.get("suspect")
            # Highlight rows with an implausible per-share price or a
            # suspiciously long (cumulative-looking) period window
            bad = (suspect is not None) or long_period or (implied is not None and (
                implied > (5000 if s.get("ticker") == "MSTR" else 1000) or implied < 5))
            style = ' style="background:#3a1414"' if bad else ''
            counted = "✅" if s.get("counts") else "❌ sayılmıyor"
            period_cell = esc(w.get("period"))
            if long_period:
                period_cell += f" <b style='color:#fbbf24'>⚠ {span} gün</b>"
            body.append(
                f"<tr{style}>"
                f"<td>{esc(w['filing_date'])}</td>"
                f"<td style='font-size:.72rem;color:#9ca3af'>{period_cell}</td>"
                f"<td><b>{esc(s.get('ticker'))}</b></td>"
                f"<td style='text-align:right'>{esc(s.get('shares_sold'))}</td>"
                f"<td style='text-align:right'>{esc(s.get('notional'))}</td>"
                f"<td style='text-align:right'>{esc(s.get('net_proceeds'))}</td>"
                f"<td style='text-align:right'>{esc(s.get('available'))}</td>"
                f"<td style='text-align:right'>{('$'+format(implied, ',.2f')) if implied is not None else '-'}</td>"
                f"<td>{counted}</td>"
                f"<td style='color:#f87171'>{esc(suspect) if suspect else ''}</td>"
                f"<td><a href='{esc(w.get('url'))}' target='_blank'>filing</a></td>"
                f"</tr>")

    html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATM Denetim</title>
<style>
body{{background:#0b0e17;color:#e5e7eb;font-family:system-ui,sans-serif;padding:1rem;margin:0}}
h1{{font-size:1.1rem}} p{{color:#9ca3af;font-size:.85rem}}
ul{{color:#e5e7eb}} .wrap{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.8rem;min-width:820px}}
th,td{{padding:.4rem .5rem;border-bottom:1px solid #1f2937;white-space:nowrap}}
th{{color:#9ca3af;text-align:left;position:sticky;top:0;background:#0b0e17}}
a{{color:#38bdf8}}
</style></head><body>
<h1>ATM Satış Denetimi (hafta hafta)</h1>
<p>Hesaba katılan ürün bazlı toplamlar (nakit tahmininde kullanılan):</p>
<ul>{total_rows or '<li>veri yok</li>'}</ul>
<p>Kırmızı satırlar = hisse başı ima fiyatı mantıksız veya sütun kayması şüphesi. "Net Proceeds" sütununu
gerçek filing ile karşılaştır (filing linkine tıkla). İmtiyazlı hisseler ~$80-105, MSTR daha yüksek olmalı.</p>
<div class="wrap"><table>
<thead><tr><th>Tarih</th><th>Dönem</th><th>Ürün</th><th>Adet</th><th>Nominal</th><th>Net Gelir</th>
<th>Kalan Kapasite</th><th>Hisse/$</th><th>Sayılıyor?</th><th>Şüphe</th><th>Kaynak</th></tr></thead>
<tbody>{''.join(body) or '<tr><td colspan=10>Henüz ATM verisi yok (backfill sürüyor olabilir)</td></tr>'}</tbody>
</table></div>
</body></html>"""
    return html

@app.route('/api/dividends')
def get_dividends():
    try:
        return jsonify(compute_dividend_model())
    except Exception as e:
        print(f"/api/dividends error: {e}")
        return jsonify({"series": [], "model_monthly_total_m": 0})

@app.route('/api/trigger', methods=['POST'])
def force_trigger():
    # Fail closed. With ADMIN_PASSWORD unset this endpoint was open to
    # anyone, and it runs SEC fetches, a full document parse and Groq calls
    # synchronously on the request thread — competing with the poller for
    # the connection pool and the GIL, and able to fire real Telegram alerts.
    if not ADMIN_PASSWORD:
        return jsonify({"status": "error",
                        "message": "ADMIN_PASSWORD ayarlanmadan bu uç nokta kullanılamaz."}), 403
    req_pass = request.args.get("password") or request.headers.get("X-Admin-Password")
    if req_pass != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Yetkisiz işlem: Şifre hatalı."}), 401
    
    trigger_type = request.args.get("type", "poll")

    if trigger_type in ("polymarket", "polymarket_dry"):
        res = run_polymarket_digest(force=True,
                                    dry_run=(trigger_type == "polymarket_dry"))
        return jsonify({"status": "success", "result": res})
    
    if trigger_type == "poll":
        try:
            new_count = check_for_new_filings()
            return jsonify({
                "status": "success",
                "message": f"SEC Edgar API sorgulandı. {new_count} adet yeni bildirim bulundu."
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Sorgulama hatası: {str(e)}"
            }), 500
            
    elif trigger_type == "test":
        test_url = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm" # Default fallback
        try:
            try:
                data = fetch_mstr_filings(use_conditional=False)
                if data:
                    recent = data.get('filings', {}).get('recent', {})
                    forms = recent.get('form', [])
                    accession_numbers = recent.get('accessionNumber', [])
                    primary_docs = recent.get('primaryDocument', [])
                    for idx, form in enumerate(forms):
                        if form == '8-K':
                            acc_num = accession_numbers[idx]
                            doc = primary_docs[idx]
                            acc_num_no_dash = acc_num.replace('-', '')
                            test_url = f"https://www.sec.gov/Archives/edgar/data/1050446/{acc_num_no_dash}/{doc}"
                            print(f"Test route dynamically selected latest Form 8-K: {test_url}")
                            break
            except Exception as e:
                print(f"Error fetching latest filing for test route: {e}, using default fallback.")
                
            # Send immediate alert that we started testing
            send_telegram_alert("🧪 **[TEST BİLDİRİMİ]** MSTR SEC alım raporu testi başlatıldı. Analiz ediliyor...")
            
            html_content = fetch_html(test_url)
            if not html_content:
                return jsonify({"status": "error", "message": "Test HTML'i SEC EDGAR'dan çekilemedi."}), 500
                
            cleaned_text = clean_html(html_content)
            test_tables = extract_filing_tables(html_content)
            fallback_data = parse_btc_tables(test_tables)
            test_atm = parse_atm_table(test_tables)
            if fallback_data and test_atm and test_atm.get("period_scoped", True):
                fallback_data["atm"] = test_atm
                fallback_data["financing_details"] = financing_source_from_atm(test_atm)
            parsed_data = None

            if groq_keys:
                parsed_data = analyze_filing_with_groq(cleaned_text, test_url)

            if fallback_data:
                if parsed_data:
                    # The locally parsed table data is authoritative — Groq
                    # output only fills the narrative fields.
                    if parsed_data.get("event_type") in ["corporate_update", "financing", None]:
                        parsed_data["event_type"] = fallback_data["event_type"]
                    for key in ("purchase_period", "btc_acquired", "btc_signed_str",
                                "btc_abs_str", "btc_net_signed", "purchase_price",
                                "avg_price", "total_holdings", "total_cost", "avg_cost",
                                "total_debt", "atm", "financing_details", "inferred",
                                "sale_breakdown", "purchase_breakdown", "mixed_breakdown"):
                        if fallback_data.get(key) is not None:
                            parsed_data[key] = fallback_data[key]
                else:
                    parsed_data = fallback_data
            elif test_atm and test_atm.get("sold_any") and test_atm.get("period_scoped", True) and not parsed_data:
                parsed_data = {
                    "event_type": "financing",
                    "atm": test_atm,
                    "financing_details": financing_source_from_atm(test_atm),
                    "purchase_period": test_atm.get("period"),
                }

            if parsed_data:
                if "total_debt" not in parsed_data and "total_debt_usd" not in parsed_data:
                    parsed_data["total_debt"] = "$6.7B"
                if "financing_source_turkish" not in parsed_data and "financing_details" not in parsed_data:
                    parsed_data["financing_source_turkish"] = "ATM Hisse Satışı"
                    
                alert_text = format_alert(parsed_data, test_url)
                test_alert_text = f"🧪 **[TEST BİLDİRİMİ - SONUÇ]**\n\n{alert_text}"
                
                sent_successfully = send_telegram_alert(test_alert_text)
                if not sent_successfully:
                    return jsonify({
                        "status": "error",
                        "message": "Analiz başarılı fakat Telegram'a bildirim gönderilemedi. Bot token ve chat ID ayarlarınızı veya botun grup yetkisini kontrol edin."
                    }), 500
                
                return jsonify({
                    "status": "success",
                    "preview": test_alert_text
                })
            else:
                return jsonify({"status": "error", "message": "Bildirim metni parse edilemedi."}), 500
                
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Test tetikleme hatası: {str(e)}"
            }), 500
            
    return jsonify({"status": "error", "message": "Bilinmeyen tetikleyici tipi."}), 400

# ----------------- TELEGRAM BOT COMMANDS -----------------

if bot:
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(
            message,
            "📊 **MSTR SEC Filings Monitor Bot**\n\n"
            "Bu bot MicroStrategy SEC bildirimlerini (Form 8-K) gerçek zamanlı takip eder. "
            "TR Saatiyle 14:59 - 15:10 arasında 1 saniyede bir yüksek hızlı sorgulama yapar.\n\n"
            "**Komutlar:**\n"
            "/data veya /history - Son BTC alım geçmişini ve toplam portföy durumunu gösterir.\n"
            "/check - Hemen şimdi zorla SEC EDGAR kontrolü yapar.\n"
            "/insider - Polymarket içeriden takip özetini şimdi kanala gönderir.\n"
            "/insider_test - Özeti kanala göndermeden sadece size gösterir.\n"
            "/test_integration - Son BTC alım raporunu (22 Haziran) okuyup analiz testi yapar.\n"
            "/status - Botun çalışma durumunu ve anlık modunu gösterir.",
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['status'])
    def send_status(message):
        et = now_et()
        mode, interval, _ = poll_schedule(et)
        us, ue = ULTRA_WINDOW_ET
        bot.reply_to(
            message,
            f"🤖 **Bot Durum Raporu**\n\n"
            f"🟢 **Durum**: Çalışıyor\n"
            f"⚡ **Aktif Mod**: {mode} ({interval}s)\n"
            f"⏰ **Sunucu Saati (TR)**: {now_trt().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"🇺🇸 **SEC Saati (ET)**: {et.strftime('%d.%m.%Y %H:%M:%S %Z')}\n"
            f"🎯 **Ultra pencere**: {us//60:02d}:{us%60:02d}-{ue//60:02d}:{ue%60:02d} ET\n"
            f"🔄 **Son SEC Kontrolü**: {last_checked_time or 'Yapılmadı'}\n"
            f"📁 **Veritabanı Yolu**: `{DB_PATH}`",
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['check'])
    def force_check_telegram(message):
        bot.reply_to(message, "SEC EDGAR sorgulanıyor, lütfen bekleyin...")
        try:
            new_count = check_for_new_filings()
            bot.reply_to(message, f"Sorgulama tamamlandı. {new_count} adet yeni bildirim bulundu.")
        except Exception as e:
            bot.reply_to(message, f"Sorgulama sırasında hata oluştu: {str(e)}")

    @bot.message_handler(commands=['insider'])
    def insider_digest_telegram(message):
        if not POLYMARKET_ENABLED:
            bot.reply_to(message, "Polymarket takibi kapalı: POLYMARKET_INSIDERS ayarlanmamış.")
            return
        bot.reply_to(message, "🎯 Polymarket özeti hazırlanıyor...")
        # Can take up to POLYMARKET_BUDGET_S; must not block infinity_polling.
        threading.Thread(target=lambda: run_polymarket_digest(force=True),
                         daemon=True).start()

    @bot.message_handler(commands=['insider_test'])
    def insider_dry_run_telegram(message):
        """Render the digest back to the requester without posting it.

        The endpoints could not be reached from the machine this was written
        on, so this is how the real response shape gets verified: against
        production data, without spending the day's diff or posting to the
        channel.
        """
        if not POLYMARKET_ENABLED:
            bot.reply_to(message, "Polymarket takibi kapalı: POLYMARKET_INSIDERS ayarlanmamış.")
            return

        def _run():
            res = run_polymarket_digest(dry_run=True)
            if res["parts"]:
                for part in res["parts"]:
                    bot.reply_to(message, part, parse_mode="Markdown")
            else:
                bot.reply_to(message,
                             f"Yeni hareket yok. Durum: {res['status']}. "
                             f"{'; '.join(res.get('errors') or []) or '-'}")
        threading.Thread(target=_run, daemon=True).start()

    @bot.message_handler(commands=['test_integration'])
    def test_integration_telegram(message):
        bot.reply_to(message, "22 Haziran alım raporu çekilip Groq/Telegram entegrasyonu test ediliyor...")
        test_url = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm"
        try:
            send_telegram_alert("🧪 **[TEST BİLDİRİMİ]** Telegram entegrasyon testi başlatıldı. Analiz ediliyor...")
            html_content = fetch_html(test_url)
            if html_content:
                cleaned_text = clean_html(html_content)
                parsed_data = None
                if GROQ_API_KEY:
                    parsed_data = analyze_filing_with_groq(cleaned_text, test_url)
                if not parsed_data:
                    parsed_data = parse_table_fallback(html_content)
                    
                if parsed_data:
                    if "total_debt" not in parsed_data and "total_debt_usd" not in parsed_data:
                        parsed_data["total_debt"] = "$6.7B"
                    if "financing_source_turkish" not in parsed_data and "financing_details" not in parsed_data:
                        parsed_data["financing_source_turkish"] = "ATM Hisse Satışı"
                        
                    alert_text = format_alert(parsed_data, test_url)
                    test_alert_text = f"🧪 **[TEST BİLDİRİMİ - SONUÇ]**\n\n{alert_text}"
                    send_telegram_alert(test_alert_text)
                    bot.reply_to(message, f"Test alerti Telegram'a atıldı! Analiz Önizleme:\n\n{alert_text}", parse_mode="Markdown")
                else:
                    bot.reply_to(message, "Rapor parse edilemedi.")
            else:
                bot.reply_to(message, "SEC EDGAR'dan rapor çekilemedi.")
        except Exception as e:
            bot.reply_to(message, f"Test sırasında hata oluştu: {str(e)}")

    @bot.message_handler(commands=['data', 'history'])
    def send_history(message):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM purchase_history ORDER BY id DESC LIMIT 1")
        latest = cursor.fetchone()
        
        cursor.execute("SELECT * FROM purchase_history ORDER BY id DESC LIMIT 6")
        recent_purchases = cursor.fetchall()
        conn.close()
        
        if not latest:
            bot.reply_to(message, "Veritabanında kayıtlı alım geçmişi bulunamadı.")
            return
            
        summary = (
            f"📊 **MSTR Güncel Portföy Özeti**\n"
            f"🪙 **Toplam BTC Varlığı**: {latest['total_holdings']} BTC\n"
            f"📉 **Toplam Kümülatif Maliyet**: {latest['total_cost']}\n"
            f"🎯 **Ortalama Maliyet**: {latest['avg_cost']}\n"
            f"🏦 **Toplam Borç (Tahvil)**: {latest['total_debt']}\n"
            f"💸 **Finansman Kaynağı**: {latest['financing_source']}\n"
            f"📅 **Son Güncelleme**: {latest['filing_date']}\n\n"
            f"📜 **Son Alım/İşlem Geçmişi (Son 6 Bildirim):**\n"
        )
        
        for idx, item in enumerate(recent_purchases):
            date = item['filing_date']
            acquired = item['btc_acquired']
            avg_price = item['avg_price']
            
            if acquired == '0' or acquired == '-':
                summary += f"{idx+1}. 📅 {date} | Alım yapılmadı ℹ️\n"
            elif str(acquired).startswith('-'):
                summary += f"{idx+1}. 📅 {date} | **{acquired} BTC** (Ort. {avg_price}) 🔻\n"
            else:
                summary += f"{idx+1}. 📅 {date} | **+{acquired} BTC** (Ort. {avg_price}) 🚀\n"
                
        bot.reply_to(message, summary, parse_mode="Markdown")

    def run_telegram_bot():
        print("Starting Telegram Bot listener thread...")
        while running:
            try:
                bot.infinity_polling()
            except Exception as e:
                print(f"Telegram Bot polling error: {e}")
                time.sleep(5)

# ----------------- MAIN RUNNER -----------------

def run_web_server():
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Flask Web Server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    print("Initializing MSTR SEC Filings Monitor Bot & Dashboard...")
    init_db()
    
    # Start Telegram Listener Thread
    if bot:
        telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        telegram_thread.start()
    else:
        print("WARNING: TELEGRAM_BOT_TOKEN is not configured. Telegram commands will not work.")
        
    # Start Flask Web Server Thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Keep connections warm during the ultra-critical window
    warmer_thread = threading.Thread(target=connection_warmer_loop, daemon=True)
    warmer_thread.start()

    # Backfill per-security ATM data + the weekly USD Reserve series in the background
    def _backfill_all():
        # Minutes of sequential fetch + full-document parse. Held out of the
        # fast window, and each half guarded so a failure in the first can no
        # longer silently skip the second.
        _wait_out_ultra_window("historical backfill")
        # Reconcile FIRST: both backfills below iterate purchase_history, so
        # they cannot enrich a week whose row does not exist yet.
        for name, fn in (("missing history", reconcile_missing_history),
                         ("ATM history", backfill_atm_history),
                         ("USD reserves", backfill_usd_reserves)):
            try:
                fn()
            except Exception as e:
                print(f"Backfill of {name} failed: {e}")
    backfill_thread = threading.Thread(target=_backfill_all, daemon=True)
    backfill_thread.start()

    # Quarterly cash reserves from SEC XBRL (startup + every 12 hours)
    cash_thread = threading.Thread(target=cash_refresh_loop, daemon=True)
    cash_thread.start()

    # Polymarket insider digest (weekdays at POLYMARKET_DIGEST_AT_TRT)
    if POLYMARKET_ENABLED:
        pm_thread = threading.Thread(target=polymarket_digest_loop, daemon=True)
        pm_thread.start()
    else:
        print("Polymarket insider digest disabled (POLYMARKET_INSIDERS not set).")

    # Run Polling Loop in main thread
    try:
        polling_loop()
    except KeyboardInterrupt:
        print("Shutting down bot...")
        running = False
