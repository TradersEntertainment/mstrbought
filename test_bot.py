import os
import sqlite3
from bot import init_db, DB_PATH, get_db_connection

def test_db_seeding():
    print(f"Testing DB initialization at: {DB_PATH}")
    # Remove existing local DB if it exists to ensure a fresh test of seeding
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Removed old database file.")
        except Exception as e:
            print(f"Could not remove old database: {e}")
            
    init_db()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM purchase_history")
    history_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM processed_filings")
    processed_count = cursor.fetchone()[0]
    
    print(f"Seeded records - Purchase History: {history_count}, Processed Filings: {processed_count}")
    
    cursor.execute("SELECT * FROM purchase_history ORDER BY id DESC LIMIT 3")
    rows = cursor.fetchall()
    
    print("\nMost recent 3 seeded purchases:")
    for r in rows:
        print(f"ID: {r['id']} | Date: {r['filing_date']} | BTC: {r['btc_acquired']} | Avg: {r['avg_price']} | Total Holdings: {r['total_holdings']} | URL: {r['url']}")
        
    conn.close()
    
    if history_count == 18 and processed_count >= 18:
        print("\nSUCCESS: DB initialization and seeding verification passed!")
    else:
        print(f"\nFAILURE: Seeding count mismatch (History: {history_count}, Processed: {processed_count}).")

if __name__ == '__main__':
    test_db_seeding()
