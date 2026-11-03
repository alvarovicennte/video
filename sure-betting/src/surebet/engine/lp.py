"""Programacion lineal exacta (fracciones) para el arbitraje generalizado.

Problema: hay apuestas j con pago bruto R[j][s] por unidad apostada en cada
escenario s. Buscamos importes y >= 0 que minimicen lo apostado (sum y) con
pago >= 1 en todo escenario:

    min  sum_j y_j      s.a.  sum_j y_j R[j][s] >= 1  (todo s),  y >= 0

Si el optimo V < 1 hay arbitraje: apostando y_j cobras al menos 1 habiendo
puesto V. Retorno garantizado = 1/V - 1. Con una apuesta por resultado de un
mercado simple, V es exactamente la suma de probabilidades S.

Se resuelve el dual (max sum p_s, sum_s R[j][s] p_s <= 1, p >= 0), que parte de
una base factible, con simplex y regla de Bland (sin ciclos). Todo con
Fraction: sin errores de redondeo. Los precios duales de las restricciones
son los importes y_j. Las p_s optimas se leen como probabilidades "neutrales al
riesgo" que hacen justas todas las cuotas a la vez.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

F = Fraction


class Unbounded(Exception):
    """Algun escenario no lo paga ninguna apuesta: no hay cobertura posible."""


def simplex_max(c: Sequence[F], A: Sequence[Sequence[F]], b: Sequence[F]):
    """max c.x  s.a.  A x <= b, x >= 0, con b >= 0. Devuelve (valor, x, duales)."""
    m, n = len(A), len(c)
    if any(bi < 0 for bi in b):
        raise ValueError("b debe ser >= 0")
    # tableau: m filas [A | I | b], fila objetivo [-c | 0 | 0]
    T = [[F(v) for v in A[i]] + [F(int(i == k)) for k in range(m)] + [F(b[i])] for i in range(m)]
    z = [-F(v) for v in c] + [F(0)] * m + [F(0)]
    basis = [n + i for i in range(m)]
    width = n + m
    while True:
        enter = next((j for j in range(width) if z[j] < 0), None)  # Bland: menor indice
        if enter is None:
            break
        best = None
        for i in range(m):
            a = T[i][enter]
            if a > 0:
                ratio = T[i][-1] / a
                if best is None or ratio < best[0] or (ratio == best[0] and basis[i] < basis[best[1]]):
                    best = (ratio, i)
        if best is None:
            raise Unbounded()
        r = best[1]
        piv = T[r][enter]
        T[r] = [v / piv for v in T[r]]
        for i in range(m):
            if i != r and T[i][enter] != 0:
                f = T[i][enter]
                T[i] = [vi - f * vr for vi, vr in zip(T[i], T[r])]
        if z[enter] != 0:
            f = z[enter]
            z = [vz - f * vr for vz, vr in zip(z, T[r])]
        basis[r] = enter
    x = [F(0)] * n
    for i, bv in enumerate(basis):
        if bv < n:
            x[bv] = T[i][-1]
    duals = [z[n + i] for i in range(m)]
    return z[-1], x, duals


@dataclass
class Cover:
    value: F                  # V: lo que hay que apostar para cobrar >= 1 en todo escenario
    stakes: list[F]           # y_j (suman V)
    probs: list[F]            # p_s del dual
    min_payout: F             # comprobacion: minimo pago con y (debe ser >= 1)

    @property
    def is_arbitrage(self) -> bool:
        return self.value < 1

    @property
    def guaranteed_return(self) -> F:
        return 1 / self.value - 1


def best_cover(R: Sequence[Sequence[F]]) -> Cover | None:
    """R[j][s] >= 0. Devuelve la cobertura minima o None si algun escenario no se cubre."""
    nb = len(R)
    if nb == 0:
        return None
    ns = len(R[0])
    if any(all(R[j][s] == 0 for j in range(nb)) for s in range(ns)):
        return None
    try:
        value, p, y = simplex_max([F(1)] * ns, R, [F(1)] * nb)
    except Unbounded:
        return None
    pays = [sum(y[j] * R[j][s] for j in range(nb)) for s in range(ns)]
    mp = min(pays)
    # comprobaciones exactas de optimalidad (dualidad fuerte)
    assert sum(y) == value, "dualidad: sum y != V"
    assert mp >= 1, "la cobertura no paga 1 en algun escenario"
    return Cover(value=value, stakes=list(y), probs=list(p), min_payout=mp)
