"""Una ronda de captura: presupuesto -> llamada -> respuesta original -> SQLite."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .providers import the_odds_api as t
from .quota import check_budget


@dataclass
class IngestSummary:
    status: int
    events: int
    quotes: int
    books: Counter
    with_update_time: int
    unmapped: int
    cost_estimated: int
    credits_last: int | None
    credits_remaining: int | None
    error: str | None = None


def run_ingest(api: t.TheOddsApi, conn, sport_key: str, markets: list[str], regions: list[str],
               raw_dir: str | Path = "data/raw", per_run_max: int = 4) -> IngestSummary:
    cost = t.estimate_cost(markets, regions)
    check_budget(conn, t.PROVIDER, cost, per_run_max)
    requested_at = t.utc_now()
    resp = api.odds(sport_key, markets, regions)
    params = json.dumps({"sport": sport_key, "markets": markets, "regions": regions})
    sha = hashlib.sha256(resp.body).hexdigest()
    day = requested_at[:10]
    rawp = Path(raw_dir) / day / t.PROVIDER
    rawp.mkdir(parents=True, exist_ok=True)
    raw_file = rawp / f"{requested_at.replace(':', '')}_{sport_key}_{sha[:8]}.json.gz"
    raw_file.write_bytes(gzip.compress(resp.body))
    err = None
    quotes: list = []
    if resp.status == 200:
        quotes = t.parse_odds(resp.body, requested_at, sport_key)
    else:
        err = f"HTTP {resp.status}: {resp.body[:200].decode('utf-8', 'replace')}"
    with conn:
        cur = conn.execute(
            "INSERT INTO poll(provider,endpoint,params,requested_at,http_status,credits_used,credits_remaining,"
            "credits_last,raw_path,raw_sha256,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (t.PROVIDER, f"/sports/{sport_key}/odds", params, requested_at, resp.status, resp.usage.used,
             resp.usage.remaining, resp.usage.last, str(raw_file), sha, err))
        pid = cur.lastrowid
        conn.executemany(
            "INSERT INTO odds_quote(poll_id,provider_event_id,sport_key,commence_time,home_raw,away_raw,book_key,"
            "market_code,period,line,outcome,odds,book_updated_at,captured_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(pid, q.provider_event_id, q.sport_key, q.commence_time, q.home_raw, q.away_raw, q.book_key,
              q.market_code, q.period, q.line, q.outcome, str(q.odds), q.book_updated_at, q.captured_at)
             for q in quotes])
    return IngestSummary(
        status=resp.status, events=len({q.provider_event_id for q in quotes}), quotes=len(quotes),
        books=Counter(q.book_key for q in quotes), with_update_time=sum(q.book_updated_at is not None for q in quotes),
        unmapped=sum(q.outcome.startswith("UNMAPPED") for q in quotes), cost_estimated=cost,
        credits_last=resp.usage.last, credits_remaining=resp.usage.remaining, error=err)
