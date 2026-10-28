"""Casos dorados: ejemplos de docs/fase-0-investigacion.md, al centimo."""
from decimal import Decimal as D

import pytest

from surebet.engine import arb_math as m


def q(x, places="0.000001"):
    return x.quantize(D(places))


def test_ej1_margen_190_190():
    assert q(sum(m.implied_probabilities(["1.90", "1.90"])), "0.0001") == D("1.0526")
    assert q(m.overround(["1.90", "1.90"]), "0.0001") == D("0.0526")


def test_ej2_margen_1x2():
    assert q(m.overround(["2.30", "3.30", "3.20"]), "0.0001") == D("0.0503")


def test_ej3_surebet_dos_vias():
    s = m.arbitrage_sum(["2.10", "2.00"])
    assert q(s) == D("0.976190")
    assert q(m.theoretical_return(s), "0.00001") == D("0.02439")
    st = m.equal_payout_stakes(["2.10", "2.00"], 100)
    assert [m.money(x) for x in st] == [D("48.78"), D("51.22")]
    assert m.money(100 / s) == D("102.44")


def test_ej4_surebet_1x2():
    odds = ["2.45", "3.60", "3.40"]
    s = m.arbitrage_sum(odds)
    assert q(s) == D("0.980059")
    st = m.equal_payout_stakes(odds, 100)
    assert [m.money(x) for x in st] == [D("41.65"), D("28.34"), D("30.01")]


def test_favorito_bajo_2_sigue_siendo_arbitraje():
    s = m.arbitrage_sum(["1.65", "4.50", "6.50"])
    assert q(s) == D("0.982129")
    assert q(m.theoretical_return(s), "0.0001") == D("0.0182")


def test_ej5_comision_cuota_efectiva():
    assert m.effective_back_odds("2.10", "0.02") == D("2.0780")
    assert m.effective_back_odds("2.10", "0.05") == D("2.0450")


@pytest.mark.parametrize("k,lay,liab,profit,roi_back,roi_cap", [
    ("0.02", "105.77", "116.35", "3.65", "0.0365", "0.0169"),
    ("0.05", "107.32", "118.05", "1.95", "0.0195", "0.0089"),
])
def test_ej5_back_lay(k, lay, liab, profit, roi_back, roi_cap):
    r = m.back_lay(100, "2.20", "2.10", k)
    assert m.money(r.lay_stake) == D(lay)
    assert m.money(r.liability) == D(liab)
    assert m.money(r.profit_if_lay_wins) == D(profit)
    assert m.money(r.profit_if_back_wins) == D(profit)
    assert q(r.roi_on_back, "0.0001") == D(roi_back)
    assert q(r.roi_on_capital, "0.0001") == D(roi_cap)
    assert r.is_arbitrage


@pytest.mark.parametrize("step,stakes,profit", [
    ("0.01", ["48.78", "51.22"], "2.44"),
    ("1", ["49", "51"], "2.00"),
    ("5", ["50", "50"], "0.00"),
])
def test_redondeo_dos_vias(step, stakes, profit):
    ideal = m.equal_payout_stakes(["2.10", "2.00"], 100)
    r = m.optimize_rounding(["2.10", "2.00"], ideal, step)
    assert r.stakes == [D(x) for x in stakes]
    assert m.money(r.min_profit) == D(profit)


def test_redondeo_1x2_paso_1_optimizado():
    odds = ["2.45", "3.60", "3.40"]
    r = m.optimize_rounding(odds, m.equal_payout_stakes(odds, 100), "1")
    assert r.stakes == [D(41), D(28), D(30)]
    assert r.total == 99
    assert m.money(r.min_profit) == D("1.45")
    assert q(r.roi, "0.0001") == D("0.0146")


def test_redondeo_1x2_paso_5_da_perdida():
    odds = ["2.45", "3.60", "3.40"]
    r = m.optimize_rounding(odds, m.equal_payout_stakes(odds, 100), "5")
    assert r.stakes == [D(45), D(30), D(35)]
    assert m.money(r.min_profit) == D("-2.00")


@pytest.mark.parametrize("new_a,stake_a,profit", [
    ("2.10", "48.78", "2.44"),
    ("2.05", "49.97", "1.25"),
    ("2.02", "50.71", "0.51"),
    ("2.00", "51.22", "0.00"),
    ("1.95", "52.53", "-1.31"),
    ("1.90", "53.92", "-2.70"),
])
def test_ej6_cuota_cae_tras_primera_pata(new_a, stake_a, profit):
    h = m.hedge_after_partial({"B": ("51.22", "2.00")}, {"A": new_a})
    assert m.money(h.stakes["A"]) == D(stake_a)
    assert m.money(h.guaranteed) == D(profit)


def test_ej7_limite_de_apuesta():
    st = m.equal_payout_stakes(["2.10", "2.00"], 100)
    sc = m.scale_to_limit(st, 0, "30")
    assert [m.money(x) for x in sc] == [D("30.00"), D("31.50")]
    assert m.money(min(m.payouts(["2.10", "2.00"], sc)) - sum(sc)) == D("1.50")


def test_ej8_anulacion_asimetrica_numeros():
    # No es un test del motor: documenta los importes que usa el ejemplo del documento.
    sa, sb = D("48.78"), D("51.22")
    assert m.money(sb * D("2.00")) - sb == D("51.22")
    assert -sb == D("-51.22")
