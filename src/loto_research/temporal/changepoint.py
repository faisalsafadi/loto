"""Détection de rupture (Cahier des charges §19). Deux méthodes, à dessein redondantes :

1. CUSUM auto-écrit + permutation (test PRIMAIRE de cet addendum) : formule simple, entièrement
   testée à la main ci-dessous (tests/test_changepoint_autocorr.py).
2. ruptures.Pelt (bibliothèque tierce) : recoupement DESCRIPTIF uniquement, aucune p-value calculée
   pour sa pénalité (non calibrée) — sert à corroborer visuellement le CUSUM, pas à décider seul.
"""
import time

import numpy as np
from scipy.stats import norm


def cusum_single_changepoint(signal):
    """CUSUM pour une rupture unique dans la MOYENNE. Retourne l'indice le plus probable de rupture
    (position APRÈS laquelle la moyenne change), la statistique |S_k| maximale, et les moyennes
    avant/après. N'importe quel autre type de changement (variance, forme) n'est PAS détecté ici.
    """
    x = np.asarray(signal, dtype=float)
    n = len(x)
    mu = x.mean()
    s = np.cumsum(x - mu)
    k = int(np.argmax(np.abs(s[:-1])))  # exclut le dernier point (rupture triviale en fin de série)
    stat = float(np.abs(s[k]))
    return {
        "changepoint_index": k, "cusum_statistic": stat,
        "mean_before": float(x[:k + 1].mean()), "mean_after": float(x[k + 1:].mean()),
    }


def cusum_permutation_test(signal, n_permutations, seed, progress=True):
    """Loi nulle EXACTE par permutation (même logique que l'amendement A3) : aucune hypothèse
    paramétrique sur la distribution du signal n'est nécessaire."""
    rng = np.random.default_rng(seed)
    x = np.asarray(signal, dtype=float)
    observed = cusum_single_changepoint(x)

    null_stats = np.empty(n_permutations)
    t0 = time.time()
    for i in range(n_permutations):
        null_stats[i] = cusum_single_changepoint(rng.permutation(x))["cusum_statistic"]
        if progress and (i + 1) % max(1, n_permutations // 20) == 0:
            print(f"  CUSUM permutation : {i + 1}/{n_permutations} ({time.time() - t0:.1f}s)", end="\r")
    if progress:
        print()
    p_value = (float((null_stats >= observed["cusum_statistic"]).sum()) + 1) / (n_permutations + 1)
    return {**observed, "p_value_permutation": p_value, "n_permutations": n_permutations, "seed": seed}


def ruptures_pelt_breakpoints(signal, model="l2"):
    """Recoupement descriptif via la bibliothèque `ruptures`. Pénalité BIC standard
    (log(n) * variance du signal), fixée AVANT d'inspecter le résultat — mais aucune p-value
    n'accompagne cette pénalité (non calibrée par permutation) : à lire comme indicatif seulement.
    """
    try:
        import ruptures as rpt
        x = np.asarray(signal, dtype=float)
        n = len(x)
        pen = float(np.log(n) * np.var(x))
        algo = rpt.Pelt(model=model).fit(x)
        bkps = algo.predict(pen=pen)
        return {"breakpoints": bkps[:-1], "penalty": pen, "model": model}  # dernier = len(signal)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
