import sys
import numpy as np
import pandas as pd
df = pd.read_csv(sys.argv[1], low_memory=False)
df["date"] = pd.to_datetime(df["MatchDate"])
df["season"] = np.where(df["date"].dt.month >= 7, df["date"].dt.year, df["date"].dt.year - 1)
d = df.dropna(subset=["OddHome", "MaxHome", "OddDraw", "MaxDraw", "OddAway", "MaxAway"])
d = d.assign(eqH=(d["MaxHome"] <= d["OddHome"] + 1e-9), gapH=(d["MaxHome"] / d["OddHome"] - 1))
g = d.groupby("season")
print(pd.DataFrame({"n": g.size(), "pct_max_igual_b365": (g["eqH"].mean() * 100).round(1), "gap_medio_max_vs_b365_%": (g["gapH"].mean() * 100).round(2), "n_divisiones": g["Division"].nunique()}).to_string())
