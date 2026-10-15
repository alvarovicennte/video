"""Tasa de retiradas / walkovers en tenis (datos Jeff Sackmann, espejo archivado, CC BY-NC-SA 4.0).
Clasifica cada partido no completado segun cuantos sets se completaron antes de la retirada.
Uso: python3 -I tennis_retirements.py <dir_datos> <out_dir>
"""
import re
import sys
from pathlib import Path
import pandas as pd

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

LEVELS = {
    "G": "Grand Slam", "M": "Masters 1000", "A": "ATP/WTA 250-500", "F": "Finals",
    "C": "Challenger", "Q": "Qualifying", "S": "ITF", "15": "ITF W15", "25": "ITF W25",
    "35": "ITF W35", "40": "ITF W40", "50": "ITF W50", "60": "ITF W60", "75": "ITF W75",
    "80": "ITF W80", "100": "ITF W100", "P": "WTA Premier", "PM": "WTA Premier Mandatory",
    "I": "WTA International", "D": "Davis/BJK Cup", "O": "Olympics", "W": "WTA 125/250", "T": "Team",
}

SET_RE = re.compile(r"^(\d+)-(\d+)(\(\d+\))?$")

def completed_set(token: str) -> bool:
    m = SET_RE.match(token)
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    hi, lo = max(a, b), min(a, b)
    # set completo: 6-x con diferencia >=2, 7-5, 7-6, o supertiebreak/sets largos (>=6 y diff>=2)
    return (hi >= 6 and hi - lo >= 2) or (hi == 7 and lo in (5, 6)) or (hi >= 10 and hi - lo >= 2)

def classify(score) -> str:
    if not isinstance(score, str) or not score.strip():
        return "sin_dato"
    s = score.strip().upper()
    if "W/O" in s or "WALKOVER" in s:
        return "walkover"
    if "DEF" in s:
        return "descalificacion"
    if "RET" in s or "ABN" in s or "ABD" in s:
        tokens = [t for t in s.replace("RET", "").replace("ABN", "").replace("ABD", "").split() if t]
        n_sets = sum(completed_set(t) for t in tokens)
        return "retirada_con_>=1_set" if n_sets >= 1 else "retirada_sin_set_completo"
    return "completado"

frames = []
for f in sorted(src.glob("*.csv")):
    tour = "ATP" if f.name.startswith("atp") else "WTA"
    circuito = "principal" if re.search(r"_matches_\d{4}\.csv$", f.name) else "qual/challenger/ITF"
    d = pd.read_csv(f, low_memory=False, usecols=["tourney_level", "tourney_date", "score", "surface"])
    d["tour"], d["circuito"] = tour, circuito
    d["year"] = d["tourney_date"].astype(str).str[:4]
    frames.append(d)
df = pd.concat(frames, ignore_index=True)
df = df[~df["tourney_level"].astype(str).isin(["D", "T"])]  # excluir competiciones por equipos
df["resultado"] = df["score"].map(classify)
df = df[df["resultado"] != "sin_dato"]

def pct_table(group_cols):
    t = pd.crosstab([df[c] for c in group_cols], df["resultado"], normalize="index").mul(100).round(2)
    t["partidos"] = df.groupby(group_cols).size()
    return t

print("Resumen por tour y circuito (2019-2026, % de partidos):")
t = pct_table(["tour", "circuito"])
print(t.to_string())
t.to_csv(out / "retiradas_por_tour_circuito.csv")

print("\nPor tour y anio (circuito principal):")
main = df[df["circuito"] == "principal"]
t2 = pd.crosstab([main["tour"], main["year"]], main["resultado"], normalize="index").mul(100).round(2)
t2["partidos"] = main.groupby(["tour", "year"]).size()
print(t2.to_string())
t2.to_csv(out / "retiradas_por_anio_principal.csv")

nc = df["resultado"].isin(["retirada_con_>=1_set", "retirada_sin_set_completo", "walkover", "descalificacion"])
print("\nTotal partidos:", len(df), "| no completados:", int(nc.sum()), f"({100*nc.mean():.2f}%)")
ret = df["resultado"].isin(["retirada_con_>=1_set", "retirada_sin_set_completo"])
print("Retiradas en juego:", int(ret.sum()), f"({100*ret.mean():.2f}% de partidos)")
print("De las retiradas en juego, % con al menos 1 set completado:",
      round(100 * (df["resultado"] == "retirada_con_>=1_set").sum() / ret.sum(), 1))
