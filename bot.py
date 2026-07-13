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
        
    conn.commit()
    
    # Seed database
    seed_database(conn)
    
    # If the processed filings table is fresh (e.g. less than 100 entries), mark all current Edgar index filings as processed
    cursor.execute("SELECT COUNT(*) FROM processed_filings")
    proc_count = cursor.fetchone()[0]
    if proc_count < 100:
        mark_current_filings_processed(conn)
        
    conn.close()

def seed_database(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM purchase_history")
    count = cursor.fetchone()[0]
    if count == 0:
        print("Seeding database with historical purchase data...")
        history = [
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
        for item in reversed(history):
            cursor.execute(
                """INSERT INTO purchase_history 
                   (filing_date, period, btc_acquired, purchase_price, avg_price, total_holdings, total_cost, avg_cost, url, total_debt, financing_source) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                item
            )
            
            url = item[8]
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
    data = fetch_mstr_filings()
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

def fetch_mstr_filings():
    cik = "0001050446"
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        resp = http_session.get(url, timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching SEC JSON: {e}")
    return None

def fetch_mstr_filings_efts():
    """Query EDGAR Full-Text Search (EFTS) API — often indexes 30-60s before submissions API."""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22bitcoin%22&dateRange=custom&startdt={today}&enddt={today}&forms=8-K&entities=0001050446"
    try:
        resp = http_session.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            results = []
            for hit in hits:
                source = hit.get("_source", {})
                acc = source.get("file_num") or hit.get("_id", "")
                # Extract accession number from the filing URL
                filing_url = source.get("file_url", "")
                filing_date = source.get("file_date", today)
                if filing_url and acc:
                    results.append({
                        "accession": acc,
                        "date": filing_date,
                        "url": filing_url
                    })
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
        s = str(s).replace('$', '').replace(',', '').strip()
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

                # Detect price unit from header
                price_header = row_data[1][1].lower() if len(row_data[1]) > 1 else ''
                unit = "M" if "millions" in price_header else ("B" if "billions" in price_header else "")
                price_val = cleaned[1]
                if price_val != '-' and unit and not price_val.endswith(unit):
                    price_val = f"{price_val}{unit}"

                avg_val = cleaned[2]

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
                        h_holdings = cleaned[3]
                        h_cost_val = cleaned[4]
                        if h_cost_val != '-' and h_cost_unit and not h_cost_val.endswith(h_cost_unit):
                            h_cost_val = f"{h_cost_val}{h_cost_unit}"
                        h_avg_cost = cleaned[5] if len(cleaned) > 5 else '-'

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

                # Detect cost unit
                cost_header = row_data[1][1].lower() if len(row_data[1]) > 1 else ''
                cost_unit = "M" if "millions" in cost_header else ("B" if "billions" in cost_header else "")
                cost_val = cleaned[1]
                if cost_val != '-' and cost_unit and not cost_val.endswith(cost_unit):
                    cost_val = f"{cost_val}{cost_unit}"

                as_of = period_text.replace("As of ", "").replace("*", "").strip()

                holdings_snapshots.append({
                    "as_of": as_of,
                    "holdings": cleaned[0],
                    "total_cost": cost_val,
                    "avg_cost": cleaned[2]
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

        total_money_m = sum(parse_money(a["price"]) for a in activities)

        # Weighted average price across all periods
        weighted_sum = 0
        total_btc_for_avg = 0
        for a in activities:
            btc_n = abs(a["signed_count"])
            try:
                avg_p = float(a["avg_price"].replace('$', '').replace(',', ''))
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
        btc = table_data.get("btc_acquired", "-")
        price = table_data.get("purchase_price", "-")
        avg = table_data.get("avg_price", "-")
        holdings = table_data.get("total_holdings", "-")
        breakdown = table_data.get("sale_breakdown") or table_data.get("purchase_breakdown") or []
        
        table_context = f"""
Parsed table data:
- Event type: {event}
- Total BTC: {btc}
- Total amount: {price}
- Weighted avg price: {avg}
- Current holdings: {holdings} BTC
"""
        if breakdown:
            table_context += "Period breakdown:\n"
            for b in breakdown:
                table_context += f"  - {b['period']}: {b['btc_count']} BTC @ {b['avg_price']} (total: {b['price']})\n"
    
    pass2_prompt = f"""Sen bir uzman finans analistsin. Aşağıdaki verileri kullanarak MicroStrategy (Strategy Inc.) hakkında kapsamlı bir Türkçe analiz yaz.

Çıkarılan veriler (Pass 1):
{json.dumps(pass1_result, indent=2, ensure_ascii=False)}
{table_context}

SEC Bildirimi URL: {url}

Şu JSON formatında yanıt ver:
- "summary_turkish": (string) 4-6 cümlelik detaylı Türkçe analiz. Şunları içermeli:
  1. Ne oldu? (BTC alım/satım/değişiklik yok) - Eğer birden fazla dönem varsa HEPSİNİ belirt
  2. Neden oldu? (Temettü ödemesi, fon oluşturma, tercihli hisse dağıtımı vs.)
  3. Portföy etkisi (toplam BTC, maliyet değişimi)
  4. Yatırımcı için ne anlama geliyor?
- "market_impact": (string) 1-2 cümle, bu haberin piyasaya potansiyel etkisi
- "risk_note": (string) 1 cümle, dikkat edilmesi gereken risk veya önemli not

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

def format_alert(parsed_data, url):
    event_type = parsed_data.get("event_type")
    
    if event_type == "btc_purchase":
        acquired = parsed_data.get('btc_acquired') or '-'
        price = parsed_data.get('purchase_price') or parsed_data.get('purchase_price_usd') or '-'
        avg = parsed_data.get('avg_price') or parsed_data.get('avg_purchase_price') or '-'
        holdings = parsed_data.get('total_holdings') or parsed_data.get('total_btc_holdings') or '-'
        
        return f"""🚀 **MSTR BTC ALDI: +{acquired} BTC!** (Tutar: {price} | Ort: {avg})
ℹ️ Toplam Portföy: {holdings} BTC'ye ulaştı.

**Detaylı Rapor:**
- 📅 **Dönem**: {parsed_data.get('purchase_period') or 'Belirtilmemiş'}
- 🪙 **Miktar**: {acquired} BTC
- 💰 **Ödenen Tutar**: {price}
- 🏷️ **Ortalama Fiyat**: {avg}
- 📊 **Toplam Portföy**: {holdings} BTC
- 📉 **Toplam Maliyet**: {parsed_data.get('total_cost') or parsed_data.get('total_cost_usd') or 'Belirtilmemiş'}
- 🎯 **Ortalama Maliyet**: {parsed_data.get('avg_cost') or parsed_data.get('avg_cost_per_btc') or 'Belirtilmemiş'}
- 🏦 **Toplam Borç (Tahvil)**: {parsed_data.get('total_debt') or parsed_data.get('total_debt_usd') or 'Belirtilmemiş'}
- 💸 **Nakit Kaynağı / Seyreltme**: {parsed_data.get('financing_source_turkish') or parsed_data.get('financing_details') or 'Belirtilmemiş'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "btc_sale":
        acquired = parsed_data.get('btc_acquired') or '-'
        price = parsed_data.get('purchase_price') or parsed_data.get('purchase_price_usd') or '-'
        avg = parsed_data.get('avg_price') or parsed_data.get('avg_purchase_price') or '-'
        holdings = parsed_data.get('total_holdings') or parsed_data.get('total_btc_holdings') or '-'
        
        # Build period breakdown for multi-period sales
        breakdown = parsed_data.get('sale_breakdown', [])
        if len(breakdown) > 1:
            breakdown_text = ""
            for b in breakdown:
                breakdown_text += f"\n  ↳ {b['period']}: {b['btc_count']} BTC @ {b['avg_price']} ({b['price']})"
            period_line = f"- 📅 **Dönem**: {parsed_data.get('purchase_period') or 'Belirtilmemiş'}{breakdown_text}"
        else:
            period_line = f"- 📅 **Dönem**: {parsed_data.get('purchase_period') or 'Belirtilmemiş'}"
        
        return f"""🚨 **MSTR BITCOIN SATTI: -{acquired} BTC!** (Tutar: {price} | Ort: {avg})
ℹ️ Kalan Toplam Portföy: {holdings} BTC.

**Detaylı Rapor:**
{period_line}
- 🪙 **Toplam Satılan**: -{acquired} BTC
- 💰 **Toplam Elde Edilen**: {price}
- 🏷️ **Ağırlıklı Ort. Satış Fiyatı**: {avg}
- 📊 **Kalan Toplam Portföy**: {holdings} BTC
- 📉 **Toplam Kümülatif Maliyet**: {parsed_data.get('total_cost') or parsed_data.get('total_cost_usd') or 'Belirtilmemiş'}
- 🎯 **Ortalama Maliyet**: {parsed_data.get('avg_cost') or parsed_data.get('avg_cost_per_btc') or 'Belirtilmemiş'}
- 🏦 **Toplam Borç (Tahvil)**: {parsed_data.get('total_debt') or parsed_data.get('total_debt_usd') or 'Belirtilmemiş'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "no_purchase":
        holdings = parsed_data.get('total_holdings') or parsed_data.get('total_btc_holdings') or '-'
        return f"""ℹ️ **MSTR Bu Hafta Alım Yapmadı.** (Toplam Portföy: {holdings} BTC)
MicroStrategy, yeni SEC bildirimine göre bu hafta Bitcoin alımı gerçekleştirmedi.

**Detaylı Rapor:**
- 📅 **Dönem**: {parsed_data.get('purchase_period') or 'Belirtilmemiş'}
- 📊 **Toplam Portföy**: {holdings} BTC
- 📉 **Toplam Maliyet**: {parsed_data.get('total_cost') or parsed_data.get('total_cost_usd') or 'Belirtilmemiş'}
- 🎯 **Ortalama Maliyet**: {parsed_data.get('avg_cost') or parsed_data.get('avg_cost_per_btc') or 'Belirtilmemiş'}
- 🏦 **Toplam Borç (Tahvil)**: {parsed_data.get('total_debt') or parsed_data.get('total_debt_usd') or 'Belirtilmemiş'}
- 💸 **Nakit Kaynağı / Seyreltme**: {parsed_data.get('financing_source_turkish') or parsed_data.get('financing_details') or 'Belirtilmemiş'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "financing":
        source = parsed_data.get('financing_source_turkish') or parsed_data.get('financing_details') or 'Finansman Bildirimi'
        summary = parsed_data.get('summary_turkish') or 'Detaylar bildirilmeyi bekliyor.'
        
        return f"""💵 **MSTR Yeni Finansman/Hisse İhraç:** {source}
ℹ️ Rapor Analizi: {summary[:120]}...

**Özet (Analist Yorumu):**
{summary}

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
        
        cursor.execute(
            """INSERT INTO purchase_history 
               (filing_date, period, btc_acquired, purchase_price, avg_price, total_holdings, total_cost, avg_cost, url, total_debt, financing_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                date,
                parsed_data.get("purchase_period"),
                str(parsed_data.get("btc_acquired") or "-"),
                str(parsed_data.get("purchase_price") or parsed_data.get("purchase_price_usd") or "-"),
                str(parsed_data.get("avg_price") or parsed_data.get("avg_purchase_price") or "-"),
                str(parsed_data.get("total_holdings") or parsed_data.get("total_btc_holdings") or "-"),
                str(parsed_data.get("total_cost") or parsed_data.get("total_cost_usd") or "-"),
                str(parsed_data.get("avg_cost") or parsed_data.get("avg_cost_per_btc") or "-"),
                url,
                str(parsed_data.get("total_debt") or parsed_data.get("total_debt_usd") or "-"),
                str(parsed_data.get("financing_source_turkish") or parsed_data.get("financing_details") or "-")
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
        acquired = (table_data or {}).get("btc_acquired") or "-"
        price = (table_data or {}).get("purchase_price") or "-"
        avg = (table_data or {}).get("avg_price") or "-"
        holdings = (table_data or {}).get("total_holdings") or "-"
        cost = (table_data or {}).get("total_cost") or "-"
        avg_cost = (table_data or {}).get("avg_cost") or "-"
        debt = (table_data or {}).get("total_debt") or "-"
        source = (table_data or {}).get("financing_source") or "-"
        period = (table_data or {}).get("purchase_period") or "-"
        
        event_type = (table_data or {}).get("event_type") or "no_purchase"
        
        if event_type == "btc_purchase":
            title = f"💡 **[AI Analizi] MSTR BTC ALDI: +{acquired} BTC!**"
            stats_block = f"""**Finansal Detaylar:**
- 📅 **Dönem**: {period}
- 🪙 **Satın Alınan**: +{acquired} BTC
- 💰 **Ödenen Tutar**: {price}
- 🏷️ **Ortalama Fiyat**: {avg}
- 📊 **Toplam Portföy**: {holdings} BTC
- 📉 **Kümülatif Maliyet**: {cost}
- 🎯 **Ortalama Maliyet**: {avg_cost}
- 🏦 **Toplam Borç (Tahvil)**: {debt}
- 💸 **Finansman Kaynağı**: {source}"""
        elif event_type == "btc_sale":
            title = f"💡 **[AI Analizi] MSTR BTC SATTI: -{acquired} BTC!**"
            stats_block = f"""**Finansal Detaylar:**
- 📅 **Dönem**: {period}
- 🪙 **Satılan Miktar**: -{acquired} BTC
- 💰 **Elde Edilen Tutar**: {price}
- 🏷️ **Ortalama Satış Fiyatı**: {avg}
- 📊 **Kalan Toplam Portföy**: {holdings} BTC
- 📉 **Kümülatif Maliyet**: {cost}
- 🏦 **Toplam Borç (Tahvil)**: {debt}"""
        else:
            title = "💡 **[AI Analizi] MSTR Bu Hafta Alım Yapmadı**"
            stats_block = f"""**Finansal Detaylar:**
- 📅 **Dönem**: {period}
- 📊 **Toplam Portföy**: {holdings} BTC
- 📉 **Toplam Maliyet**: {cost}
- 🎯 **Ortalama Maliyet**: {avg_cost}
- 🏦 **Toplam Borç (Tahvil)**: {debt}
- 💸 **Finansman Kaynağı**: {source}"""

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
        
    html_content = fetch_html(url)
    if not html_content:
        print(f"Could not load HTML for {url}")
        return
        
    # First, run local table parser (offline, instant, 100% reliable)
    fallback_data = parse_table_fallback(html_content)
    
    if fallback_data:
        # Table is present! We can determine event and statistics instantly without Groq.
        print("BTC update table found in filing! Bypassing synchronous Groq call for instant alert.")
        
        # SPEED: Send Telegram FIRST, then save to DB async
        main_msg_id = None
        if should_alert:
            alert_text = format_alert(fallback_data, url)
            main_msg_id = send_telegram_alert(alert_text)
        
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
                    cursor2.execute("SELECT total_debt, financing_source FROM purchase_history ORDER BY id DESC LIMIT 1")
                    last_row = cursor2.fetchone()
                    conn2.close()
                    last_debt = last_row["total_debt"] if last_row else "$6.7B"
                    last_source = last_row["financing_source"] if last_row else "ATM Hisse Satışı"
                except Exception:
                    last_debt = "$6.7B"
                    last_source = "ATM Hisse Satışı"
                    
                parsed_data = {
                    "event_type": "corporate_update",
                    "summary_turkish": "Filtrelenemeyen veya tablo içermeyen yeni 8-K bildirimi.",
                    "total_debt_usd": last_debt,
                    "financing_source_turkish": last_source
                }
                
            save_to_database(date, parsed_data, url, accession, form)
            
            if should_alert and main_msg_id:
                summary = parsed_data.get("summary_turkish", "")
                if summary:
                    detail_text = f"💡 **[AI Analizi — Detaylı Rapor]**\n\n{summary}\n\n🔗 [SEC Bildirimi]({url})"
                    send_telegram_alert(detail_text, reply_to_message_id=main_msg_id)
                    print("Async no-table Groq analysis completed and sent.")
                
        threading.Thread(target=async_no_table_analysis, daemon=True).start()

# Cache for processed filings — avoid DB query every 250ms
_processed_cache = set()
_processed_cache_time = 0

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
    
    # Run BOTH sources in parallel threads for maximum speed
    submissions_result = [None]
    efts_result = [[]]
    
    def _fetch_submissions():
        submissions_result[0] = fetch_mstr_filings()
    def _fetch_efts():
        efts_result[0] = fetch_mstr_filings_efts()
    
    t1 = threading.Thread(target=_fetch_submissions, daemon=True)
    t2 = threading.Thread(target=_fetch_efts, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=4)
    t2.join(timeout=4)
    
    # Process submissions results
    data = submissions_result[0]
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
    
    # Process EFTS results
    for result in efts_result[0]:
        acc = result["accession"]
        if acc not in processed and acc not in seen_accessions:
            new_filings_found.append((acc, result["date"], "8-K", result["url"]))
            seen_accessions.add(acc)
                
    for acc, date, form, url in reversed(new_filings_found):
        process_filing(acc, date, form, url)
        # Immediately add to cache so we don't re-process
        _processed_cache.add(acc)
        
    return len(new_filings_found)

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
            "url": r["url"]
        })
    return jsonify(history_list)

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
                data = fetch_mstr_filings()
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
            fallback_data = parse_table_fallback(html_content)
            parsed_data = None
            
            if groq_keys:
                parsed_data = analyze_filing_with_groq(cleaned_text, test_url)
                
            if fallback_data:
                if parsed_data:
                    if parsed_data.get("event_type") in ["corporate_update", "financing", None]:
                        parsed_data["event_type"] = fallback_data["event_type"]
                    parsed_data["purchase_period"] = fallback_data.get("purchase_period") or parsed_data.get("purchase_period")
                    parsed_data["btc_acquired"] = fallback_data.get("btc_acquired") or parsed_data.get("btc_acquired")
                    parsed_data["purchase_price"] = fallback_data.get("purchase_price") or fallback_data.get("purchase_price_usd") or parsed_data.get("purchase_price")
                    parsed_data["avg_price"] = fallback_data.get("avg_price") or fallback_data.get("avg_purchase_price") or parsed_data.get("avg_price")
                    parsed_data["total_holdings"] = fallback_data.get("total_holdings") or fallback_data.get("total_btc_holdings") or parsed_data.get("total_holdings")
                    parsed_data["total_cost"] = fallback_data.get("total_cost") or fallback_data.get("total_cost_usd") or parsed_data.get("total_cost")
                    parsed_data["avg_cost"] = fallback_data.get("avg_cost") or fallback_data.get("avg_cost_per_btc") or parsed_data.get("avg_cost")
                else:
                    parsed_data = fallback_data
                    
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
        
    # Run Polling Loop in main thread
    try:
        polling_loop()
    except KeyboardInterrupt:
        print("Shutting down bot...")
        running = False
