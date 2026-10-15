"""Simulacion: efecto de combinar casas con reglas de retirada distintas en surebets de tenis.
Supuestos: surebet 2.10/2.00 con 100 EUR (beneficio 2.44); con prob p el partido acaba en retirada
con >=1 set completado; quien se retira es 50/50; resultado de esa apuesta +/-51.22 EUR.
Uso: python3 -I asym_void_sim.py
"""
import random

def simulate(n_arbs, p_ret, trials=200_000, seed=7):
    rng = random.Random(seed)
    neg = 0
    totals = []
    for _ in range(trials):
        total = 0.0
        for _ in range(n_arbs):
            if rng.random() < p_ret:
                total += 51.22 if rng.random() < 0.5 else -51.22
            else:
                total += 2.44
        totals.append(total)
        neg += total < 0
    totals.sort()
    mean = sum(totals) / trials
    p5 = totals[int(0.05 * trials)]
    return mean, p5, neg / trials

for n in (50, 200):
    for p in (0.0227, 0.0291):
        mean, p5, pneg = simulate(n, p, trials=50_000)
        print(f"n={n:3d} surebets, p_retirada_con_set={p:.2%}: media {mean:7.1f} EUR | percentil 5 {p5:7.1f} EUR | P(total<0) {pneg:.1%} | sin riesgo asimetrico: {n*2.44:.1f} EUR")
