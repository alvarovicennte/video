"""Verificacion numerica de los ejemplos del documento (Decimal, precision 28)."""
from decimal import Decimal as D, getcontext, ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING
from itertools import product

getcontext().prec = 28
Q2 = D("0.01")

def r2(x):
    return x.quantize(Q2, rounding=ROUND_HALF_UP)

def pct(x, n=3):
    return (x * 100).quantize(D(10) ** -n, rounding=ROUND_HALF_UP)

def arb(odds, bank):
    S = sum(1 / o for o in odds)
    ret = 1 / S - 1
    stakes = [bank * (1 / o) / S for o in odds]
    payout = bank / S
    return S, ret, stakes, payout

print("== 1. Margen de un mercado 1.90 / 1.90")
S = 1 / D("1.90") + 1 / D("1.90")
print("suma probs implicitas", pct(S, 4), "% -> margen", pct(S - 1, 2), "%")

print("\n== 1b. Margen 1X2 de ejemplo 2.30 / 3.30 / 3.20")
o = [D("2.30"), D("3.30"), D("3.20")]
S = sum(1 / x for x in o)
print("probs implicitas", [pct(1 / x, 2) for x in o], "suma", pct(S, 2), "margen", pct(S - 1, 2))
print("prob 'justa' metodo proporcional", [pct((1 / x) / S, 2) for x in o])

print("\n== 2. Surebet 2 vias: A 2.10 (casa X) / B 2.00 (casa Y), banca 100")
S, ret, st, pay = arb([D("2.10"), D("2.00")], D(100))
print("S", S.quantize(D("0.000001")), "retorno", pct(ret), "%", "stakes", [r2(s) for s in st], "pago", r2(pay))

print("\n== 3. Surebet 1X2: 1 a 2.45 (X) / X a 3.60 (Y) / 2 a 3.40 (Z), banca 100")
S, ret, st, pay = arb([D("2.45"), D("3.60"), D("3.40")], D(100))
print("S", S.quantize(D("0.000001")), "retorno", pct(ret), "%", "stakes", [r2(s) for s in st], "pago", r2(pay))
odds3 = [D("2.45"), D("3.60"), D("3.40")]

def best_rounding(odds, ideal, step):
    best = None
    cands = []
    for s in ideal:
        lo = (s / step).to_integral_value(rounding=ROUND_FLOOR) * step
        hi = (s / step).to_integral_value(rounding=ROUND_CEILING) * step
        cands.append(sorted({lo, hi}))
    for combo in product(*cands):
        total = sum(combo)
        pays = [c * o for c, o in zip(combo, odds)]
        minprof = min(pays) - total
        roi = minprof / total
        key = (roi, minprof)
        if best is None or key > best[0]:
            best = (key, combo, pays, total)
    return best

print("\n== 4. Redondeo (2 vias, ideal 48.78 / 51.22)")
_, _, ideal2, _ = arb([D("2.10"), D("2.00")], D(100))
for step in (D("0.01"), D("1"), D("5")):
    naive = [(s / step).to_integral_value(rounding=ROUND_HALF_UP) * step for s in ideal2]
    pays = [n * o for n, o in zip(naive, [D("2.10"), D("2.00")])]
    total = sum(naive)
    print(f"paso {step}: redondeo simple {naive} total {total} pagos {[r2(p) for p in pays]} beneficio minimo {r2(min(pays)-total)} ({pct((min(pays)-total)/total,2)}%)")
    (roi, mp), combo, pays, total = best_rounding([D("2.10"), D("2.00")], ideal2, step)
    print(f"        optimo floor/ceil {list(combo)} total {total} pagos {[r2(p) for p in pays]} beneficio minimo {r2(mp)} ({pct(roi,2)}%)")

print("\n== 4b. Redondeo 1X2 (ideal)", [r2(s) for s in arb(odds3, D(100))[2]])
for step in (D("1"), D("5")):
    _, _, ideal3, _ = arb(odds3, D(100))
    naive = [(s / step).to_integral_value(rounding=ROUND_HALF_UP) * step for s in ideal3]
    pays = [n * o for n, o in zip(naive, odds3)]
    total = sum(naive)
    print(f"paso {step}: simple {naive} total {total} pagos {[r2(p) for p in pays]} benef. min {r2(min(pays)-total)} ({pct((min(pays)-total)/total,2)}%)")
    (roi, mp), combo, pays, total = best_rounding(odds3, ideal3, step)
    print(f"        optimo {list(combo)} total {total} pagos {[r2(p) for p in pays]} benef. min {r2(mp)} ({pct(roi,2)}%)")

print("\n== 5. Comision exchange sobre ganancia neta: cuota efectiva = 1 + (o-1)(1-c)")
for c in (D("0.02"), D("0.05")):
    print(f"c={pct(c,0)}%: back 2.10 -> efectiva {(1 + (D('2.10')-1)*(1-c)).quantize(D('0.0001'))}")

print("\n== 6. Back (casa) / Lay (exchange): B=2.20, L=2.10, back 100")
for c in (D("0.02"), D("0.05")):
    B, L, sb = D("2.20"), D("2.10"), D(100)
    sl = sb * B / (L - c)
    liab = sl * (L - 1)
    win_back = sb * (B - 1) - liab
    win_lay = sl * (1 - c) - sb
    print(f"c={pct(c,0)}%: lay stake {r2(sl)} responsabilidad {r2(liab)} | gana back: {r2(win_back)} | gana lay: {r2(win_lay)} | ROI sobre back {pct(win_lay/sb,2)}% | sobre capital inmovilizado (back+resp.) {pct(win_lay/(sb+liab),2)}%")
    print(f"        condicion de arbitraje B(1-c) > L-c : {B*(1-c)} > {L-c} -> {B*(1-c) > L-c}")

print("\n== 7. Cuota que cae tras colocar la primera pata (B colocada a 2.00 con 51.22)")
sB = D("51.22")
for newA in (D("2.10"), D("2.05"), D("2.02"), D("2.00"), D("1.95"), D("1.90")):
    # cubrir para igualar el resultado si gana A: sA * newA = sB*2.00 ... buscamos minimizar perdida: igualar pagos
    payout_B = sB * D("2.00")
    sA = payout_B / newA
    total = sA + sB
    prof = payout_B - total
    print(f"A cae a {newA}: stake A {r2(sA)} total {r2(total)} resultado garantizado {r2(prof)} ({pct(prof/total,2)}%)")

print("\n== 8. Anulacion asimetrica (tenis): A en X (anula si no se completa), B en Y (vale con 1 set)")
sA, sB, oA, oB = D("48.78"), D("51.22"), D("2.10"), D("2.00")
print("se retira A tras 1 set: X devuelve", sA, "; Y paga B", r2(sB*oB), "-> neto", r2(sA + sB*oB - sA - sB))
print("se retira B tras 1 set: X devuelve", sA, "; Y pierde B -> neto", r2(sA - sA - sB))
print("partido completado: neto", r2(min(sA*oA, sB*oB) - sA - sB), "(minimo)")

print("\n== 9. Limite de apuesta: maximo 30 EUR aceptado en la pata A (2.10)")
S, ret, st, pay = arb([D("2.10"), D("2.00")], D(100))
scale = D(30) / st[0]
print("banca maxima", r2(D(100)*scale), "stakes", [r2(s*scale) for s in st], "beneficio", r2((pay-100)*scale))

print("\n== 10. Impuestos: retorno bruto 2,0% con tipo marginal IRPF 30% sobre ganancia neta anual")
print("retorno neto aprox.", pct(D("0.02")*(1-D("0.30")),2), "%")
