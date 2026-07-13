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

# Optimization: critical poll interval is 0.25s (250ms) by default now
POLL_INTERVAL_NORMAL = float(os.getenv("POLL_INTERVAL_NORMAL", "300"))
POLL_INTERVAL_CRITICAL = float(os.getenv("POLL_INTERVAL_CRITICAL", "0.25"))

# Global states
current_mode = "Normal Mode"
last_checked_time = None
running = True

# Initialize Telegram Bot
bot = None
if TELEGRAM_BOT_TOKEN:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Initialize Flask App
app = Flask(__name__)

# Optimization: Keep-Alive Connection Pooling
http_session = requests.Session()
http_session.headers.update({
    'User-Agent': 'Antigravity Telegram Bot antigravity@tradersentertainment.com',
    'Accept-Encoding': 'gzip, deflate',
})

# ----------------- DB MANAGEMENT -----------------

def get_db_connection():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
    cursor = conn.cursor()
    print("Marking all existing SEC filings in EDGAR index as processed to prevent backfilling...")
    data = fetch_mstr_filings(use_conditional=False)
    if data:
        recent = data.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        accession_numbers = recent.get('accessionNumber', [])
        filing_dates = recent.get('filingDate', [])
        primary_docs = recent.get('primaryDocument', [])
        
        count_marked = 0
        for idx, form in enumerate(forms):
            if form == '8-K':
                acc_num = accession_numbers[idx]
                date = filing_dates[idx]
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
    soup = BeautifulSoup(html_content, 'html.parser')
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
        return (None, None) if return_state else None
    cik = "0001050446"
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {}
    if use_conditional and _submissions_etag:
        headers['If-None-Match'] = _submissions_etag
    if use_conditional and _submissions_last_modified:
        headers['If-Modified-Since'] = _submissions_last_modified
    try:
        resp = http_session.get(url, timeout=3, headers=headers)
        if resp.status_code == 200:
            _sec_clear_backoff('submissions')
            state = {
                'etag': resp.headers.get('ETag'),
                'last_modified': resp.headers.get('Last-Modified'),
            }
            data = resp.json()
            return (data, state) if return_state else data
        elif resp.status_code == 304:
            # Index unchanged since the last poll — nothing new
            pass
        else:
            _register_sec_throttle('submissions', resp.status_code)
    except Exception as e:
        print(f"Error fetching SEC JSON: {e}")
    return (None, None) if return_state else None

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
        return []
    today = datetime.now().strftime("%Y-%m-%d")
    url = (f"https://efts.sec.gov/LATEST/search-index?q=%22bitcoin%22"
           f"&forms=8-K&ciks=0001050446&startdt={today}&enddt={today}")
    try:
        resp = http_session.get(url, timeout=3)
        if resp.status_code != 200:
            _register_sec_throttle('efts', resp.status_code)
            return []
        _sec_clear_backoff('efts')
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
            # Legacy/unknown shape fallback
            filing_url = source.get("file_url", "")
            acc = source.get("adsh") or source.get("file_num") or hit_id
            if filing_url and acc:
                results.append({"accession": acc, "date": filing_date, "url": filing_url})
            elif hit_id:
                print(f"EFTS: unrecognized hit shape, _id={hit_id[:120]}")
        return results
    except Exception as e:
        print(f"EFTS query error (non-critical): {e}")
    return []

def fetch_html(url):
    try:
        resp = http_session.get(url, timeout=3)
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

        is_sold = 'BTC Sold' in header_text or 'BTC Sold' in table_text
        is_acquired = 'BTC Acquired' in header_text or 'BTC Acquired' in table_text
        is_holdings = 'Aggregate BTC Holdings' in header_text or 'Aggregate BTC Holdings' in table_text

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
                if is_holdings and len(cleaned) >= 6:
                    holdings_header_idx = next((h for h, hdr in enumerate(row_data[1]) if 'Aggregate BTC Holdings' in hdr), None)
                    if holdings_header_idx is not None:
                        h_cost_header = row_data[1][holdings_header_idx + 1].lower() if holdings_header_idx + 1 < len(row_data[1]) else ''
                        h_cost_unit = "M" if "millions" in h_cost_header else ("B" if "billions" in h_cost_header else "")
                        h_holdings = re.sub(r'\(\d+\)', '', cleaned[3]).strip() or '-'
                        h_cost_val = re.sub(r'\(\d+\)', '', cleaned[4]).strip() or '-'
                        if h_cost_val != '-' and h_cost_unit and not h_cost_val.endswith(h_cost_unit):
                            h_cost_val = f"{h_cost_val}{h_cost_unit}"
                        h_avg_cost = (re.sub(r'\(\d+\)', '', cleaned[5]).strip() or '-') if len(cleaned) > 5 else '-'

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

                # Detect cost unit; strip footnote markers from all values
                cost_header = row_data[1][1].lower() if len(row_data[1]) > 1 else ''
                cost_unit = "M" if "millions" in cost_header else ("B" if "billions" in cost_header else "")
                cost_val = re.sub(r'\(\d+\)', '', cleaned[1]).strip() or '-'
                if cost_val != '-' and cost_unit and not cost_val.endswith(cost_unit):
                    cost_val = f"{cost_val}{cost_unit}"

                as_of = period_text.replace("As of ", "").replace("*", "").strip()

                holdings_snapshots.append({
                    "as_of": as_of,
                    "holdings": re.sub(r'\(\d+\)', '', cleaned[0]).strip() or '-',
                    "total_cost": cost_val,
                    "avg_cost": re.sub(r'\(\d+\)', '', cleaned[2]).strip() or '-'
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
        if btc_net_signed > 0:
            event_type = "btc_purchase"
            inferred = True
        elif btc_net_signed < 0:
            event_type = "btc_sale"
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

            m = ATM_TICKER_RE.search(first)
            if m:
                ticker = m.group(1)
            elif 'Common Stock' in first:
                ticker = 'MSTR'
            else:
                # Description-continuation row (e.g. "10.00% Series A ...")
                continue

            cleaned = clean_row_values(row[1:])
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
            securities.append(entry)

        if not securities:
            continue

        sold = [s for s in securities if s["shares_sold_num"] > 0]
        if total_net_proceeds == "-" and sold:
            total_m = sum(s["net_proceeds_num_m"] for s in sold)
            if total_m >= 1000:
                total_net_proceeds = f"${total_m/1000:.2f}B"
            elif total_m > 0:
                total_net_proceeds = f"${total_m:.1f}M"

        return {
            "period": period,
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

def cash_refresh_loop():
    """Refresh the quarterly cash data at startup and every 12 hours."""
    while running:
        try:
            refresh_cash_reserves()
        except Exception as e:
            print(f"Cash refresh loop error: {e}")
        time.sleep(12 * 3600)

# ----------------- HISTORICAL ATM BACKFILL -----------------

ATM_SENTINEL_NO_TABLE = {"sold_any": False, "securities": [], "note": "no_atm_table"}
ATM_SENTINEL_NO_DOC = {"sold_any": False, "securities": [], "note": "no_fetchable_doc"}

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
        rows = conn.execute(
            "SELECT id, url, financing_source FROM purchase_history "
            "WHERE atm_sales IS NULL OR atm_sales = ''"
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
            atm = parse_atm_table(extract_filing_tables(html))
            if atm:
                atm_json = json.dumps(atm, ensure_ascii=False)
                filled += 1
                # Fill the badge only when the row has no description yet —
                # existing Turkish notes (e.g. convertible debt) carry info
                # the ATM table doesn't and must be preserved.
                if (row["financing_source"] or "-").strip() in ("-", "") and atm.get("sold_any"):
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

# ----------------- GROQ API INTEGRATION -----------------

# Groq API Keys Rotation Support
groq_keys = [k.strip() for k in os.getenv("GROQ_API_KEY", "").split(",") if k.strip()]
current_key_idx = 0

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
        "model": "llama-3.1-8b-instant",
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
        "model": "llama-3.1-8b-instant",
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
            else:
                print(f"Groq error {response.status_code}. Rotating...")
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
            for s in atm.get("securities", []):
                if s.get("shares_sold_num", 0) > 0:
                    table_context += (f"  - {s['ticker']}: {s.get('shares_sold', '-')} shares sold, "
                                      f"net proceeds {s.get('net_proceeds', '-')}, "
                                      f"remaining capacity {s.get('available', '-')}\n")
                else:
                    table_context += f"  - {s['ticker']}: no shares sold (remaining capacity {s.get('available', '-')})\n"
            table_context += f"  Total net proceeds: {atm.get('total_net_proceeds', '-')}\n"

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

# ----------------- TELEGRAM ALERTS -----------------

def send_telegram_alert(message_text, reply_to_message_id=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot not configured.")
        return None
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
        
    try:
        # Optimization: Use http_session for Keep-Alive connection reuse
        resp = http_session.post(url, json=payload, timeout=5)
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
                
            resp_plain = http_session.post(url, json=payload_plain, timeout=5)
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

def _atm_sold_lines(parsed_data):
    """Per-security ATM sale lines for Telegram (tickers only).

    Returns None when the filing had no ATM table, [] when the table exists
    but nothing was sold, otherwise one line per sold security.
    """
    atm = parsed_data.get("atm")
    if not atm:
        return None
    lines = []
    for s in atm.get("securities", []):
        if s.get("shares_sold_num", 0) > 0:
            lines.append(f"{s['ticker']}: {s.get('shares_sold', '-')} adet → **{s.get('net_proceeds', '-')}** net")
    return lines

def _atm_block(parsed_data, emoji="💸"):
    """Compact ATM section shared by the alert templates."""
    lines = _atm_sold_lines(parsed_data)
    if lines is None:
        source = parsed_data.get("financing_source_turkish") or parsed_data.get("financing_details")
        if source and source != "-":
            return f"{emoji} Finansman: {source}"
        return f"{emoji} ATM Satışı: Yok"
    if not lines:
        return f"{emoji} ATM Satışı: Yok"
    atm = parsed_data.get("atm") or {}
    unsold = [s["ticker"] for s in atm.get("securities", []) if s.get("shares_sold_num", 0) <= 0]
    block = f"{emoji} **ATM Satışı VAR:** " + "\n   ".join(lines)
    if unsold:
        block += f"\n   {' / '.join(unsold)}: satış yok"
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
{_atm_block(parsed_data)}
🏦 Toplam Borç (Tahvil): {debt}
📅 Dönem: {period}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "btc_sale":
        return f"""🚨 **MSTR BTC SATTI: {minus_amt} BTC!**{inferred_note} (Elde Edilen: {price} | Ort: {avg}){_breakdown_lines(parsed_data)}
📊 Kalan Portföy: {holdings} BTC | Maliyet: {total_cost} (Ort: {avg_cost})
{_atm_block(parsed_data)}
🏦 Toplam Borç (Tahvil): {debt}
📅 Dönem: {period}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "no_purchase":
        return f"""⏸️ **MSTR BTC ALMADI / SATMADI (0 BTC)** — Portföy: {holdings} BTC sabit{_breakdown_lines(parsed_data)}
{_atm_block(parsed_data, emoji="💵")}
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
        return f"""{source_block}
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

{stats_block}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""
        
        send_telegram_alert(analysis_text, reply_to_message_id=reply_to_id)
        print("Async Groq analysis completed and sent.")
    else:
        print("Async Groq analysis finished with no summary output.")

def process_filing(accession, date, form, url):
    print(f"Processing new filing: {accession} | Date: {date} | Form: {form}")
    
    # Anti-Spam Safeguard: Only send Telegram alerts for filings from today or yesterday
    should_alert = True
    try:
        filing_dt = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.now().date()
        if filing_dt < today - timedelta(days=1):
            print(f"Filing date {date} is older than yesterday. Suppressing Telegram alert to prevent spam.")
            should_alert = False
    except Exception as e:
        print(f"Error parsing filing date for spam check: {e}")
        should_alert = False
        
    t_start = time.time()
    html_content = fetch_html(url)
    if not html_content:
        print(f"Could not load HTML for {url}")
        return False
    t_fetch = time.time()

    # First, run the local table parsers (offline, instant, no LLM):
    # one HTML parse feeds both the BTC parser and the ATM parser.
    tables = extract_filing_tables(html_content)
    fallback_data = parse_btc_tables(tables)
    atm_data = parse_atm_table(tables)
    t_parse = time.time()

    if fallback_data:
        # Table is present! We can determine event and statistics instantly without Groq.
        print("BTC update table found in filing! Bypassing synchronous Groq call for instant alert.")

        if atm_data:
            fallback_data["atm"] = atm_data
            fallback_data["financing_details"] = financing_source_from_atm(atm_data)

        # SPEED: Send Telegram FIRST, then save to DB async
        main_msg_id = None
        if should_alert:
            alert_text = format_alert(fallback_data, url)
            main_msg_id = send_telegram_alert(alert_text)
            print(f"Alert latency: fetch {(t_fetch-t_start)*1000:.0f}ms | "
                  f"parse {(t_parse-t_fetch)*1000:.0f}ms | "
                  f"telegram {(time.time()-t_parse)*1000:.0f}ms")

        # Save to DB in background — don't block the alert pipeline
        threading.Thread(
            target=save_to_database,
            args=(date, fallback_data, url, accession, form),
            daemon=True
        ).start()

        # Run Groq in the background asynchronously for the interpretation summary
        if groq_keys and should_alert:
            cleaned_text = clean_html(html_content)
            threading.Thread(
                target=async_groq_analysis,
                args=(cleaned_text, url, main_msg_id, fallback_data),
                daemon=True
            ).start()
    elif atm_data and atm_data.get("sold_any"):
        # ATM-only filing: shares were sold but there is no BTC table.
        # Send an instant financing alert from the parsed ATM data; do NOT
        # add a purchase_history row (no holdings snapshot → would corrupt
        # the charts), only mark the filing as processed.
        print("ATM table found (no BTC table). Sending instant financing alert...")
        cleaned_text = clean_html(html_content)

        atm_parsed = {
            "event_type": "financing",
            "atm": atm_data,
            "financing_details": financing_source_from_atm(atm_data),
            "purchase_period": atm_data.get("period"),
        }

        main_msg_id = None
        if should_alert:
            main_msg_id = send_telegram_alert(format_alert(atm_parsed, url))

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT OR IGNORE INTO processed_filings (accession_number, filing_date, form, url) VALUES (?, ?, ?, ?)",
                (accession, date, form, url)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error marking ATM-only filing processed: {e}")

        if groq_keys and should_alert:
            threading.Thread(
                target=async_groq_analysis,
                args=(cleaned_text, url, main_msg_id, atm_parsed),
                daemon=True
            ).start()
    else:
        # No table found — but we MUST still send an immediate alert, then analyze async
        print("No BTC table found. Sending immediate alert, then running async Groq analysis...")
        cleaned_text = clean_html(html_content)

        main_msg_id = None
        if should_alert:
            # Send an immediate "new filing detected" alert — don't wait for Groq
            instant_alert = (
                f"📋 **MSTR Yeni SEC Bildirimi (Form 8-K)**\n\n"
                f"📅 Tarih: {date}\n"
                f"📄 Yeni bir Form 8-K bildirimi tespit edildi. İçerik analiz ediliyor...\n\n"
                f"🔗 [SEC Bildirimi]({url})"
            )
            main_msg_id = send_telegram_alert(instant_alert)
        
        # Run Groq analysis in background thread — reply with details when ready
        def async_no_table_analysis():
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

                # Debt carries forward (cumulative); financing_source must
                # describe THIS filing, so it is never carried forward.
                parsed_data = {
                    "event_type": "corporate_update",
                    "summary_turkish": "Filtrelenemeyen veya tablo içermeyen yeni 8-K bildirimi.",
                    "total_debt_usd": last_debt,
                    "financing_source_turkish": "-"
                }
                
            save_to_database(date, parsed_data, url, accession, form)
            
            if should_alert and main_msg_id:
                summary = parsed_data.get("summary_turkish", "")
                if summary:
                    detail_text = f"💡 **[AI Analizi — Detaylı Rapor]**\n\n{summary}\n\n🔗 [SEC Bildirimi]({url})"
                    send_telegram_alert(detail_text, reply_to_message_id=main_msg_id)
                    print("Async no-table Groq analysis completed and sent.")
                
        threading.Thread(target=async_no_table_analysis, daemon=True).start()

    return True

# Cache for processed filings — avoid DB query every 250ms
_processed_cache = set()
_processed_cache_time = 0

# EFTS polls are staggered to at most 1/s (see check_for_new_filings)
_last_efts_time = 0.0

def _refresh_processed_cache():
    """Refresh the processed filings cache from DB. Called sparingly."""
    global _processed_cache, _processed_cache_time
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT accession_number FROM processed_filings")
        _processed_cache = set(row['accession_number'] for row in cursor.fetchall())
        conn.close()
        _processed_cache_time = time.time()
    except Exception as e:
        print(f"Error refreshing processed cache: {e}")

def check_for_new_filings():
    global last_checked_time
    last_checked_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    # Refresh cache every 30 seconds (not every poll cycle)
    if time.time() - _processed_cache_time > 30:
        _refresh_processed_cache()
    
    processed = _processed_cache
    
    new_filings_found = []
    seen_accessions = set()

    # Run BOTH sources in parallel threads for maximum speed. The submissions
    # index is polled every tick (conditional GET makes unchanged responses
    # cheap 304s); EFTS is staggered to at most once per second to stay well
    # under the SEC's 10 req/s fair-use limit at 4 ticks/s.
    global _last_efts_time, _submissions_etag, _submissions_last_modified
    run_efts = time.time() - _last_efts_time >= 1.0

    # Single-cell tuple assignment keeps (data, state) atomic: a join timeout
    # must never observe the payload without its conditional-GET state or
    # vice versa.
    submissions_fetch = [(None, None)]
    efts_result = [[]]

    def _fetch_submissions():
        submissions_fetch[0] = fetch_mstr_filings(return_state=True)
    def _fetch_efts():
        efts_result[0] = fetch_mstr_filings_efts()

    t1 = threading.Thread(target=_fetch_submissions, daemon=True)
    t1.start()
    t2 = None
    if run_efts:
        _last_efts_time = time.time()
        t2 = threading.Thread(target=_fetch_efts, daemon=True)
        t2.start()
    t1.join(timeout=4)
    if t2:
        t2.join(timeout=4)
    
    # Process submissions results
    data, sub_state = submissions_fetch[0]
    if data:
        recent = data.get('filings', {}).get('recent', {})
        if recent:
            forms = recent.get('form', [])
            accession_numbers = recent.get('accessionNumber', [])
            filing_dates = recent.get('filingDate', [])
            primary_docs = recent.get('primaryDocument', [])

            for idx, form in enumerate(forms):
                if form == '8-K':
                    acc_num = accession_numbers[idx]
                    if acc_num not in processed and acc_num not in seen_accessions:
                        filing_date = filing_dates[idx]
                        doc = primary_docs[idx]
                        acc_num_no_dash = acc_num.replace('-', '')
                        url = f"https://www.sec.gov/Archives/edgar/data/1050446/{acc_num_no_dash}/{doc}"
                        new_filings_found.append((acc_num, filing_date, form, url))
                        seen_accessions.add(acc_num)
        # The payload has been scanned — only NOW is it safe to remember the
        # validators. A timed-out fetch leaves data None, nothing is
        # committed, and the next poll re-fetches with the OLD ETag.
        _commit_submissions_state(sub_state)

    # Process EFTS results
    for result in efts_result[0]:
        acc = result["accession"]
        if acc not in processed and acc not in seen_accessions:
            new_filings_found.append((acc, result["date"], "8-K", result["url"]))
            seen_accessions.add(acc)
                
    for acc, date, form, url in reversed(new_filings_found):
        ok = False
        try:
            ok = process_filing(acc, date, form, url)
        except Exception as e:
            print(f"Error processing filing {acc}: {e}")
        if ok:
            # Immediately add to cache so we don't re-process
            _processed_cache.add(acc)
        else:
            # Invalidate the conditional-GET state: without this, the next
            # polls would get 304 (index unchanged) and never retry this
            # filing until the index changes again.
            _submissions_etag = None
            _submissions_last_modified = None
            print(f"Filing {acc} not fully processed — will retry on the next poll.")

    return len(new_filings_found)

def connection_warmer_loop():
    """Keep TCP/TLS connections hot during the ultra-critical window.

    A tiny request every ~50s to www.sec.gov (the Archives host used by
    fetch_html) and to the Telegram API keeps the pooled connections open,
    so the first real fetch/alert skips both handshakes (~0.02 req/s cost).
    """
    trt_tz = timezone(timedelta(hours=3))
    while running:
        try:
            now_trt = datetime.now(timezone.utc).astimezone(trt_tz)
            in_window = now_trt.weekday() < 5 and (
                (now_trt.hour == 14 and now_trt.minute >= 30) or
                (now_trt.hour == 15 and now_trt.minute <= 15)
            )
            if in_window:
                try:
                    http_session.get("https://www.sec.gov/robots.txt", timeout=3)
                except Exception:
                    pass
                if TELEGRAM_BOT_TOKEN:
                    try:
                        http_session.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe", timeout=3)
                    except Exception:
                        pass
                time.sleep(50)
            else:
                time.sleep(30)
        except Exception:
            time.sleep(30)

def polling_loop():
    global current_mode, running
    print("Starting SEC Polling Loop...")
    
    trt_tz = timezone(timedelta(hours=3))
    
    while running:
        try:
            now_trt = datetime.now(timezone.utc).astimezone(trt_tz)
            
            is_weekday = now_trt.weekday() < 5
            
            # Ultra-critical: 14:30 - 15:15 TRT (sub-second polling)
            is_ultra_critical = (
                (now_trt.hour == 14 and now_trt.minute >= 30) or
                (now_trt.hour == 15 and now_trt.minute <= 15)
            )
            # Extended fast: 14:00-14:30 and 15:15-16:00 TRT (15s polling)
            is_extended_fast = (
                (now_trt.hour == 14 and now_trt.minute < 30) or
                (now_trt.hour == 15 and now_trt.minute > 15)
            )
            
            if is_weekday and is_ultra_critical:
                if current_mode != "Ultra High-Speed Mode":
                    print(f"Entering ULTRA HIGH-SPEED POLLING MODE at {now_trt.strftime('%H:%M:%S')} TRT")
                    current_mode = "Ultra High-Speed Mode"
                interval = POLL_INTERVAL_CRITICAL
            elif is_weekday and is_extended_fast:
                if current_mode != "Extended Fast Mode":
                    print(f"Entering EXTENDED FAST POLLING MODE at {now_trt.strftime('%H:%M:%S')} TRT")
                    current_mode = "Extended Fast Mode"
                interval = 15.0
            else:
                if current_mode != "Normal Mode":
                    print(f"Entering NORMAL POLLING MODE at {now_trt.strftime('%H:%M:%S')} TRT")
                    current_mode = "Normal Mode"
                interval = POLL_INTERVAL_NORMAL
                
            check_for_new_filings()
            
        except Exception as e:
            print(f"Exception in polling loop: {e}")
            interval = POLL_INTERVAL_NORMAL
            
        time.sleep(interval)

# ----------------- FLASK WEB ROUTES & APIS -----------------

@app.route('/')
def dashboard_index():
    return render_template('index.html')

@app.route('/api/status')
def get_bot_status():
    return jsonify({
        "mode": current_mode,
        "last_checked": last_checked_time,
        "db_path": DB_PATH
    })

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

@app.route('/api/trigger', methods=['POST'])
def force_trigger():
    if ADMIN_PASSWORD:
        req_pass = request.args.get("password") or request.headers.get("X-Admin-Password")
        if req_pass != ADMIN_PASSWORD:
            return jsonify({"status": "error", "message": "Yetkisiz işlem: Şifre hatalı."}), 401
            
    trigger_type = request.args.get("type", "poll")
    
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
            if fallback_data and test_atm:
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
            elif test_atm and test_atm.get("sold_any") and not parsed_data:
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
            "/test_integration - Son BTC alım raporunu (22 Haziran) okuyup analiz testi yapar.\n"
            "/status - Botun çalışma durumunu ve anlık modunu gösterir.",
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['status'])
    def send_status(message):
        trt_tz = timezone(timedelta(hours=3))
        now_trt = datetime.now(timezone.utc).astimezone(trt_tz)
        
        bot.reply_to(
            message,
            f"🤖 **Bot Durum Raporu**\n\n"
            f"🟢 **Durum**: Çalışıyor\n"
            f"⚡ **Aktif Mod**: {current_mode}\n"
            f"⏰ **Sunucu Saati (TR)**: {now_trt.strftime('%d.%m.%Y %H:%M:%S')}\n"
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

    # Backfill per-security ATM data for historical rows in the background
    backfill_thread = threading.Thread(target=backfill_atm_history, daemon=True)
    backfill_thread.start()

    # Quarterly cash reserves from SEC XBRL (startup + every 12 hours)
    cash_thread = threading.Thread(target=cash_refresh_loop, daemon=True)
    cash_thread.start()

    # Run Polling Loop in main thread
    try:
        polling_loop()
    except KeyboardInterrupt:
        print("Shutting down bot...")
        running = False
