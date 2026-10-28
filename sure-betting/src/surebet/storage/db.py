"""SQLite (H2): capturas anadidas, nunca sobrescritas. Esquema ampliable en hitos siguientes."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS poll (
  id INTEGER PRIMARY KEY, provider TEXT NOT NULL, endpoint TEXT NOT NULL, params TEXT,
  requested_at TEXT NOT NULL, http_status INTEGER, credits_used INTEGER,
  credits_remaining INTEGER, credits_last INTEGER, raw_path TEXT, raw_sha256 TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS odds_quote (
  id INTEGER PRIMARY KEY, poll_id INTEGER NOT NULL REFERENCES poll(id),
  provider_event_id TEXT NOT NULL, sport_key TEXT NOT NULL, commence_time TEXT NOT NULL,
  home_raw TEXT, away_raw TEXT, book_key TEXT NOT NULL, market_code TEXT NOT NULL,
  period TEXT NOT NULL, line TEXT NOT NULL DEFAULT '', outcome TEXT NOT NULL,
  odds TEXT NOT NULL, book_updated_at TEXT, captured_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_quote_event ON odds_quote(provider_event_id, market_code, captured_at);
"""


def connect(path: str | Path = "data/surebet.db") -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
