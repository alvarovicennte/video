"""Linea de comandos: surebet calc | backlay | gen-test-data."""
from __future__ import annotations

from decimal import InvalidOperation
from typing import List, Optional

import typer

from .engine import arb_math as m
from . import testdata

app = typer.Typer(add_completion=False, help="SURE BETTING (H1): calculadora verificable.")


def _clean(e: Exception) -> str:
    return "numero no valido" if isinstance(e, InvalidOperation) else str(e)


def _fmt_pct(x) -> str:
    return f"{(x * 100).quantize(m.Decimal('0.01'))}%"


@app.command()
def calc(
    cuotas: List[str] = typer.Argument(..., help="Mejor cuota de cada resultado, ej: 2,10 2,00"),
    banca: str = typer.Option("100", help="Dinero total a repartir (EUR)."),
    paso: str = typer.Option("0.01", help="Multiplo de redondeo de cada apuesta (EUR), ej: 1"),
    comision: Optional[List[str]] = typer.Option(None, help="Comision por resultado (ej: 0,02), en el mismo orden."),
):
    """Calcula si hay arbitraje y cuanto apostar a cada resultado."""
    try:
        s = m.arbitrage_sum(cuotas, comision)
        r = m.theoretical_return(s)
    except (ValueError, TypeError, InvalidOperation) as e:
        typer.echo(f"Error: revisa los numeros ({_clean(e)})")
        raise typer.Exit(1)
    typer.echo(f"Suma de probabilidades (S): {s.quantize(m.Decimal('0.000001'))}")
    if not m.has_arbitrage(cuotas, comision):
        typer.echo(f"NO hay arbitraje (S >= 1). Margen del conjunto: {_fmt_pct(max(s - 1, m.Decimal(0)))}")
        raise typer.Exit(0)
    typer.echo(f"HAY arbitraje teorico: retorno {_fmt_pct(r)}")
    ideal = m.equal_payout_stakes(cuotas, banca, comision)
    typer.echo("\nReparto ideal (cobras lo mismo pase lo que pase):")
    for i, (c, a) in enumerate(zip(cuotas, ideal), 1):
        typer.echo(f"  Resultado {i} a cuota {c}: {m.money(a)} EUR")
    res = m.optimize_rounding(cuotas, ideal, paso, comision)
    typer.echo(f"\nTras redondear a multiplos de {paso} EUR (mejor combinacion):")
    for i, a in enumerate(res.stakes, 1):
        typer.echo(f"  Resultado {i}: {m.money(a)} EUR")
    typer.echo(f"  Total apostado: {m.money(res.total)} EUR")
    typer.echo(f"  Beneficio minimo garantizado: {m.money(res.min_profit)} EUR ({_fmt_pct(res.roi)})")
    if res.min_profit <= 0:
        typer.echo("  OJO: con este redondeo el arbitraje desaparece (no hay beneficio).")
    typer.echo("\nEsto es teoria con cuotas que tu das. No tiene en cuenta que la cuota cambie,"
               "\nlimites de apuesta ni reglas de liquidacion distintas entre casas.")


@app.command()
def backlay(
    apuesta_a_favor: str = typer.Argument(..., help="Importe a favor en la casa (EUR)"),
    cuota_a_favor: str = typer.Argument(..., help="Cuota a favor en la casa"),
    cuota_en_contra: str = typer.Argument(..., help="Cuota en contra en el exchange"),
    comision: str = typer.Option("0.02", help="Comision del exchange (Betfair Espana: 0,02)"),
):
    """A favor en una casa y en contra en un exchange."""
    try:
        r = m.back_lay(apuesta_a_favor, cuota_a_favor, cuota_en_contra, comision)
    except (ValueError, TypeError, InvalidOperation) as e:
        typer.echo(f"Error: revisa los numeros ({_clean(e)})")
        raise typer.Exit(1)
    typer.echo(f"Apuesta en contra: {m.money(r.lay_stake)} EUR  (responsabilidad {m.money(r.liability)} EUR)")
    typer.echo(f"Beneficio si gana la casa: {m.money(r.profit_if_back_wins)} EUR")
    typer.echo(f"Beneficio si gana el exchange: {m.money(r.profit_if_lay_wins)} EUR")
    typer.echo(f"Sobre la apuesta: {_fmt_pct(r.roi_on_back)} | sobre el dinero inmovilizado: {_fmt_pct(r.roi_on_capital)}")
    if not r.is_arbitrage:
        typer.echo("NO es arbitraje: despues de comision pierdes en al menos un caso.")


@app.command("gen-test-data")
def gen_test_data(
    salida: str = typer.Option("data/synthetic_quotes.csv", help="Fichero CSV de salida"),
    semilla: int = typer.Option(7),
    eventos: int = typer.Option(50),
):
    """Genera cuotas inventadas con arbitrajes plantados y trampas (para pruebas)."""
    n = testdata.write_csv(salida, semilla, eventos)
    typer.echo(f"{n} filas escritas en {salida}. Son datos inventados, no reales.")


if __name__ == "__main__":
    app()
