"""Motor universal: LP exacto sobre escenarios."""
from fractions import Fraction as F

from hypothesis import given, settings, strategies as st

from surebet.engine import arb_math as m
from surebet.engine.lp import best_cover, simplex_max
from surebet.engine.scenarios import Bet, build_matrix, compact, payoff, back_results_score
from surebet.universal import analyse_event, scan_bets, round_legs, Opportunity


def b(book, market, outcome, odds, line=None, side="BACK", k="0", rule="UNKNOWN"):
    return Bet(book, market, outcome, F(odds), F(line) if line is not None else None, side, F(k), rule)


def solve(model, bets, retire=True):
    s, R = build_matrix(model, bets, retire)
    s, R, _ = compact(s, R)
    return best_cover(R)


def test_simplex_basico():
    val, x, y = simplex_max([F(3), F(5)], [[F(1), F(0)], [F(0), F(2)], [F(3), F(2)]], [F(4), F(12), F(18)])
    assert val == 36 and x == [2, 6]


def test_lp_igual_a_S_en_mercado_simple():
    c = solve("winner", [b("X", "WINNER", "P1", "2.10"), b("Y", "WINNER", "P2", "2.00")], retire=False)
    assert c.value == F(1) / F("2.10") + F(1) / F("2.00")
    assert [round(float(v), 4) for v in c.stakes] == [0.4762, 0.5]


@settings(max_examples=200, deadline=None)
@given(st.lists(st.decimals(min_value="1.05", max_value="15", places=2), min_size=3, max_size=3))
def test_lp_1x2_coincide_con_motor_clasico(odds):
    bets = [b(f"c{i}", "1X2", o, str(x)) for i, (o, x) in enumerate(zip(["HOME", "DRAW", "AWAY"], odds))]
    c = solve("score", bets)
    assert c.value == sum(F(1) / F(str(x)) for x in odds)
    assert c.is_arbitrage == m.has_arbitrage([str(x) for x in odds])


def test_arbitraje_entre_mercados_dnb_mas_doble_oportunidad():
    bets = [b("A", "DNB", "HOME", "1.80"), b("B", "DC", "X2", "2.40")]
    c = solve("score", bets)
    assert c.value == F(1) / F("1.80") + F(1) / F("2.40")
    assert c.is_arbitrage


def test_tenis_reglas_distintas_no_es_arbitraje_robusto():
    bets = [b("bet365", "WINNER", "P1", "2.10", rule="MATCH_COMPLETED"), b("Y", "WINNER", "P2", "2.00", rule="ONE_SET")]
    assert solve("winner", bets).value == F(3, 2)
    assert solve("winner", bets, retire=False).is_arbitrage   # solo sin retiradas: fragil


def test_tenis_misma_regla_es_robusto():
    bets = [b("X", "WINNER", "P1", "2.10", rule="ONE_SET"), b("Y", "WINNER", "P2", "2.00", rule="ONE_SET")]
    c = solve("winner", bets)
    assert c.is_arbitrage and c.value == F(1) / F("2.10") + F(1) / F("2.00")


def test_regla_desconocida_se_trata_como_peor_caso():
    bets = [b("X", "WINNER", "P1", "2.10", rule="UNKNOWN"), b("Y", "WINNER", "P2", "2.00", rule="UNKNOWN")]
    assert solve("winner", bets) is None or not solve("winner", bets).is_arbitrage


def test_linea_entera_con_devolucion():
    bets = [b("X", "TOTAL", "OVER", "2.10", line="2"), b("Y", "TOTAL", "UNDER", "2.00", line="2")]
    c = solve("score", bets)
    assert c.is_arbitrage and c.value == F(1) / F("2.10") + F(1) / F("2.00")


def test_linea_de_cuarto_media_ganada():
    bet = b("X", "AH", "HOME", "2.00", line="-0.25")
    assert payoff(bet, back_results_score(bet, 1, 1)) == F(1, 2)     # empate: mitad perdida, mitad devuelta
    assert payoff(bet, back_results_score(bet, 2, 1)) == F(2)
    bet2 = b("X", "TOTAL", "OVER", "2.00", line="2.75")
    assert payoff(bet2, back_results_score(bet2, 2, 1)) == F(3, 2)   # 3 goles: mitad gana, mitad devuelta


def test_lay_coincide_con_back_lay_clasico():
    bets = [b("casa", "WINNER", "P1", "2.20"), b("exchange", "WINNER", "P1", "2.10", side="LAY", k="0.02")]
    c = solve("winner", bets, retire=False)
    B, L, k = F("2.20"), F("2.10"), F("0.02")
    lay = 100 * B / (L - k)
    liability = lay * (L - 1)
    roi_capital = (lay * (1 - k) - 100) / (100 + liability)
    assert c.guaranteed_return == roi_capital                 # mismo numero exacto que el ejemplo 5 (1,69 %)


ODDS = st.sampled_from(["1.50", "1.80", "1.95", "2.05", "2.30", "3.10", "3.60", "4.50"])
BETS = st.one_of(
    st.builds(lambda o, x: b("a", "1X2", o, x), st.sampled_from(["HOME", "DRAW", "AWAY"]), ODDS),
    st.builds(lambda o, x: b("b", "DC", o, x), st.sampled_from(["1X", "X2", "12"]), ODDS),
    st.builds(lambda o, x: b("c", "DNB", o, x), st.sampled_from(["HOME", "AWAY"]), ODDS),
    st.builds(lambda o, x, ln: b("d", "AH", o, x, line=ln), st.sampled_from(["HOME", "AWAY"]), ODDS,
              st.sampled_from(["-1.5", "-1", "-0.75", "-0.25", "0", "0.25", "0.5", "1", "1.25"])),
    st.builds(lambda o, x, ln: b("e", "TOTAL", o, x, line=ln), st.sampled_from(["OVER", "UNDER"]), ODDS,
              st.sampled_from(["0.5", "1.75", "2", "2.25", "2.5", "3", "3.5"])),
    st.builds(lambda o, x: b("f", "BTTS", o, x), st.sampled_from(["YES", "NO"]), ODDS),
)


@settings(max_examples=60, deadline=None)
@given(st.lists(BETS, min_size=2, max_size=6))
def test_estados_representativos_equivalen_a_todos_los_marcadores(bets):
    s, R = build_matrix("score", bets)
    s, R, _ = compact(s, R)
    full = [(h, a) for h in range(13) for a in range(13)]
    Rf = [[payoff(x, back_results_score(x, h, a)) for (h, a) in full] for x in bets]
    keep = [i for i in range(len(full)) if not all(Rf[j][i] == 1 for j in range(len(bets)))]
    Rf = [[row[i] for i in keep] for row in Rf]
    c1 = best_cover(R) if s else None
    c2 = best_cover(Rf) if keep else None
    assert (c1 is None) == (c2 is None)
    if c1:
        assert c1.value == c2.value


def test_escaner_csv_y_redondeo():
    rows = [
        {"event_id": "E1", "event_name": "A-B", "sport": "football", "period": "REG_90", "market": "1X2", "line": "", "outcome": o,
         "side": "BACK", "book": bk, "odds": x, "commission": "0", "rule": ""}
        for o, bk, x in [("HOME", "X", "2.45"), ("DRAW", "Y", "3.60"), ("AWAY", "Z", "3.40"), ("HOME", "Z", "2.30")]
    ]
    opps = scan_bets(rows)
    assert len(opps) == 1
    assert opps[0].value == F(1) / F("2.45") + F(1) / F("3.60") + F(1) / F("3.40")
    stakes, total, worst = round_legs(opps[0], "score", F(100), F(1), False)
    by_outcome = {leg.outcome: s for (leg, _), s in zip(opps[0].legs, stakes)}
    assert by_outcome == {"HOME": 41, "DRAW": 28, "AWAY": 30}
    assert total == 99 and worst == F("1.45")
