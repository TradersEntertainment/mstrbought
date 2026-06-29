import os
import time
import json
import sqlite3
import threading
import urllib.request
import re
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
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

# Optimization: critical poll interval is 1s by default now
POLL_INTERVAL_NORMAL = int(os.getenv("POLL_INTERVAL_NORMAL", "300"))
POLL_INTERVAL_CRITICAL = int(os.getenv("POLL_INTERVAL_CRITICAL", "1"))

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
    
    # Self-healing: Check if database contains corrupt data (such as NaN or '-' in total_holdings)
    should_reset = False
    try:
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
            ("2026-06-22", "June 15, 2026 to June 21, 2026", "520", "$34.9M", "$67,068", "847,363", "$64.10B", "$75,651", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm", "$6.7B", "ATM Hisse Satışı"),
            ("2026-06-15", "June 8, 2026 to June 14, 2026", "1,587", "$100.0M", "$63,024", "846,842", "$64.07B", "$75,656", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526270311/mstr-20260504.htm", "$6.7B", "ATM Hisse Satışı"),
            ("2026-06-08", "June 1, 2026 to June 7, 2026", "1,550", "$101.3M", "$65,332", "845,256", "$63.97B", "$75,680", "https://www.sec.gov/Archives/edgar/data/1050446/000119312526260709/mstr-20260504.htm", "$6.7B", "ATM Hisse Satışı"),
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
    cursor.execute("SELECT COUNT(*) FROM processed_filings")
    count = cursor.fetchone()[0]
    
    if count <= 16:
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
        resp = http_session.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching SEC JSON: {e}")
    return None

def fetch_html(url):
    try:
        resp = http_session.get(url, timeout=5)
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

def parse_table_fallback(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    
    for table in tables:
        text = table.get_text()
        if "BTC Acquired" in text and ("BTC Holdings" in text or "Aggregate BTC Holdings" in text):
            rows = table.find_all('tr')
            row_data = []
            for r in rows:
                cols = [col.get_text().strip().replace('\n', ' ') for col in r.find_all(['td', 'th'])]
                cols = [re.sub(r'\s+', ' ', c) for c in cols if c.strip()]
                if cols:
                    row_data.append(cols)
            
            if len(row_data) >= 3:
                try:
                    period_text = row_data[0][0].replace("During Period ", "").strip()
                    headers = row_data[1]
                    raw_values = row_data[2]
                    cleaned_values = clean_row_values(raw_values)
                    
                    if len(cleaned_values) < 6:
                        cleaned_values += ['-'] * (6 - len(cleaned_values))
                        
                    btc_acquired = cleaned_values[0]
                    
                    # Purchase Price
                    price_header = headers[1].lower()
                    unit = "M" if "millions" in price_header else ("B" if "billions" in price_header else "")
                    purch_price = cleaned_values[1]
                    if purch_price != '-' and unit and not purch_price.endswith(unit):
                        purch_price = f"{purch_price}{unit}"
                        
                    avg_price = cleaned_values[2]
                    total_holdings = cleaned_values[3]
                    
                    # Total Cost
                    total_cost_header = headers[4].lower()
                    total_cost_unit = "M" if "millions" in total_cost_header else ("B" if "billions" in total_cost_header else "")
                    total_cost = cleaned_values[4]
                    if total_cost != '-' and total_cost_unit and not total_cost.endswith(total_cost_unit):
                        total_cost = f"{total_cost}{total_cost_unit}"
                        
                    avg_cost = cleaned_values[5]
                    
                    # Try to fetch last known debt & financing as fallback value
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT total_debt, financing_source FROM purchase_history ORDER BY id DESC LIMIT 1")
                    last_row = cursor.fetchone()
                    conn.close()
                    last_debt = last_row["total_debt"] if last_row else "$6.7B"
                    last_source = last_row["financing_source"] if last_row else "ATM Hisse Satışı"
                    
                    return {
                        "event_type": "btc_purchase" if btc_acquired != '0' and btc_acquired != '-' else "no_purchase",
                        "purchase_period": period_text,
                        "btc_acquired": btc_acquired,
                        "purchase_price": purch_price,
                        "avg_price": avg_price,
                        "total_holdings": total_holdings,
                        "total_cost": total_cost,
                        "avg_cost": avg_cost,
                        "total_debt": last_debt,
                        "financing_details": last_source,
                        "summary_turkish": None
                    }
                except Exception as e:
                    print(f"Fallback table parsing exception: {e}")
                    
    return None

# ----------------- GROQ API INTEGRATION -----------------

def analyze_filing_with_groq(text, url):
    if not GROQ_API_KEY:
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

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Optimization: Using llama-3.1-8b-instant which operates at 800+ tokens/sec
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    try:
        response = http_session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            return json.loads(content)
        else:
            print(f"Groq API error status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Groq API exception: {e}")
        return None

# ----------------- TELEGRAM ALERTS -----------------

def send_telegram_alert(message_text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot not configured.")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        # Optimization: Use http_session for Keep-Alive connection reuse
        resp = http_session.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            return True
        else:
            print(f"Telegram Markdown send failed (Status {resp.status_code}): {resp.text}. Retrying as plain text...")
            # Fallback: strip markdown formatting to guarantee delivery
            plain_text = message_text.replace("**", "").replace("`", "").replace("🔗 ", "").replace("[", "").replace("]", "")
            plain_text = re.sub(r'\((https?://.*?)\)', r': \1', plain_text)
            
            payload_plain = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": plain_text
            }
            resp_plain = http_session.post(url, json=payload_plain, timeout=5)
            if resp_plain.status_code == 200:
                print("Fallback plain text send succeeded.")
                return True
            else:
                print(f"Telegram fallback send failed (Status {resp_plain.status_code}): {resp_plain.text}")
                return False
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")
        return False

def format_alert(parsed_data, url):
    event_type = parsed_data.get("event_type")
    
    if event_type == "btc_purchase":
        return f"""🚀 **MSTR BTC ALDI!**

MicroStrategy, yeni SEC bildirimine göre Bitcoin alımı gerçekleştirdi.

**Detaylar:**
- 📅 **Dönem**: {parsed_data.get('purchase_period') or 'Belirtilmemiş'}
- 🪙 **Miktar**: {parsed_data.get('btc_acquired')} BTC
- 💰 **Ödenen Tutar**: {parsed_data.get('purchase_price') or parsed_data.get('purchase_price_usd') or 'Belirtilmemiş'}
- 🏷️ **Ortalama Fiyat**: {parsed_data.get('avg_price') or parsed_data.get('avg_purchase_price') or 'Belirtilmemiş'}
- 📊 **Toplam Portföy**: {parsed_data.get('total_holdings') or parsed_data.get('total_btc_holdings') or 'Belirtilmemiş'} BTC
- 📉 **Toplam Maliyet**: {parsed_data.get('total_cost') or parsed_data.get('total_cost_usd') or 'Belirtilmemiş'}
- 🎯 **Ortalama Maliyet**: {parsed_data.get('avg_cost') or parsed_data.get('avg_cost_per_btc') or 'Belirtilmemiş'}
- 🏦 **Toplam Borç (Tahvil)**: {parsed_data.get('total_debt') or parsed_data.get('total_debt_usd') or 'Belirtilmemiş'}
- 💸 **Nakit Kaynağı / Seyreltme**: {parsed_data.get('financing_source_turkish') or parsed_data.get('financing_details') or 'Belirtilmemiş'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "no_purchase":
        return f"""ℹ️ **MSTR Bu Hafta Alım Yapmadı**

MicroStrategy, yeni SEC bildirimine göre bu hafta Bitcoin alımı gerçekleştirmedi.

**Detaylar:**
- 📅 **Dönem**: {parsed_data.get('purchase_period') or 'Belirtilmemiş'}
- 📊 **Toplam Portföy**: {parsed_data.get('total_holdings') or parsed_data.get('total_btc_holdings') or 'Belirtilmemiş'} BTC
- 📉 **Toplam Maliyet**: {parsed_data.get('total_cost') or parsed_data.get('total_cost_usd') or 'Belirtilmemiş'}
- 🎯 **Ortalama Maliyet**: {parsed_data.get('avg_cost') or parsed_data.get('avg_cost_per_btc') or 'Belirtilmemiş'}
- 🏦 **Toplam Borç (Tahvil)**: {parsed_data.get('total_debt') or parsed_data.get('total_debt_usd') or 'Belirtilmemiş'}
- 💸 **Nakit Kaynağı / Seyreltme**: {parsed_data.get('financing_source_turkish') or parsed_data.get('financing_details') or 'Belirtilmemiş'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "financing":
        return f"""💵 **MSTR Yeni Finansman / Hisse İhraç Bildirimi**

MicroStrategy, yeni bir finansman veya hisse satışı (ATM / Tahvil / STRC / STRF Preferred Stock vb.) bildirimi yayınladı.

**Özet (Analist Yorumu):**
{parsed_data.get('summary_turkish') or parsed_data.get('financing_details') or 'Ayrıntı belirtilmemiş.'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    elif event_type == "corporate_update":
        return f"""ℹ️ **MSTR Kurumsal Güncelleme Yayınladı**

MicroStrategy (Strategy Inc.) yeni bir SEC kurumsal güncelleme bildirimi yayınladı.

**Detaylar:**
{parsed_data.get('summary_turkish') or 'Rutin kurumsal güncelleme.'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

    else:
        return f"""ℹ️ **MSTR Yeni SEC Bildirimi (Form 8-K)**

MicroStrategy yeni bir Form 8-K bildiriminde bulundu.

**Özet:**
{parsed_data.get('summary_turkish') or 'Detaylar için bildirimi inceleyin.'}

🔗 [Resmi SEC Bildirimi (Form 8-K)]({url})"""

# ----------------- MONITORS ENGINE -----------------

def process_filing(accession, date, form, url):
    print(f"Processing new filing: {accession} | Date: {date} | Form: {form}")
    
    # Optimization: Instant notification on filing detection
    preliminary_text = f"⚠️ **MSTR Yeni SEC Bildirimi (Form 8-K) Yayınlandı!**\n\nFiling analiz ediliyor...\n🔗 [Filing Linki]({url})"
    send_telegram_alert(preliminary_text)
    
    html_content = fetch_html(url)
    if not html_content:
        print(f"Could not load HTML for {url}")
        return
        
    cleaned_text = clean_html(html_content)
    parsed_data = None
    
    if GROQ_API_KEY:
        print("Calling Groq API for analysis...")
        parsed_data = analyze_filing_with_groq(cleaned_text, url)
        if parsed_data:
            print("Groq analysis succeeded:", parsed_data)
            
    if not parsed_data:
        print("Falling back to local HTML parsing...")
        parsed_data = parse_table_fallback(html_content)
        if parsed_data:
            print("Local HTML parser succeeded:", parsed_data)
            
    if not parsed_data:
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
            
        parsed_data = {
            "event_type": "corporate_update",
            "summary_turkish": "Filtrelenemeyen veya tablo içermeyen yeni 8-K bildirimi.",
            "total_debt_usd": last_debt,
            "financing_source_turkish": last_source
        }
        
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
            str(parsed_data.get("btc_acquired") or parsed_data.get("btc_acquired_count") or "-"),
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
    
    alert_text = format_alert(parsed_data, url)
    send_telegram_alert(alert_text)

def check_for_new_filings():
    global last_checked_time
    last_checked_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    data = fetch_mstr_filings()
    if not data:
        return 0
        
    recent = data.get('filings', {}).get('recent', {})
    if not recent:
        return 0
        
    forms = recent.get('form', [])
    accession_numbers = recent.get('accessionNumber', [])
    filing_dates = recent.get('filingDate', [])
    primary_docs = recent.get('primaryDocument', [])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT accession_number FROM processed_filings")
    processed = set(row['accession_number'] for row in cursor.fetchall())
    conn.close()
    
    new_filings_found = []
    for idx, form in enumerate(forms):
        if form == '8-K':
            acc_num = accession_numbers[idx]
            if acc_num not in processed:
                filing_date = filing_dates[idx]
                doc = primary_docs[idx]
                acc_num_no_dash = acc_num.replace('-', '')
                url = f"https://www.sec.gov/Archives/edgar/data/1050446/{acc_num_no_dash}/{doc}"
                new_filings_found.append((acc_num, filing_date, form, url))
                
    for acc, date, form, url in reversed(new_filings_found):
        process_filing(acc, date, form, url)
        time.sleep(1)
        
    return len(new_filings_found)

def polling_loop():
    global current_mode, running
    print("Starting SEC Polling Loop...")
    
    trt_tz = timezone(timedelta(hours=3))
    
    while running:
        try:
            now_trt = datetime.now(timezone.utc).astimezone(trt_tz)
            
            is_weekday = now_trt.weekday() < 5
            is_critical_time = (
                (now_trt.hour == 14 and now_trt.minute >= 59) or
                (now_trt.hour == 15 and now_trt.minute <= 10)
            )
            
            if is_weekday and is_critical_time:
                if current_mode != "High-Speed Mode":
                    print(f"Entering HIGH-SPEED POLLING MODE at {now_trt.strftime('%H:%M:%S')} TRT")
                    current_mode = "High-Speed Mode"
                interval = POLL_INTERVAL_CRITICAL
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
        test_url = "https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm"
        try:
            # Send immediate alert that we started testing
            send_telegram_alert("🧪 **[TEST BİLDİRİMİ]** MSTR SEC alım raporu testi başlatıldı. Analiz ediliyor...")
            
            html_content = fetch_html(test_url)
            if not html_content:
                return jsonify({"status": "error", "message": "Test HTML'i SEC EDGAR'dan çekilemedi."}), 500
                
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
