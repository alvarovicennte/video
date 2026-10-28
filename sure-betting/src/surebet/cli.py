"""Linea de comandos: surebet calc | backlay | gen-test-data."""
from __future__ import annotations

from decimal import InvalidOperation
from typing import List, Optional

import typer

from .engine import arb_math as m
from . import testdata
from .config import ConfigError, get_odds_api_key
from .ingest import run_ingest
from .providers import the_odds_api as t_api
from .quota import BudgetError, known_remaining
from .storage.db import connect
import json as _json

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



def _api() -> t_api.TheOddsApi:
    try:
        return t_api.TheOddsApi(get_odds_api_key())
    except ConfigError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)


@app.command()
def sports(buscar: str = typer.Option("", help="Filtra por texto, ej: spain o soccer")):
    """Lista los deportes/ligas que ofrece la API (no consume creditos segun su documentacion)."""
    try:
        r = _api().sports()
    except t_api.SourceError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    if r.status != 200:
        typer.echo(f"La API respondio HTTP {r.status}. Revisa la clave en .env.")
        raise typer.Exit(1)
    for s in _json.loads(r.body):
        if buscar.lower() in (s["key"] + s.get("title", "")).lower():
            typer.echo(f"{s['key']:40s} {s.get('title', '')}")
    typer.echo(f"\nCreditos restantes segun la API: {r.usage.remaining}")


@app.command()
def ingest(
    liga: str = typer.Argument(..., help="Clave de la liga, ej: soccer_spain_la_liga"),
    mercados: str = typer.Option("h2h", help="h2h (1X2) y/o totals (mas/menos), separados por coma"),
    regiones: str = typer.Option("eu", help="Regiones: eu, uk..."),
    max_creditos: int = typer.Option(4, help="Maximo de creditos que puede gastar esta ejecucion"),
    db: str = typer.Option("data/surebet.db"),
):
    """Captura cuotas reales de una liga y las guarda (con tope de gasto)."""
    conn = connect(db)
    try:
        s = run_ingest(_api(), conn, liga, mercados.split(","), regiones.split(","), per_run_max=max_creditos)
    except BudgetError as e:
        typer.echo(f"No se hizo la llamada: {e}")
        raise typer.Exit(1)
    except t_api.SourceError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    if s.error:
        typer.echo(f"La API respondio con error: {s.error}")
        raise typer.Exit(1)
    typer.echo(f"HTTP {s.status} | eventos: {s.events} | cuotas guardadas: {s.quotes}")
    typer.echo(f"Creditos: esta llamada {s.credits_last} (estimado {s.cost_estimated}), quedan {s.credits_remaining}")
    typer.echo(f"Cuotas con hora de actualizacion de la casa: {s.with_update_time} de {s.quotes}")
    typer.echo(f"Resultados sin reconocer: {s.unmapped}")
    typer.echo("Casas devueltas (cuotas por casa):")
    for k, n in sorted(s.books.items()):
        typer.echo(f"  {k:24s} {n}")


@app.command()
def quota(db: str = typer.Option("data/surebet.db")):
    """Muestra los creditos que quedan segun la ultima llamada guardada."""
    rem = known_remaining(connect(db), t_api.PROVIDER)
    typer.echo("Aun no hay llamadas guardadas." if rem is None else f"Creditos restantes: {rem}")


if __name__ == "__main__":
    app()
