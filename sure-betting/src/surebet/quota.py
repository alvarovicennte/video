"""Gestor de presupuesto de creditos: ninguna llamada de pago sin pasar por aqui."""
from __future__ import annotations

import sqlite3


class BudgetError(Exception):
    pass


def known_remaining(conn: sqlite3.Connection, provider: str) -> int | None:
    row = conn.execute("SELECT credits_remaining FROM poll WHERE provider=? AND credits_remaining IS NOT NULL "
                       "ORDER BY id DESC LIMIT 1", (provider,)).fetchone()
    return row[0] if row else None


def check_budget(conn, provider: str, cost: int, per_run_max: int, reserve: int = 25) -> None:
    if cost > per_run_max:
        raise BudgetError(f"Esta llamada costaria {cost} creditos y el maximo por ejecucion es {per_run_max}. "
                          f"Usa menos mercados o regiones, o sube --max-creditos conscientemente.")
    rem = known_remaining(conn, provider)
    if rem is not None and rem - cost < reserve:
        raise BudgetError(f"Quedan {rem} creditos y la reserva es {reserve}. No se hace la llamada.")
