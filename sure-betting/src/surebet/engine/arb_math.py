"""Motor matematico del arbitraje. Solo Decimal, funciones puras.

Formulas: docs/fase-0-investigacion.md, seccion 9.1.
"""
from __future__ import annotations

from fractions import Fraction
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, getcontext
from itertools import product
from typing import Sequence

getcontext().prec = 28

__all__ = [
    "to_decimal", "implied_probabilities", "overround", "effective_back_odds",
    "arbitrage_sum", "has_arbitrage", "theoretical_return", "equal_payout_stakes", "payouts",
    "min_profit", "optimize_rounding", "back_lay", "hedge_after_partial",
    "scale_to_limit", "money", "RoundingResult", "BackLayResult", "HedgeResult",
]

ONE = Decimal(1)
CENT = Decimal("0.01")


def to_decimal(value) -> Decimal:
    """Convierte str/int/Decimal a Decimal. Rechaza float (error de precision)."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("Usa str, int o Decimal para cuotas e importes, nunca float.")
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    return Decimal(value)


def money(x: Decimal) -> Decimal:
    """Cuantiza a centimos. Solo para presentar importes."""
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def _odds(odds: Sequence) -> list[Decimal]:
    out = [to_decimal(o) for o in odds]
    if len(out) < 2:
        raise ValueError("Hacen falta al menos 2 resultados.")
    if any(o <= ONE for o in out):
        raise ValueError("Toda cuota debe ser mayor que 1.")
    return out


def _commissions(n: int, commissions) -> list[Decimal]:
    if commissions is None:
        return [Decimal(0)] * n
    c = [to_decimal(x) for x in commissions]
    if len(c) != n:
        raise ValueError("Una comision por resultado.")
    if any(x < 0 or x >= ONE for x in c):
        raise ValueError("La comision debe estar entre 0 y 1.")
    return c


def implied_probabilities(odds: Sequence) -> list[Decimal]:
    return [ONE / o for o in _odds(odds)]


def overround(odds: Sequence) -> Decimal:
    """Margen de la casa: suma de probabilidades implicitas menos 1."""
    return sum(implied_probabilities(odds)) - ONE


def effective_back_odds(odds, commission="0") -> Decimal:
    """Cuota efectiva tras comision sobre ganancia neta: 1 + (c-1)(1-k)."""
    o, k = to_decimal(odds), to_decimal(commission)
    if o <= ONE:
        raise ValueError("Toda cuota debe ser mayor que 1.")
    return ONE + (o - ONE) * (ONE - k)


def _effective(odds, commissions) -> list[Decimal]:
    o = _odds(odds)
    k = _commissions(len(o), commissions)
    return [effective_back_odds(a, b) for a, b in zip(o, k)]


def arbitrage_sum(odds: Sequence, commissions=None) -> Decimal:
    """S = suma de 1/cuota_efectiva. Hay arbitraje teorico si S < 1."""
    return sum(ONE / e for e in _effective(odds, commissions))


def has_arbitrage(odds: Sequence, commissions=None) -> bool:
    """Decision exacta de S < 1 con fracciones (sin error de redondeo).

    Con Decimal, 3 cuotas de 3.00 suman 0.999...9 en vez de 1. Toda decision de
    'hay o no hay arbitraje' debe usar esta funcion, no comparar arbitrage_sum.
    """
    return sum(Fraction(1) / Fraction(e) for e in _effective(odds, commissions)) < 1


def theoretical_return(s: Decimal) -> Decimal:
    """R = 1/S - 1."""
    return ONE / s - ONE


def equal_payout_stakes(odds: Sequence, bank, commissions=None) -> list[Decimal]:
    """Importes que dan el mismo pago en cualquier resultado: a_i = B/(e_i*S)."""
    eff = _effective(odds, commissions)
    s = sum(ONE / e for e in eff)
    b = to_decimal(bank)
    return [b * (ONE / e) / s for e in eff]


def payouts(odds: Sequence, stakes: Sequence, commissions=None) -> list[Decimal]:
    eff = _effective(odds, commissions)
    st = [to_decimal(x) for x in stakes]
    if len(st) != len(eff):
        raise ValueError("Un importe por resultado.")
    return [a * e for a, e in zip(st, eff)]


def min_profit(odds: Sequence, stakes: Sequence, commissions=None) -> Decimal:
    """Beneficio garantizado: peor pago menos el total apostado."""
    return min(payouts(odds, stakes, commissions)) - sum(to_decimal(x) for x in stakes)


class RoundingResult:
    __slots__ = ("stakes", "payouts", "total", "min_profit", "roi")

    def __init__(self, stakes, pays, total, profit):
        self.stakes, self.payouts, self.total = stakes, pays, total
        self.min_profit, self.roi = profit, profit / total

    def __repr__(self):
        return f"RoundingResult(stakes={self.stakes}, min_profit={self.min_profit}, roi={self.roi})"


def optimize_rounding(odds: Sequence, ideal_stakes: Sequence, step, commissions=None) -> RoundingResult:
    """Mejor combinacion de importes multiplos de `step` (suelo/techo del ideal).

    Maximiza el retorno minimo garantizado sobre el total apostado. El retorno
    publicable es el de esta funcion, no el teorico.
    """
    h = to_decimal(step)
    if h <= 0:
        raise ValueError("El paso debe ser positivo.")
    eff = _effective(odds, commissions)
    cands = []
    for s in ideal_stakes:
        q = to_decimal(s) / h
        lo = q.to_integral_value(rounding=ROUND_FLOOR) * h
        hi = q.to_integral_value(rounding=ROUND_CEILING) * h
        opts = sorted({x for x in (lo, hi) if x > 0})
        if not opts:
            opts = [h]
        cands.append(opts)
    best = None
    for combo in product(*cands):
        total = sum(combo)
        pays = [c * e for c, e in zip(combo, eff)]
        profit = min(pays) - total
        key = (profit / total, profit)
        if best is None or key > best[0]:
            best = (key, combo, pays, total, profit)
    _, combo, pays, total, profit = best
    return RoundingResult(list(combo), pays, total, profit)


class BackLayResult:
    __slots__ = ("lay_stake", "liability", "profit_if_back_wins", "profit_if_lay_wins",
                 "roi_on_back", "roi_on_capital", "is_arbitrage")

    def __repr__(self):
        return (f"BackLayResult(lay={money(self.lay_stake)}, liability={money(self.liability)}, "
                f"profit={money(self.profit_if_lay_wins)})")


def back_lay(back_stake, back_odds, lay_odds, commission="0") -> BackLayResult:
    """A favor en una casa y en contra en un exchange (comision k sobre ganancia)."""
    s, b, l, k = (to_decimal(x) for x in (back_stake, back_odds, lay_odds, commission))
    if b <= ONE or l <= ONE or s <= 0 or not (0 <= k < ONE):
        raise ValueError("Valores invalidos.")
    r = BackLayResult()
    r.lay_stake = s * b / (l - k)
    r.liability = r.lay_stake * (l - ONE)
    r.profit_if_back_wins = s * (b - ONE) - r.liability
    r.profit_if_lay_wins = r.lay_stake * (ONE - k) - s
    r.roi_on_back = r.profit_if_lay_wins / s
    r.roi_on_capital = r.profit_if_lay_wins / (s + r.liability)
    r.is_arbitrage = b * (ONE - k) > l - k
    return r


class HedgeResult:
    __slots__ = ("stakes", "total", "guaranteed", "guaranteed_roi")

    def __repr__(self):
        return f"HedgeResult(stakes={self.stakes}, guaranteed={money(self.guaranteed)})"


def hedge_after_partial(placed: dict, remaining_odds: dict, commissions: dict | None = None) -> HedgeResult:
    """Cobertura tras colocar patas. placed: {resultado: (importe, cuota)};
    remaining_odds: {resultado: cuota}. Iguala el pago al peor de los ya colocados.
    El resultado garantizado puede ser negativo.
    """
    commissions = commissions or {}
    placed_pay = {}
    placed_total = Decimal(0)
    for k, (stake, o) in placed.items():
        stake = to_decimal(stake)
        e = effective_back_odds(o, commissions.get(k, "0"))
        placed_pay[k] = stake * e
        placed_total += stake
    target = min(placed_pay.values())
    stakes = {}
    for k, o in remaining_odds.items():
        e = effective_back_odds(o, commissions.get(k, "0"))
        stakes[k] = target / e
    total = placed_total + sum(stakes.values())
    r = HedgeResult()
    r.stakes, r.total = stakes, total
    r.guaranteed = target - total
    r.guaranteed_roi = r.guaranteed / total
    return r


def scale_to_limit(stakes: Sequence, leg: int, max_stake) -> list[Decimal]:
    """Reduce todos los importes proporcionalmente si la pata `leg` no admite tanto."""
    st = [to_decimal(x) for x in stakes]
    m = to_decimal(max_stake)
    if m <= 0:
        raise ValueError("El limite debe ser positivo.")
    if st[leg] <= m:
        return st
    f = m / st[leg]
    return [x * f for x in st]
