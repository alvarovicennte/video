"""Frecuencia de arbitrajes 'aparentes' con cuotas maximas de mercado (football-data.co.uk via mirror xgabora).
Uso: python3 -I apparent_arbs_football.py <Matches.csv> <out_dir>
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(src, low_memory=False)
df["date"] = pd.to_datetime(df["MatchDate"])
# temporada europea: julio-junio
df["season"] = np.where(df["date"].dt.month >= 7, df["date"].dt.year, df["date"].dt.year - 1)

m = df.dropna(subset=["MaxHome", "MaxDraw", "MaxAway"]).copy()
m = m[(m[["MaxHome", "MaxDraw", "MaxAway"]] > 1.0).all(axis=1)]
m["S_1x2_max"] = 1 / m["MaxHome"] + 1 / m["MaxDraw"] + 1 / m["MaxAway"]
m["ret_1x2_max"] = 1 / m["S_1x2_max"] - 1

b = df.dropna(subset=["OddHome", "OddDraw", "OddAway"]).copy()
b = b[(b[["OddHome", "OddDraw", "OddAway"]] > 1.0).all(axis=1)]
b["margin_b365"] = 1 / b["OddHome"] + 1 / b["OddDraw"] + 1 / b["OddAway"] - 1

o = df.dropna(subset=["MaxOver25", "MaxUnder25"]).copy()
o = o[(o[["MaxOver25", "MaxUnder25"]] > 1.0).all(axis=1)]
o["S_ou_max"] = 1 / o["MaxOver25"] + 1 / o["MaxUnder25"]

def summary(frame, col, label):
    s = frame[col]
    return {
        "mercado": label,
        "partidos": len(s),
        "pct_S<1": round(100 * (s < 1).mean(), 2),
        "pct_S<0.99 (>=1,01% retorno)": round(100 * (s < 0.99).mean(), 2),
        "pct_S<0.98 (>=2,04% retorno)": round(100 * (s < 0.98).mean(), 2),
        "pct_S<0.95 (>=5,26% retorno; sospechoso)": round(100 * (s < 0.95).mean(), 3),
        "mediana_S": round(s.median(), 4),
    }

rows = [summary(m, "S_1x2_max", "1X2 todas las ligas"), summary(o, "S_ou_max", "O/U 2,5 todas las ligas")]
for div, name in [("SP1", "LaLiga"), ("E0", "Premier League"), ("SP2", "Segunda Division")]:
    rows.append(summary(m[m["Division"] == div], "S_1x2_max", f"1X2 {name}"))
    rows.append(summary(o[o["Division"] == div], "S_ou_max", f"O/U 2,5 {name}"))
overall = pd.DataFrame(rows)
print(overall.to_string(index=False))
overall.to_csv(out / "resumen_global.csv", index=False)

# evolucion por temporada (todas las ligas) y LaLiga
def by_season(frame, col, div=None):
    f = frame if div is None else frame[frame["Division"] == div]
    g = f.groupby("season")[col]
    return pd.DataFrame({
        "partidos": g.size(),
        "pct_S<1": (g.apply(lambda s: (s < 1).mean()) * 100).round(2),
        "pct_S<0.99": (g.apply(lambda s: (s < 0.99).mean()) * 100).round(2),
        "mediana_S": g.median().round(4),
    })

t1 = by_season(m, "S_1x2_max")
t2 = by_season(o, "S_ou_max")
t3 = by_season(m, "S_1x2_max", "SP1")
mb = b.groupby("season")["margin_b365"].median().mul(100).round(2).rename("margen_mediano_b365_%")
print("\n1X2 max (todas las ligas) por temporada + margen mediano Bet365:")
print(t1.join(mb).to_string())
print("\nO/U 2,5 max (todas las ligas) por temporada:")
print(t2.to_string())
print("\n1X2 max LaLiga por temporada:")
print(t3.to_string())
t1.join(mb).to_csv(out / "por_temporada_1x2.csv")
t2.to_csv(out / "por_temporada_ou25.csv")
t3.to_csv(out / "por_temporada_1x2_laliga.csv")

# margen Bet365 por liga (ultimas 3 temporadas completas)
recent = b[b["season"].between(2022, 2024)]
ml = recent.groupby("Division")["margin_b365"].median().mul(100).round(2).sort_values()
print("\nMargen mediano Bet365 1X2 por division (temporadas 2022-2024):")
print(ml.to_string())
ml.to_csv(out / "margen_b365_por_division_2022_2024.csv")

# casos extremos (posibles errores de datos)
ext = m[m["S_1x2_max"] < 0.90][["Division", "MatchDate", "HomeTeam", "AwayTeam", "MaxHome", "MaxDraw", "MaxAway", "S_1x2_max"]]
print("\nCasos S<0.90 (retorno aparente >11%):", len(ext))
print(ext.sort_values("S_1x2_max").head(10).to_string(index=False))
