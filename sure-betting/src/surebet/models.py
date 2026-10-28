"""Modelos comunes. Las cuotas son Decimal exactos (nunca float)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Quote:
    provider: str
    provider_event_id: str
    sport_key: str
    commence_time: str
    home_raw: str
    away_raw: str
    book_key: str
    market_code: str      # FT_1X2, FT_OU, o H2H/TOTALS si el periodo no esta claro
    period: str           # REG_90, o UNKNOWN (bloquea la validacion)
    line: str             # "2.5" o ""
    outcome: str          # HOME, DRAW, AWAY, OVER, UNDER, o UNMAPPED:<nombre>
    odds: Decimal
    book_updated_at: str | None
    captured_at: str
