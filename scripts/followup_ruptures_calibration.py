#!/usr/bin/env python3
"""Suivi de l'addendum Phase 5 : (1) convertit les indices de rupture ruptures.Pelt en dates
reelles, (2) calibre la methode (meme regle de penalite) sur du bruit pur pour savoir si 4
ruptures sur le complementaire est surprenant ou attendu meme sous H0. Lecture seule sur
l'ANALYTIC ; aucune modification.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from loto_research.temporal.changepoint import ruptures_pelt_breakpoints

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
N_CALIBRATION_REPS = 5000

df = pd.read_parquet(ROOT / "data/analytic/draws.parquet").sort_values("chronological_id").reset_index(drop=True)
n_draws = len(df)

bkps = [255, 530, 1800, 1875]
print("=== Conversion indice -> date reelle (complementaire) ===")
for idx in bkps:
    d = df["date"].iloc[idx]
    print(f"  indice {idx:4d} -> {d.date()}  (annee {d.year})")

print(f"\n=== Calibration : ruptures.Pelt sur bruit pur ({N_CALIBRATION_REPS} repetitions) ===")
print("Meme regle de penalite (log(n)*variance), memes n_draws, valeurs uniformes 1..49 avec remise.")
rng = np.random.default_rng(SEED)
n_bkps_null = np.empty(N_CALIBRATION_REPS, dtype=int)
for i in range(N_CALIBRATION_REPS):
    synthetic = rng.integers(1, 50, size=n_draws)
    res = ruptures_pelt_breakpoints(synthetic)
    n_bkps_null[i] = len(res.get("breakpoints", [])) if "error" not in res else -1

if (n_bkps_null == -1).any():
    print(f"  ATTENTION : {(n_bkps_null == -1).sum()} repetitions ont echoue (voir erreur ruptures.Pelt).")
valid = n_bkps_null[n_bkps_null >= 0]
print(f"  Nombre de ruptures trouvees sous bruit pur : moyenne={valid.mean():.2f}, "
      f"mediane={np.median(valid):.0f}, max={valid.max()}, "
      f"P(>=4 ruptures sous H0) = {(valid >= 4).mean():.4f}")
vals, counts = np.unique(valid, return_counts=True)
print(f"  Distribution : {dict(zip(vals.tolist(), counts.tolist()))}")
