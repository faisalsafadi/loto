"""Corrections de comparaisons multiples (IMPLEMENTATION_SPEC §16).

Wrapper mince autour de statsmodels.stats.multitest.multipletests plutôt qu'une réimplémentation :
ce sont des algorithmes bien établis, la bibliothèque est déjà une dépendance du projet, et une
réimplémentation manuelle ajouterait un risque d'erreur sans bénéfice.
"""
import numpy as np
from statsmodels.stats.multitest import multipletests


def _correct(pvalues, method, alpha):
    pvalues = np.asarray(pvalues, dtype=float)
    reject, adjusted, _, _ = multipletests(pvalues, alpha=alpha, method=method)
    return {
        "method": method,
        "alpha": alpha,
        "number_of_tests": int(len(pvalues)),
        "raw_p_value": pvalues.tolist(),
        "adjusted_p_value": adjusted.tolist(),
        "reject": reject.tolist(),
    }


def bonferroni(pvalues, alpha=0.05):
    return _correct(pvalues, "bonferroni", alpha)


def holm(pvalues, alpha=0.05):
    return _correct(pvalues, "holm", alpha)


def fdr_bh(pvalues, alpha=0.05):
    return _correct(pvalues, "fdr_bh", alpha)
