"""Datos sinteticos con verdad conocida: arbitrajes plantados y trampas.

No son datos reales. Sirven para probar el detector (H3) sin red ni claves.
"""
from __future__ import annotations

import csv
import random
from decimal import Decimal
from pathlib import Path

from .engine.arb_math import arbitrage_sum

FIELDS = ["event_id", "competition", "market_code", "period", "line", "outcome",
          "site", "odds", "captured_at", "scenario", "expected_arb"]

SITES = ["casa_a.es", "casa_b.es", "casa_c.es", "casa_d.es"]
OUTCOMES = {"FT_1X2": ["HOME", "DRAW", "AWAY"], "FT_OU": ["OVER", "UNDER"]}
SCENARIOS = ["arb", "no_arb", "trap_market", "trap_stale", "trap_same_site"]


def _fair_odds(rng: random.Random, outcomes: list[str]) -> dict[str, Decimal]:
    raw = [rng.uniform(0.15, 1.0) for _ in outcomes]
    tot = sum(raw)
    return {o: Decimal(tot / r) for o, r in zip(outcomes, raw)}


def _round_odds(x: Decimal) -> Decimal:
    return max(Decimal("1.05"), x.quantize(Decimal("0.01")))


def generate(seed: int = 7, n_events: int = 50) -> list[dict]:
    """Devuelve filas (dicts). Cada evento tiene un escenario y su respuesta esperada."""
    rng = random.Random(seed)
    rows: list[dict] = []
    for i in range(n_events):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        market = "FT_1X2" if i % 2 == 0 else "FT_OU"
        outs = OUTCOMES[market]
        fair = _fair_odds(rng, outs)
        period = "REG_90"
        line = "" if market == "FT_1X2" else "2.5"
        hour = 10 + (i % 8)
        t_new = f"2026-11-01T{hour:02d}:00:00Z"
        t_old = f"2026-11-01T{hour - 3 if hour > 3 else 0:02d}:00:00Z"
        # cuotas por casa: margen ~5% para todas...
        book = {s: {o: _round_odds(fair[o] * Decimal("0.95") * Decimal(str(rng.uniform(0.97, 1.03))))
                    for o in outs} for s in SITES}
        quotes = []  # (outcome, site, odds, captured_at, line, period)
        if scenario == "arb":
            # plantar: la mejor cuota de cada resultado sube en una casa distinta
            for k, o in enumerate(outs):
                site = SITES[k % len(SITES)]
                book[site][o] = _round_odds(fair[o] * Decimal("1.04"))
        for s in SITES:
            for o in outs:
                quotes.append([o, s, book[s][o], t_new, line, period])
        expected = False
        if scenario == "arb":
            best = {o: max(book[s][o] for s in SITES) for o in outs}
            expected = arbitrage_sum(list(best.values())) < 1
        elif scenario == "trap_market":
            # la cuota 'buena' del ultimo resultado es de otro periodo/linea: no comparable
            q = quotes[-1]
            q[2] = _round_odds(q[2] * Decimal("1.5"))
            q[4] = "3.5" if market == "FT_OU" else ""
            q[5] = "INCL_ET" if market == "FT_1X2" else period
        elif scenario == "trap_stale":
            q = quotes[0]
            q[2] = _round_odds(q[2] * Decimal("1.5"))
            q[3] = t_old
        elif scenario == "trap_same_site":
            # el 'arbitraje' solo existe combinando dos cuotas de la misma casa
            for q in quotes:
                if q[0] == outs[0] and q[1] == SITES[0]:
                    q[2] = _round_odds(fair[outs[0]] * Decimal("1.6"))
        for o, s, odds, cap, ln, per in quotes:
            rows.append({"event_id": f"EV{i:03d}", "competition": "SYN_LIGA", "market_code": market,
                         "period": per, "line": ln, "outcome": o, "site": s, "odds": str(odds),
                         "captured_at": cap, "scenario": scenario, "expected_arb": str(expected).lower()})
    return rows


def write_csv(path: str | Path, seed: int = 7, n_events: int = 50) -> int:
    rows = generate(seed, n_events)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)
