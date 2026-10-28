"""Adaptador de The Odds API v4. Solo biblioteca estandar."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from ..models import Quote

BASE = "https://api.the-odds-api.com/v4"
PROVIDER = "the_odds_api"


class SourceError(Exception):
    pass


@dataclass
class Usage:
    remaining: int | None
    used: int | None
    last: int | None


@dataclass
class Response:
    status: int
    usage: Usage
    body: bytes


def _int(h: dict, k: str):
    try:
        return int(h[k])
    except (KeyError, ValueError):
        return None


def _urllib_get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "surebet/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
    except urllib.error.URLError as e:
        raise SourceError(f"Sin conexion con la API: {e.reason}") from None


def estimate_cost(markets: list[str], regions: list[str]) -> int:
    """Coste de /odds segun la documentacion: mercados x regiones."""
    return len(markets) * len(regions)


def soccer_codes(sport_key: str, market: str) -> tuple[str, str]:
    """(market_code, period). Fuera del futbol el periodo queda UNKNOWN a proposito."""
    if sport_key.startswith("soccer_"):
        return {"h2h": ("FT_1X2", "REG_90"), "totals": ("FT_OU", "REG_90")}.get(market, (market.upper(), "UNKNOWN"))
    return market.upper(), "UNKNOWN"


def _outcome(market: str, name: str, home: str, away: str) -> str:
    if market == "h2h":
        if name == home:
            return "HOME"
        if name == away:
            return "AWAY"
        if name.lower() == "draw":
            return "DRAW"
    if market == "totals" and name.lower() in ("over", "under"):
        return name.upper()
    return f"UNMAPPED:{name}"


def parse_odds(body: bytes, captured_at: str, sport_key: str | None = None) -> list[Quote]:
    data = json.loads(body, parse_float=Decimal)
    quotes: list[Quote] = []
    for ev in data:
        sk = sport_key or ev.get("sport_key", "")
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                code, period = soccer_codes(ev.get("sport_key", sk), mk["key"])
                for oc in mk.get("outcomes", []):
                    line = str(oc["point"]) if oc.get("point") is not None else ""
                    quotes.append(Quote(
                        provider=PROVIDER, provider_event_id=ev["id"], sport_key=ev.get("sport_key", sk),
                        commence_time=ev["commence_time"], home_raw=ev.get("home_team", ""),
                        away_raw=ev.get("away_team", ""), book_key=bk["key"], market_code=code,
                        period=period, line=line,
                        outcome=_outcome(mk["key"], oc["name"], ev.get("home_team", ""), ev.get("away_team", "")),
                        odds=Decimal(str(oc["price"])),
                        book_updated_at=mk.get("last_update") or bk.get("last_update"),
                        captured_at=captured_at))
    return quotes


class TheOddsApi:
    def __init__(self, api_key: str, http=_urllib_get):
        self._key = api_key
        self._http = http

    def _scrub(self, text: str) -> str:
        return text.replace(self._key, "***")

    def _get(self, path: str, params: dict) -> Response:
        q = urllib.parse.urlencode({**params, "apiKey": self._key})
        try:
            status, headers, body = self._http(f"{BASE}{path}?{q}")
        except SourceError as e:
            raise SourceError(self._scrub(str(e))) from None
        usage = Usage(_int(headers, "x-requests-remaining"), _int(headers, "x-requests-used"),
                      _int(headers, "x-requests-last"))
        return Response(status, usage, body)

    def sports(self) -> Response:
        """No consume creditos segun la documentacion."""
        return self._get("/sports", {})

    def odds(self, sport_key: str, markets: list[str], regions: list[str]) -> Response:
        return self._get(f"/sports/{sport_key}/odds", {
            "regions": ",".join(regions), "markets": ",".join(markets),
            "oddsFormat": "decimal", "dateFormat": "iso"})


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
