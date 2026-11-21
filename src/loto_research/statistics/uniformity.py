"""Tests d'uniformité / d'adéquation (IMPLEMENTATION_SPEC §15, amendement A1)."""
import time

import numpy as np
from scipy import stats


def _merge_low_expected_bins(observed, expected, min_expected):
    """Fusionne les classes adjacentes, en partant des deux extrémités, tant qu'une classe a un
    effectif attendu < min_expected (règle usuelle de validité du chi2, ex. Cochran 1954).
    Les classes du MILIEU ne sont jamais fusionnées : seules les queues de distribution le sont,
    ce qui est adapté aux distributions unimodales (somme, pair/impair, bas/haut)."""
    obs, exp = list(map(float, observed)), list(map(float, expected))
    while len(exp) > 1 and exp[0] < min_expected:
        obs[1] += obs[0]
        exp[1] += exp[0]
        del obs[0]
        del exp[0]
    while len(exp) > 1 and exp[-1] < min_expected:
        obs[-2] += obs[-1]
        exp[-2] += exp[-1]
        del obs[-1]
        del exp[-1]
    return np.array(obs), np.array(exp)


def chi_square_uniformity(observed, expected, min_expected=None):
    """χ² de Pearson : chi2 = Σ (O-E)²/E (IMPLEMENTATION_SPEC §15).

    Si min_expected est fourni, les classes de faible effectif attendu sont fusionnées AVANT le
    calcul (règle de validité usuelle) ; n_bins_before/after_merge documentent l'opération.
    Ce test seul suffit pour le complémentaire (amendement A7 : df=49-1=48 est la vraie loi nulle,
    car un seul tirage catégoriel par ligne). Pour les 6 principaux, voir monte_carlo_uniformity_pvalue
    ci-dessous : df=48 n'est PAS la loi nulle (amendement A1), ce test seul est insuffisant.
    """
    observed = np.asarray(observed, dtype=float)
    expected = np.asarray(expected, dtype=float)
    n_bins_before = len(expected)
    if min_expected is not None:
        observed, expected = _merge_low_expected_bins(observed, expected, min_expected)
    chi2 = float(((observed - expected) ** 2 / expected).sum())
    df = len(expected) - 1
    p_value = float(1 - stats.chi2.cdf(chi2, df)) if df > 0 else float("nan")
    return {
        "chi2": chi2, "df": df, "p_value": p_value, "n": float(observed.sum()),
        "n_bins_before_merge": n_bins_before, "n_bins_after_merge": len(expected),
    }


def simulate_main_numbers_null_chi2(n_draws, n_simulations, seed, batch_size=100, progress=True):
    """Amendement A1 : simule n_simulations historiques de n_draws tirages de 6 numéros distincts
    parmi 49, et retourne le tableau des statistiques χ² de Pearson (une par simulation), calculées
    avec E = n_draws*6/49 — exactement comme pour les vraies données.

    Vectorisé par lots de `batch_size` simulations pour limiter la mémoire (IMPLEMENTATION_SPEC §70).
    Utilise argpartition (pas besoin de l'ordre complet, seulement des 6 numéros sélectionnés).
    """
    rng = np.random.default_rng(seed)
    expected = n_draws * 6 / 49
    out = np.empty(n_simulations, dtype=float)
    done = 0
    t0 = time.time()
    while done < n_simulations:
        b = min(batch_size, n_simulations - done)
        keys = rng.random((b, n_draws, 49))
        idx = np.argpartition(keys, 6, axis=2)[:, :, :6]
        for i in range(b):
            counts = np.bincount(idx[i].ravel(), minlength=49)
            out[done + i] = ((counts - expected) ** 2 / expected).sum()
        done += b
        if progress:
            elapsed = time.time() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = (n_simulations - done) / rate if rate > 0 else float("nan")
            print(f"  Monte-Carlo : {done}/{n_simulations}  "
                  f"({elapsed:.1f}s écoulées, ~{eta:.0f}s restantes)", end="\r")
    if progress:
        print()
    return out


def monte_carlo_uniformity_pvalue(observed_chi2, n_draws, n_simulations, seed, **kw):
    """Amendement A1 : p-value Monte-Carlo pour l'uniformité des 6 numéros principaux (H001).

    Retourne p_value_monte_carlo, expected_statistic_null (doit être proche de 43, PAS 48),
    n_simulations, seed — champs exigés en complément de chi_square_uniformity() (naïf, df=48,
    rapporté seulement à titre indicatif).
    """
    null_stats = simulate_main_numbers_null_chi2(n_draws, n_simulations, seed, **kw)
    # correction usuelle pour une p-value Monte-Carlo (North, Curtis & Sham, 2002) : évite p=0
    p_mc = (float((null_stats >= observed_chi2).sum()) + 1) / (n_simulations + 1)
    return {
        "p_value_monte_carlo": p_mc,
        "expected_statistic_null": float(null_stats.mean()),
        "std_statistic_null": float(null_stats.std(ddof=1)),
        "n_simulations": n_simulations,
        "seed": seed,
    }
