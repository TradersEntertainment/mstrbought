"""Tests for the quarterly cash-reserves pipeline (SEC XBRL)."""
import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


class FakeResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    monkeypatch.setattr(bot, 'DB_PATH', db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE financial_metrics (
        metric TEXT, period_end TEXT, value REAL, form TEXT, filed TEXT,
        PRIMARY KEY (metric, period_end))""")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def xbrl_payload():
    with open(os.path.join(FIXTURES, 'xbrl_cash.json'), encoding='utf-8') as f:
        return json.load(f)


def mock_get(monkeypatch, resp):
    monkeypatch.setattr(bot.http_session, 'get',
                        lambda url, timeout=None, headers=None: resp)


def test_fetch_prefers_canonical_frame_and_latest_filed(monkeypatch, xbrl_payload):
    mock_get(monkeypatch, FakeResp(200, xbrl_payload))
    monkeypatch.setattr(bot, '_cash_shape_logged', True)

    quarters = bot.fetch_cash_reserves()
    by_end = {q['end']: q for q in quarters}

    assert list(by_end) == ['2025-09-30', '2025-12-31', '2026-03-31']  # chronological
    assert by_end['2025-09-30']['val'] == 610000000.0
    # frame'd (canonical) entry beats the earlier 10-K comparative
    assert by_end['2025-12-31']['val'] == 2450000000.0
    # no frame → most recently filed (the 10-Q/A restatement) wins
    assert by_end['2026-03-31']['val'] == 3150000000.0
    assert by_end['2026-03-31']['form'] == '10-Q/A'


def test_fetch_failure_returns_empty(monkeypatch):
    mock_get(monkeypatch, FakeResp(403))
    assert bot.fetch_cash_reserves() == []

    mock_get(monkeypatch, FakeResp(200, {"unexpected": "shape"}))
    assert bot.fetch_cash_reserves() == []


def test_refresh_upsert_is_idempotent(temp_db, monkeypatch, xbrl_payload):
    mock_get(monkeypatch, FakeResp(200, xbrl_payload))
    monkeypatch.setattr(bot, '_cash_shape_logged', True)

    assert bot.refresh_cash_reserves() == 3
    assert bot.refresh_cash_reserves() == 3

    conn = sqlite3.connect(temp_db)
    count = conn.execute("SELECT COUNT(*) FROM financial_metrics").fetchone()[0]
    conn.close()
    assert count == 3


def test_failed_refresh_preserves_existing_data(temp_db, monkeypatch, xbrl_payload):
    mock_get(monkeypatch, FakeResp(200, xbrl_payload))
    monkeypatch.setattr(bot, '_cash_shape_logged', True)
    bot.refresh_cash_reserves()

    mock_get(monkeypatch, FakeResp(500))
    assert bot.refresh_cash_reserves() == 0

    conn = sqlite3.connect(temp_db)
    count = conn.execute("SELECT COUNT(*) FROM financial_metrics").fetchone()[0]
    conn.close()
    assert count == 3


def test_api_cash_roundtrip(temp_db, monkeypatch, xbrl_payload):
    mock_get(monkeypatch, FakeResp(200, xbrl_payload))
    monkeypatch.setattr(bot, '_cash_shape_logged', True)
    bot.refresh_cash_reserves()

    client = bot.app.test_client()
    data = client.get('/api/cash').get_json()

    assert [d['period_end'] for d in data] == ['2025-09-30', '2025-12-31', '2026-03-31']
    assert data[-1]['value'] == 3150000000.0
    assert data[-1]['form'] == '10-Q/A'


def test_api_cash_empty_without_table(tmp_path, monkeypatch):
    # DB without the financial_metrics table → route degrades to []
    db_path = str(tmp_path / 'empty.db')
    monkeypatch.setattr(bot, 'DB_PATH', db_path)
    sqlite3.connect(db_path).close()

    client = bot.app.test_client()
    assert client.get('/api/cash').get_json() == []
