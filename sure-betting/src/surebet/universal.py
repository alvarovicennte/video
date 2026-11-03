"""Escaner universal: cualquier deporte, cualquier combinacion de mercados.

Para cada evento junta todas las cuotas disponibles (de todas las casas y mercados),
se queda con la mejor de cada apuesta equivalente y resuelve el programa lineal exacto
de engine/lp.py sobre los escenarios del deporte. Asi encuentra:
- arbitrajes clasicos (una cuota por resultado),
- arbitrajes entre mercados (p. ej. "empate no apuesta" + "doble oportunidad"),
- arbitrajes con lineas enteras o de cuarto (devoluciones parciales),
- casa contra exchange (lay),
y solo da por bueno lo que gana o empata en TODOS los escenarios, incluidas las
retiradas con las reglas reales de cada casa.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from fractions import Fraction as F
from itertools import product
from pathlib import Path

from .engine.lp import best_cover
from .engine.scenarios import Bet, build_matrix, compact

SCORE_SPORTS = {"football", "futbol", "basketball", "baloncesto", "hockey", "handball", "balonmano"}
RETIREMENT_SPORTS = {"tennis", "tenis", "table_tennis", "tenis_de_mesa", "badminton", "padel"}
CSV_FIELDS = ["event_id", "event_name", "sport", "period", "market", "line", "outcome",
              "side", "book", "odds", "commission", "rule", "captured_at"]


def frac(s: str | None) -> F | None:
    if s is None or str(s).strip() == "":
        return None
    return F(str(s).strip().replace(",", "."))


def model_for(sport: str) -> str:
    return "score" if sport.lower() in SCORE_SPORTS else "winner"


@dataclass
class Opportunity:
    event_id: str
    event_name: str
    sport: str
    period: str
    value: F
    legs: list[tuple[Bet, F]]          # (apuesta, fraccion de la banca)
    markets_used: int
    robust: bool                       # False = solo funciona ignorando retiradas
    void_states: list = field(default_factory=list)

    @property
    def ret(self) -> F:
        return 1 / self.value - 1


def _group_key(b: Bet):
    if b.market == "AH":
        return ("AH", b.line if b.outcome == "HOME" else -b.line)
    if b.market == "TOTAL":
        return ("TOTAL", b.line)
    return (b.market,)


def _dominance(bets: list[Bet]) -> list[Bet]:
    best: dict = {}
    for b in bets:
        k = (b.market, b.line, b.outcome, b.side, b.rule)
        if k not in best or b.win_multiplier > best[k].win_multiplier:
            best[k] = b
    return list(best.values())


def _solve(model: str, bets: list[Bet], retirements: bool):
    states, R = build_matrix(model, bets, retirements)
    st, Rc, void_all = compact(states, R)
    if not st:
        return None
    cov = best_cover(Rc)
    return (cov, void_all) if cov else None


def analyse_event(model: str, bets: list[Bet], retirements: bool) -> tuple | None:
    """Mejor cobertura del evento: probando todos los mercados juntos y cada grupo por separado."""
    bets = _dominance(bets)
    groups: dict = {}
    for b in bets:
        groups.setdefault(_group_key(b), []).append(b)
    candidates = [bets] + [g for g in groups.values() if len(g) < len(bets)]
    best = None
    for subset in candidates:
        res = _solve(model, subset, retirements)
        if res and (best is None or res[0].value < best[1].value):
            best = (subset, res[0], res[1])
    return best


def scan_bets(rows: list[dict]) -> list[Opportunity]:
    events: dict = {}
    for r in rows:
        key = (r["event_id"], r.get("period") or "")
        events.setdefault(key, []).append(r)
    out = []
    for (eid, period), rs in events.items():
        sport = rs[0]["sport"]
        model = model_for(sport)
        bets = [Bet(book=r["book"], market=r["market"].upper(), outcome=r["outcome"].upper(),
                    odds=frac(r["odds"]), line=frac(r.get("line")), side=(r.get("side") or "BACK").upper(),
                    commission=frac(r.get("commission")) or F(0), rule=(r.get("rule") or "UNKNOWN").upper())
                for r in rs if frac(r["odds"]) and frac(r["odds"]) > 1]
        if not bets:
            continue
        retire = model == "winner" and sport.lower() in RETIREMENT_SPORTS
        best = analyse_event(model, bets, retire)
        robust = True
        if (best is None or not best[1].is_arbitrage) and retire:
            alt = analyse_event(model, bets, False)
            if alt and alt[1].is_arbitrage:
                best, robust = alt, False
        if best and best[1].is_arbitrage:
            subset, cov, void_all = best
            legs = [(b, y / cov.value) for b, y in zip(subset, cov.stakes) if y > 0]
            out.append(Opportunity(eid, rs[0].get("event_name") or eid, sport, period, cov.value, legs,
                                   len({_group_key(b) for b, _ in legs}), robust, void_all))
    return sorted(out, key=lambda o: (not o.robust, o.value))


def round_legs(opp: Opportunity, model: str, bank: F, step: F, retirements: bool):
    """Redondea los importes a multiplos de `step` maximizando el peor resultado neto."""
    bets = [b for b, _ in opp.legs]
    states, R = build_matrix(model, bets, retirements)
    # escenarios en que todo se devuelve: resultado 0 siempre, no cuentan para el peor caso
    live = [s for s in range(len(states)) if not all(R[j][s] == 1 for j in range(len(bets)))]
    ideal = [w * bank for _, w in opp.legs]
    cands = []
    for a in ideal:
        q = a / step
        lo, hi = (q.numerator // q.denominator) * step, -((-q.numerator) // q.denominator) * step
        cands.append(sorted({x for x in (lo, hi) if x > 0}) or [step])
    best = None
    for combo in product(*cands):
        total = sum(combo)
        worst = min(sum(c * R[j][s] for j, c in enumerate(combo)) - total for s in live)
        key = (worst / total, worst)
        if best is None or key > best[0]:
            best = (key, list(combo), total, worst)
    _, stakes, total, worst = best
    return stakes, total, worst


def read_csv(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
