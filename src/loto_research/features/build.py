"""Construction du dataset supervisé (chronological_id, number) -> target (Cahier §25-31,
IMPLEMENTATION_SPEC §29-31).

RÈGLE ABSOLUE (IMPLEMENTATION_SPEC §30) : toute feature à l'indice t est calculée UNIQUEMENT avec
des données d'indice < t. Chaque fonction ci-dessous est écrite pour que la valeur au temps t
n'utilise jamais presence[t] / draw[t] lui-même — vérifié séparément par leakage.py.
"""
import numpy as np
import pandas as pd

from loto_research.temporal.autocorrelation import build_presence_matrix
from loto_research.validation.schema import NUMBER_COLUMNS

DEFAULT_WINDOWS = (10, 20, 50, 100, 250)


def rolling_frequency_matrix(presence, windows):
    """Pour chaque k, freq[t] = somme de presence[max(0,t-k) : t] (EXCLUT t). Retourne
    {k: array (n_draws, 49)}."""
    n_draws, n_numbers = presence.shape
    cum = np.vstack([np.zeros((1, n_numbers), dtype=int), np.cumsum(presence, axis=0)])
    idx = np.arange(n_draws)
    out = {}
    for k in windows:
        start = np.maximum(idx - k, 0)
        out[k] = cum[idx] - cum[start]
    return out


def gap_current_matrix(presence):
    """gap[t,i] = nombre de tirages depuis la dernière apparition de i AVANT t (sentinelle -1 si
    jamais apparu avant t). Boucle simple (n_draws*49 ≈ 150k itérations, trivial en performance),
    plus sûre à relire/tester qu'une vectorisation complexe."""
    n_draws, n_numbers = presence.shape
    out = np.full((n_draws, n_numbers), -1, dtype=int)
    last_seen = np.full(n_numbers, -1, dtype=int)
    for t in range(n_draws):
        out[t] = np.where(last_seen >= 0, t - last_seen, -1)
        last_seen = np.where(presence[t] == 1, t, last_seen)
    return out


def draw_level_lag_features(df, columns=NUMBER_COLUMNS):
    """Contexte du tirage PRÉCÉDENT (décalé d'un cran) : somme, parité, bas/haut du tirage t-1, et
    chevauchement entre les tirages t-2 et t-1. Répété à l'identique sur les 49 lignes du tirage t."""
    d = df.sort_values("chronological_id").reset_index(drop=True)
    n = len(d)
    sums = d[columns].sum(axis=1).to_numpy()
    odd_counts = d[columns].apply(lambda row: int(sum(v % 2 == 1 for v in row)), axis=1).to_numpy()
    low_counts = d[columns].apply(lambda row: int(sum(v <= 24 for v in row)), axis=1).to_numpy()
    masks = [int(sum(1 << int(v) for v in row)) for row in d[columns].to_numpy()]

    prev_sum = np.full(n, np.nan)
    prev_odd_count = np.full(n, np.nan)
    prev_low_count = np.full(n, np.nan)
    prev_overlap = np.full(n, np.nan)
    if n > 1:
        prev_sum[1:] = sums[:-1]
        prev_odd_count[1:] = odd_counts[:-1]
        prev_low_count[1:] = low_counts[:-1]
    for t in range(2, n):
        prev_overlap[t] = (masks[t - 1] & masks[t - 2]).bit_count()

    return pd.DataFrame({
        "chronological_id": d["chronological_id"].to_numpy(),
        "prev_sum": prev_sum, "prev_odd_count": prev_odd_count,
        "prev_low_count": prev_low_count, "prev_overlap": prev_overlap,
    })


def build_feature_dataset(df, windows=DEFAULT_WINDOWS):
    """Construit le panel (chronological_id, number) -> target. 49 lignes par tirage.

    Dépendance structurelle à documenter (IMPLEMENTATION_SPEC §29) : pour un chronological_id
    donné, la somme des `target` sur les 49 lignes vaut EXACTEMENT 6 (6 numéros tirés par tirage) —
    les 49 observations d'un même tirage ne sont donc PAS indépendantes entre elles.
    """
    d = df.sort_values("chronological_id").reset_index(drop=True)
    n_draws = len(d)
    presence = build_presence_matrix(d, NUMBER_COLUMNS)
    freq = rolling_frequency_matrix(presence, windows)
    gap = gap_current_matrix(presence)
    lag_df = draw_level_lag_features(d, NUMBER_COLUMNS)
    chron_ids = d["chronological_id"].to_numpy()

    rows = []
    for t in range(n_draws):
        base = {
            "prev_sum": lag_df["prev_sum"].iloc[t], "prev_odd_count": lag_df["prev_odd_count"].iloc[t],
            "prev_low_count": lag_df["prev_low_count"].iloc[t], "prev_overlap": lag_df["prev_overlap"].iloc[t],
        }
        for num_idx in range(49):
            row = {"chronological_id": int(chron_ids[t]), "number": num_idx + 1,
                   "target": int(presence[t, num_idx]), "gap_current": int(gap[t, num_idx])}
            for k in windows:
                row[f"freq_last_{k}"] = int(freq[k][t, num_idx])
            row.update(base)
            rows.append(row)
    return pd.DataFrame(rows)
