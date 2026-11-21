"""Analyse des gaps (écarts entre apparitions), IMPLEMENTATION_SPEC §17-18, Cahier §14, H004.

Sous H0, la présence/absence d'un numéro fixé est i.i.d. Bernoulli(p) d'un tirage à l'autre (les
tirages sont indépendants — même argument que pour les tests binomiaux exacts de la Phase 4). Le
temps d'attente entre deux apparitions suit alors EXACTEMENT une loi géométrique de paramètre p :
aucune simulation n'est nécessaire pour la loi de référence du test réel (contrairement au test
joint des 6 numéros de la Phase 3, où la corrélation intra-tirage empêche une solution exacte simple).
"""
import numpy as np
import pandas as pd

from loto_research.statistics.uniformity import chi_square_uniformity
from loto_research.validation.schema import MAIN_MAX, MAIN_MIN


def observed_gaps_for_number(df, columns, number):
    """Gaps INTÉRIEURS (entre deux apparitions consécutives) de `number` dans `columns`, en nombre
    de tirages du dataset (différence de chronological_id). Les gaps ouverts en début/fin de série
    (avant la première apparition, après la dernière) sont exclus — convention usuelle en survie.
    """
    d = df.sort_values("chronological_id")
    present = d[columns].apply(lambda row: number in row.values, axis=1).to_numpy()
    positions = d["chronological_id"].to_numpy()[present]
    if len(positions) < 2:
        return np.array([], dtype=int)
    return np.diff(positions)


def geometric_gap_pmf(p, max_k):
    """P(gap = k) pour k=1..max_k (loi géométrique). La dernière valeur regroupe toute la queue
    restante P(gap >= max_k) pour que la somme fasse exactement 1 sur un support tronqué."""
    k = np.arange(1, max_k + 1)
    pmf = (1 - p) ** (k - 1) * p
    pmf[-1] += 1 - pmf.sum()
    return k, pmf


def compare_gaps_to_geometric(gaps, p, max_k=30, min_expected=5):
    """χ² d'adéquation entre les gaps observés et la loi géométrique EXACTE de paramètre p.

    Nom volontairement SANS préfixe `test_` : pytest découvre toute fonction ainsi préfixée dans
    un fichier tests/, y compris importée — un nom `test_...` ici serait pris pour un test.
    """
    k, pmf = geometric_gap_pmf(p, max_k)
    obs_counts = np.array([(gaps == kk).sum() for kk in k[:-1]] + [(gaps >= k[-1]).sum()])
    exp_counts = pmf * len(gaps)
    return chi_square_uniformity(obs_counts, exp_counts, min_expected=min_expected)


def per_number_gap_test(df, columns, p, universe=range(MAIN_MIN, MAIN_MAX + 1), max_k=30, min_expected=5):
    """Test des gaps pour chaque numéro de `universe` (test PRIMAIRE de H004, avec FDR-BH à
    appliquer sur la colonne p_value en sortie, IMPLEMENTATION_SPEC A2/HYPOTHESES.md H004)."""
    rows = []
    for number in universe:
        gaps = observed_gaps_for_number(df, columns, number)
        res = compare_gaps_to_geometric(gaps, p, max_k=max_k, min_expected=min_expected) if len(gaps) >= 10 else None
        rows.append({
            "number": number, "n_gaps": len(gaps),
            "mean_gap": float(gaps.mean()) if len(gaps) else float("nan"),
            "theoretical_mean_gap": 1 / p,
            "p_value": res["p_value"] if res else float("nan"),
        })
    return pd.DataFrame(rows)
