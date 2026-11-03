"""Escenarios y pagos por deporte. Cada apuesta se convierte en un vector de pagos
brutos por unidad apostada (cuota si gana, 1 si se devuelve, 0 si pierde).

Modelos:
- "score": marcador (local h, visitante a) dentro de un periodo fijo (futbol 90 min,
  baloncesto o hockey a tiempo reglamentario). Mercados 1X2, DNB, DC, AH (lineas
  enteras, medias y de cuarto), TOTAL (idem) y BTTS.
- "winner": gana P1 / P2 (tenis, tenis de mesa, badminton, MMA...). Con retiradas
  activadas anade escenarios de retirada y aplica la regla de cada casa:
  MATCH_COMPLETED (anula), ONE_SET (anula si no hubo set completo; si no, gana quien
  pasa), BALL_SERVED (gana quien pasa), UNKNOWN (peor caso: pierde).
Una apuesta LAY (en contra, en exchange) se modela como apuesta a favor del
resultado contrario con cuota efectiva 1 + (1-k)/(L-1) sobre la responsabilidad.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as F
from math import floor, ceil

WIN, LOSE, PUSH = "W", "L", "P"


@dataclass(frozen=True)
class Bet:
    book: str
    market: str            # WINNER, 1X2, DNB, DC, AH, TOTAL, BTTS
    outcome: str           # P1/P2, HOME/DRAW/AWAY, 1X/X2/12, OVER/UNDER, YES/NO
    odds: F                # cuota decimal tal cual
    line: F | None = None  # AH: handicap del lado apostado; TOTAL: linea
    side: str = "BACK"     # BACK o LAY
    commission: F = F(0)   # sobre ganancia neta (exchange)
    rule: str = "UNKNOWN"  # regla de retirada (solo modelo winner)

    @property
    def win_multiplier(self) -> F:
        """Pago bruto por unidad arriesgada cuando la apuesta gana."""
        if self.side == "BACK":
            return 1 + (self.odds - 1) * (1 - self.commission)
        return 1 + (1 - self.commission) / (self.odds - 1)  # LAY: unidad = responsabilidad


def _line_results(margin_fn, line: F) -> list[tuple[str, F]]:
    """Resultado de una linea, partiendo las de cuarto (x.25 / x.75) en dos mitades."""
    frac = line - floor(line)
    if frac in (F(1, 4), F(3, 4)):
        return [(_settle(margin_fn(line - F(1, 4))), F(1, 2)), (_settle(margin_fn(line + F(1, 4))), F(1, 2))]
    return [(_settle(margin_fn(line)), F(1))]


def _settle(margin: F) -> str:
    return WIN if margin > 0 else LOSE if margin < 0 else PUSH


def back_results_score(bet: Bet, h: int, a: int) -> list[tuple[str, F]]:
    d, t = h - a, h + a
    m, o = bet.market, bet.outcome
    if m == "1X2":
        ok = {"HOME": d > 0, "DRAW": d == 0, "AWAY": d < 0}[o]
        return [(WIN if ok else LOSE, F(1))]
    if m == "DC":
        ok = {"1X": d >= 0, "X2": d <= 0, "12": d != 0}[o]
        return [(WIN if ok else LOSE, F(1))]
    if m == "DNB":
        if d == 0:
            return [(PUSH, F(1))]
        return [(WIN if (d > 0) == (o == "HOME") else LOSE, F(1))]
    if m == "BTTS":
        both = h >= 1 and a >= 1
        return [(WIN if both == (o == "YES") else LOSE, F(1))]
    if m == "AH":  # line = handicap del lado apostado
        sign = 1 if o == "HOME" else -1
        return _line_results(lambda ln: sign * d + ln, bet.line)
    if m == "TOTAL":
        sign = 1 if o == "OVER" else -1
        return _line_results(lambda ln: sign * (t - ln), bet.line)
    raise ValueError(f"Mercado no soportado en modelo score: {m}")


def payoff(bet: Bet, results: list[tuple[str, F]]) -> F:
    """Pago bruto por unidad a partir de los resultados (con pesos) de la apuesta A FAVOR."""
    w = bet.win_multiplier
    total = F(0)
    for r, weight in results:
        if bet.side == "LAY":
            r = {WIN: LOSE, LOSE: WIN, PUSH: PUSH}[r]
        total += weight * (w if r == WIN else F(1) if r == PUSH else F(0))
    return total


def score_states(bets: list[Bet]) -> list[tuple[int, int]]:
    """Marcadores representativos: suficientes para distinguir todos los pagos.

    Los pagos dependen solo de signo/umbrales de d = h-a y t = h+a y de min(h,a)>=1.
    Se toman enteros alrededor de cada umbral (+-2) y todos los marcadores pequenos;
    una prueba lo compara con la enumeracion completa.
    """
    dc, tc = {0, 1, -1, 2, -2}, {0, 1, 2, 3, 4}
    for b in bets:
        if b.line is None:
            continue
        if b.market == "AH":
            thr = -b.line if b.outcome == "HOME" else b.line
            for k in range(floor(thr) - 2, ceil(thr) + 3):
                dc.add(k)
        if b.market == "TOTAL":
            for k in range(max(0, floor(b.line) - 2), ceil(b.line) + 3):
                tc.add(k)
    for k in list(tc):
        tc.update({k + 1, max(0, k - 1)})
    dmax = max(abs(x) for x in dc)
    out = set()
    for d in dc:
        for t in tc | {abs(d), abs(d) + 1, abs(d) + 2}:
            if t >= abs(d) and (t - d) % 2 == 0:
                out.add(((t + d) // 2, (t - d) // 2))
    for h in range(4):
        for a in range(4):
            out.add((h, a))
    out.add((dmax + 3, 0))
    out.add((0, dmax + 3))
    return sorted(out)


WINNER_BASE = ["P1_WIN", "P2_WIN"]
RETIREMENTS = ["RET_P1_PRE", "RET_P1_POST", "RET_P2_PRE", "RET_P2_POST"]


def back_results_winner(bet: Bet, state: str) -> list[tuple[str, F]]:
    o = bet.outcome
    if state in WINNER_BASE:
        return [(WIN if state == f"{o}_WIN" else LOSE, F(1))]
    retiring = state[4:6]          # P1 / P2
    post = state.endswith("POST")
    rule = bet.rule
    if rule == "MATCH_COMPLETED" or (rule == "ONE_SET" and not post):
        return [(PUSH, F(1))]
    if rule in ("ONE_SET", "BALL_SERVED"):
        return [(LOSE if retiring == o else WIN, F(1))]
    return [(LOSE, F(1))]          # UNKNOWN: peor caso


def build_matrix(model: str, bets: list[Bet], retirements: bool = True):
    """Devuelve (estados, R) con R[j][s] = pago bruto por unidad de la apuesta j en s."""
    if model == "score":
        states = score_states(bets)
        R = [[payoff(b, back_results_score(b, h, a)) for (h, a) in states] for b in bets]
    elif model == "winner":
        states = WINNER_BASE + (RETIREMENTS if retirements else [])
        R = [[payoff(b, back_results_winner(b, s)) for s in states] for b in bets]
    else:
        raise ValueError(f"Modelo desconocido: {model}")
    return states, R


def compact(states, R):
    """Quita escenarios con el mismo vector de pagos y los que anulan todo (pago 1 en todas).

    Un escenario en que TODAS las apuestas se devuelven deja el resultado en 0 pase lo que
    pase: no puede dar perdida ni beneficio, asi que no restringe nada.
    """
    seen, keep, void_all = {}, [], []
    for s_idx, s in enumerate(states):
        col = tuple(R[j][s_idx] for j in range(len(R)))
        if all(v == 1 for v in col):
            void_all.append(s)
            continue
        if col not in seen:
            seen[col] = s
            keep.append(s_idx)
    return [states[i] for i in keep], [[row[i] for i in keep] for row in R], void_all
