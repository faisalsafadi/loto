"""Dépendance entre tirages consécutifs (H003). Amendements A2 (test primaire), A3 (permutation
de l'ordre), A5 (filtre des vrais tirages consécutifs, ~33 tirages numérotés absents du RAW)."""
import time

import numpy as np
from scipy.stats import hypergeom

from loto_research.validation.schema import NUMBER_COLUMNS


def build_consecutive_mask(df, max_date_gap_days=4):
    """Amendement A5 : la paire (i, i+1) est un VRAI tirage consécutif si le numéro de tirage suit
    (N[i+1] = N[i]+1, ou N[i+1] = 1 en cas de remise à zéro de la numérotation) ET si l'écart de
    dates est <= max_date_gap_days. Retourne un booléen de longueur len(df)-1."""
    d = df.sort_values("chronological_id").reset_index(drop=True)
    n = d["draw_number_source"].to_numpy()
    dates = d["date"].to_numpy()
    n_ok = (n[1:] == n[:-1] + 1) | (n[1:] == 1)
    gap_days = (dates[1:] - dates[:-1]) / np.timedelta64(1, "D")
    date_ok = gap_days <= max_date_gap_days
    return n_ok & date_ok


def draws_to_bitmasks(df, columns=NUMBER_COLUMNS):
    """Encode chaque tirage en un entier (bit i = 1 si le numéro i+1 est présent) : une intersection
    devient un ET binaire + comptage de bits, bien plus rapide en boucle qu'un frozenset Python."""
    d = df.sort_values("chronological_id").reset_index(drop=True)
    arr = d[columns].to_numpy()
    return [int(sum(1 << int(v) for v in row)) for row in arr]


def observed_mean_intersection(masks, valid_mask):
    valid_idx = np.nonzero(valid_mask)[0]
    total = sum((masks[i] & masks[i + 1]).bit_count() for i in valid_idx)
    return total / len(valid_idx), len(valid_idx)


def permutation_test_mean_intersection(masks, valid_mask, n_permutations, seed, progress=True):
    """Amendement A3 : loi nulle EXACTE par permutation de l'ordre des CONTENUS des tirages — le
    calendrier réel (donc valid_mask, basé sur dates/numéros) reste fixe d'une permutation à l'autre.
    H0 : aucune dépendance temporelle entre le contenu d'un tirage et sa position chronologique.
    """
    rng = np.random.default_rng(seed)
    valid_idx = np.nonzero(valid_mask)[0]
    n = len(masks)
    observed, n_valid_pairs = observed_mean_intersection(masks, valid_mask)

    null_stats = np.empty(n_permutations)
    t0 = time.time()
    for k in range(n_permutations):
        order = rng.permutation(n)
        total = sum((masks[order[i]] & masks[order[i + 1]]).bit_count() for i in valid_idx)
        null_stats[k] = total / n_valid_pairs
        if progress and (k + 1) % max(1, n_permutations // 20) == 0:
            print(f"  Permutation H003 : {k + 1}/{n_permutations} ({time.time() - t0:.1f}s)", end="\r")
    if progress:
        print()
    p_value = (float((null_stats >= observed).sum()) + 1) / (n_permutations + 1)
    return {
        "observed_mean_intersection": observed, "n_valid_pairs": n_valid_pairs,
        "p_value_permutation": p_value, "expected_under_h0": float(null_stats.mean()),
        "std_under_h0": float(null_stats.std(ddof=1)), "n_permutations": n_permutations, "seed": seed,
    }


def intersection_size_distribution(masks, valid_mask):
    """Distribution DESCRIPTIVE des tailles d'intersection (0..6) sur les paires valides (A5),
    comparée à la loi EXACTE de deux tirages 6/49 INDÉPENDANTS (hypergéométrique : fixer un tirage,
    l'autre est un tirage sans remise de 6 parmi 49 dont 6 sont des "succès"). Secondaire par
    rapport au test primaire (la moyenne, testée par permutation ci-dessus)."""
    valid_idx = np.nonzero(valid_mask)[0]
    sizes = np.array([(masks[i] & masks[i + 1]).bit_count() for i in valid_idx])
    k = np.arange(0, 7)
    exp_p = hypergeom.pmf(k, 49, 6, 6)
    obs_counts = np.array([(sizes == kk).sum() for kk in k])
    return {
        "k": k.tolist(), "observed_counts": obs_counts.tolist(),
        "expected_counts": (exp_p * len(sizes)).tolist(), "n_pairs": int(len(sizes)),
    }
