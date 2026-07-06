import sys
import os
sys.path.insert(0, os.getcwd())

import requests
from bs4 import BeautifulSoup
import re
import json

# Minimal stubs for testing
DB_PATH = "test_parse.db"

def get_db_connection():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Create stub DB
conn = get_db_connection()
conn.execute("CREATE TABLE IF NOT EXISTS purchase_history (id INTEGER PRIMARY KEY, total_debt TEXT, financing_source TEXT)")
conn.execute("INSERT OR IGNORE INTO purchase_history (id, total_debt, financing_source) VALUES (1, '$6.7B', 'ATM Hisse Satışı')")
conn.commit()
conn.close()

# Import the functions we need
from bot import clean_row_values

# Patch get_db_connection in bot module
import bot
bot.get_db_connection = get_db_connection

from bot import parse_table_fallback

# Fetch the filing
s = requests.Session()
s.headers.update({'User-Agent': 'Antigravity Bot antigravity@tradersentertainment.com'})

print("=== Testing July 6 filing (2 sale periods) ===")
r = s.get('https://www.sec.gov/Archives/edgar/data/1050446/000119312526295586/mstr-20260706.htm', timeout=10)
result = parse_table_fallback(r.text)
print(json.dumps(result, indent=2, default=str))

print("\n=== Testing June 22 filing (normal purchase) ===")
r2 = s.get('https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm', timeout=10)
result2 = parse_table_fallback(r2.text)
if result2:
    # Remove breakdown for cleaner output
    result2.pop('purchase_breakdown', None)
    result2.pop('sale_breakdown', None)
print(json.dumps(result2, indent=2, default=str))

print("\n=== Testing June 29 filing (no purchase) ===")
r3 = s.get('https://www.sec.gov/Archives/edgar/data/1050446/000119312526286871/mstr-20260629.htm', timeout=10)
result3 = parse_table_fallback(r3.text)
if result3:
    result3.pop('purchase_breakdown', None)
    result3.pop('sale_breakdown', None)
print(json.dumps(result3, indent=2, default=str))

# Clean up
os.remove("test_parse.db")
