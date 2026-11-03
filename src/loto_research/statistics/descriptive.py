"""Statistiques descriptives (Cahier des charges §11 ; IMPLEMENTATION_SPEC §13-14).

Aucune fonction ici ne qualifie un numéro de "chaud" ou "froid" : ce sont des observations et
des calculs, l'interprétation prédictive est explicitement hors de portée (Cahier §11).
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

from loto_research.statistics.exact_distributions import (
    low_count_pmf, odd_count_pmf, sum_distribution_exact,
)
from loto_research.statistics.uniformity import chi_square_uniformity
from loto_research.validation.schema import MAIN_MAX, MAIN_MIN, NUMBER_COLUMNS


def number_frequencies(df, columns=NUMBER_COLUMNS):
    """Fréquence, écart à l'espérance, IC95 et z-score PAR NUMÉRO 1..49 (descriptif).

    p = len(columns)/49 : 6/49 pour les principaux (columns=NUMBER_COLUMNS), 1/49 pour le
    complémentaire (columns=["bonus"]).
    """
    n_draws = len(df)
    p = len(columns) / 49
    counts = pd.Series(0, index=range(MAIN_MIN, MAIN_MAX + 1), dtype="int64")
    vc = df[columns].melt(value_name="number")["number"].value_counts()
    counts.update(vc)

    expected = n_draws * p
    variance = n_draws * p * (1 - p)  # variance MARGINALE par numéro (IMPLEMENTATION_SPEC §14) ;
    sd = variance ** 0.5              # descriptive uniquement, ne tient pas compte des corrélations
    z = (counts.values - expected) / sd if sd > 0 else np.zeros(len(counts))
    ci_low = expected + norm.ppf(0.025) * sd
    ci_high = expected + norm.ppf(0.975) * sd

    return pd.DataFrame({
        "number": counts.index.values, "count": counts.values, "expected": expected,
        "deviation": counts.values - expected, "z_score": z,
        "ci95_low": ci_low, "ci95_high": ci_high,
    }).sort_values("number").reset_index(drop=True)


def bonus_frequencies(df):
    return number_frequencies(df, columns=["bonus"])


def _period_frequencies(df, period_col, columns):
    rows = []
    for period, g in df.groupby(period_col):
        f = number_frequencies(g, columns=columns)
        f.insert(0, period_col, period)
        rows.append(f[[period_col, "number", "count"]])
    return pd.concat(rows, ignore_index=True)


def annual_frequencies(df, columns=NUMBER_COLUMNS):
    """Compte par numéro et par année (observation brute, sans IC — l'effectif annuel est trop
    petit pour un z-score individuel fiable ; voir plutôt Phase 5/7 pour la stabilité temporelle)."""
    return _period_frequencies(df, "year", columns)


def monthly_frequencies(df, columns=NUMBER_COLUMNS):
    return _period_frequencies(df, "month", columns)


def sum_distribution(df):
    """Distribution de la somme des 6 numéros vs distribution EXACTE (dénombrement, pas CLT)."""
    s = df[NUMBER_COLUMNS].sum(axis=1)
    sums, probs = sum_distribution_exact()
    exp_mean = float((sums * probs).sum())
    exp_var = float(((sums - exp_mean) ** 2 * probs).sum())

    obs_counts = s.value_counts().reindex(sums, fill_value=0).values
    exp_counts = probs * len(s)
    chi2_res = chi_square_uniformity(obs_counts, exp_counts, min_expected=5)

    return {
        "n": int(len(s)),
        "observed_mean": float(s.mean()), "observed_median": float(s.median()),
        "observed_var": float(s.var(ddof=1)),
        "observed_quantiles": {str(q): float(v) for q, v in s.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).items()},
        "theoretical_mean": exp_mean, "theoretical_var": exp_var,
        "chi_square_vs_exact_distribution": chi2_res,
    }


def odd_even_distribution(df):
    """Nombre de numéros impairs par tirage (0..6) vs hypergéométrique EXACTE."""
    odd_count = df[NUMBER_COLUMNS].apply(lambda row: int(sum(v % 2 == 1 for v in row)), axis=1)
    k, p = odd_count_pmf()
    obs = odd_count.value_counts().reindex(k, fill_value=0).values
    exp = p * len(odd_count)
    return {
        "n": int(len(odd_count)),
        "observed_distribution": {int(kk): int(o) for kk, o in zip(k, obs)},
        "expected_distribution": {int(kk): float(e) for kk, e in zip(k, exp)},
        "chi_square_vs_exact_hypergeometric": chi_square_uniformity(obs, exp, min_expected=5),
    }


def low_high_distribution(df):
    """Nombre de numéros <=24 par tirage (0..6) vs hypergéométrique EXACTE."""
    low_count = df[NUMBER_COLUMNS].apply(lambda row: int(sum(v <= 24 for v in row)), axis=1)
    k, p = low_count_pmf()
    obs = low_count.value_counts().reindex(k, fill_value=0).values
    exp = p * len(low_count)
    return {
        "n": int(len(low_count)),
        "observed_distribution": {int(kk): int(o) for kk, o in zip(k, obs)},
        "expected_distribution": {int(kk): float(e) for kk, e in zip(k, exp)},
        "chi_square_vs_exact_hypergeometric": chi_square_uniformity(obs, exp, min_expected=5),
    }
