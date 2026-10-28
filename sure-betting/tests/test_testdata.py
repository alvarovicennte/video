"""Los datos sinteticos tienen la verdad que dicen tener."""
from collections import defaultdict
from decimal import Decimal as D

from surebet import testdata
from surebet.engine import arb_math as m


def _by_event(rows):
    ev = defaultdict(list)
    for r in rows:
        ev[r["event_id"]].append(r)
    return ev


def test_determinista():
    assert testdata.generate(7, 50) == testdata.generate(7, 50)
    assert testdata.generate(7, 50) != testdata.generate(8, 50)


def test_todos_los_escenarios_presentes():
    assert {r["scenario"] for r in testdata.generate(7, 50)} == set(testdata.SCENARIOS)


def test_arbitrajes_plantados_son_arbitrajes_reales():
    rows = testdata.generate(7, 100)
    planted = 0
    for ev, rs in _by_event(rows).items():
        if rs[0]["scenario"] != "arb":
            continue
        outs = {r["outcome"] for r in rs}
        best = {o: max(D(r["odds"]) for r in rs if r["outcome"] == o) for o in outs}
        s = m.arbitrage_sum(list(best.values()))
        assert (s < 1) == (rs[0]["expected_arb"] == "true")
        planted += s < 1
    assert planted >= 5


def test_no_arb_no_tiene_arbitraje_con_mejor_cuota_valida():
    for ev, rs in _by_event(testdata.generate(7, 100)).items():
        if rs[0]["scenario"] != "no_arb":
            continue
        outs = {r["outcome"] for r in rs}
        best = {o: max(D(r["odds"]) for r in rs if r["outcome"] == o) for o in outs}
        assert m.arbitrage_sum(list(best.values())) >= 1


def test_trampas_marcadas_como_no_esperadas():
    for r in testdata.generate(7, 100):
        if r["scenario"].startswith("trap_") or r["scenario"] == "no_arb":
            assert r["expected_arb"] == "false"


def test_csv(tmp_path):
    p = tmp_path / "x.csv"
    n = testdata.write_csv(p, 7, 10)
    assert n == len(p.read_text(encoding="utf-8").strip().splitlines()) - 1
