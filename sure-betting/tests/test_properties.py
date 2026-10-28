"""Propiedades con hypothesis y reglas de entrada."""
import ast
from decimal import Decimal as D
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from surebet.engine import arb_math as m

odds_st = st.decimals(min_value=D("1.05"), max_value=D("20"), places=2, allow_nan=False, allow_infinity=False)
odds_list = st.lists(odds_st, min_size=2, max_size=4)


@settings(max_examples=10000, deadline=None)
@given(odds_list, st.decimals(min_value=D("10"), max_value=D("5000"), places=2))
def test_stakes_suman_la_banca_y_pagos_iguales(odds, bank):
    stakes = m.equal_payout_stakes(odds, bank)
    assert abs(sum(stakes) - bank) < D("1e-20")
    pays = m.payouts(odds, stakes)
    assert max(pays) - min(pays) < D("1e-20")
    s = m.arbitrage_sum(odds)
    assert abs(pays[0] - bank / s) < D("1e-20")


@settings(max_examples=3000, deadline=None)
@given(odds_list, st.sampled_from([D("0.01"), D("0.5"), D(1), D(5)]))
def test_redondeo_optimizado_no_es_peor_que_el_simple(odds, step):
    ideal = m.equal_payout_stakes(odds, 100)
    opt = m.optimize_rounding(odds, ideal, step)
    simple = [(s / step).to_integral_value() * step for s in ideal]
    if min(simple) > 0:
        simple_roi = m.min_profit(odds, simple) / sum(simple)
        assert opt.roi >= simple_roi


@settings(max_examples=3000, deadline=None)
@given(odds_list)
def test_arbitraje_si_y_solo_si_s_menor_que_1(odds):
    arb = m.has_arbitrage(odds)
    stakes = m.equal_payout_stakes(odds, 100)
    profit = m.min_profit(odds, stakes)
    if arb:
        assert profit > D("-1e-20")
    else:
        assert profit < D("1e-20")


def test_rechaza_float():
    with pytest.raises(TypeError):
        m.arbitrage_sum([2.1, 2.0])
    with pytest.raises(TypeError):
        m.equal_payout_stakes(["2.1", "2.0"], 100.0)


@pytest.mark.parametrize("bad", [["1.00", "2.0"], ["0.5", "3"], ["2.0"], []])
def test_rechaza_cuotas_invalidas(bad):
    with pytest.raises(ValueError):
        m.arbitrage_sum(bad)


def test_coma_decimal_espanola():
    assert m.arbitrage_sum(["2,10", "2,00"]) == m.arbitrage_sum(["2.10", "2.00"])


def test_cuotas_extremas():
    assert m.arbitrage_sum(["1.01", "100"]) > 1
    assert m.theoretical_return(m.arbitrage_sum(["1.01", "100"])) < 0


def test_comision_invalida():
    with pytest.raises(ValueError):
        m.arbitrage_sum(["2", "2"], ["1", "0"])


def test_no_hay_float_en_el_motor():
    src = Path(__file__).parents[1] / "src" / "surebet" / "engine"
    for f in src.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                pytest.fail(f"{f.name}: literal float en linea {node.lineno}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
                pytest.fail(f"{f.name}: llamada a float() en linea {node.lineno}")


def test_s_exactamente_1_no_es_arbitraje():
    # 1/3 + 1/3 + 1/3 en Decimal da 0.999...9: la decision debe ser exacta.
    assert m.arbitrage_sum(["3.00", "3.00", "3.00"]) < 1
    assert m.has_arbitrage(["3.00", "3.00", "3.00"]) is False
    assert m.has_arbitrage(["2.00", "2.00"]) is False
    assert m.has_arbitrage(["2.10", "2.00"]) is True
