import requests
from bs4 import BeautifulSoup
import re

s = requests.Session()
s.headers.update({'User-Agent': 'Bot bot@test.com'})
r = s.get('https://www.sec.gov/Archives/edgar/data/1050446/000119312526276717/mstr-20260504.htm', timeout=10)
soup = BeautifulSoup(r.text, 'html.parser')
tables = soup.find_all('table')

for i, t in enumerate(tables):
    text = t.get_text()
    if 'BTC' in text or 'Holdings' in text:
        print(f"=== TABLE {i} ===")
        rows = t.find_all('tr')
        for j, row in enumerate(rows):
            cols = [col.get_text().strip().replace('\n', ' ') for col in row.find_all(['td', 'th'])]
            cols = [re.sub(r'\s+', ' ', c) for c in cols if c.strip()]
            if cols:
                print(f"  Row {j}: {cols}")
        print()
