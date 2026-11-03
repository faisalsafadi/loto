"""Distributions combinatoires EXACTES pour un tirage de 6 numéros distincts parmi 49 (Phase 3).

Ce sont des lois de référence exactes (dénombrement), pas des approximations asymptotiques —
elles évitent d'invoquer le CLT ou une loi normale là où un calcul exact est possible.
"""
from functools import lru_cache
from math import comb

import numpy as np
from scipy.stats import hypergeom

MAIN_MIN, MAIN_MAX, DRAW_SIZE = 1, 49, 6
ODD_NUMBERS = 25    # 1,3,...,49 => 25 nombres impairs entre 1 et 49
LOW_NUMBERS = 24    # 1..24


def odd_count_pmf():
    """P(nombre de numéros impairs parmi les 6 = k), k=0..6. Hypergéométrique exacte :
    49 numéros dont 25 impairs, on en tire 6 sans remise."""
    k = np.arange(0, DRAW_SIZE + 1)
    return k, hypergeom.pmf(k, MAIN_MAX, ODD_NUMBERS, DRAW_SIZE)


def low_count_pmf():
    """P(nombre de numéros <= 24 parmi les 6 = k), k=0..6. Même principe (24 numéros "bas")."""
    k = np.arange(0, DRAW_SIZE + 1)
    return k, hypergeom.pmf(k, MAIN_MAX, LOW_NUMBERS, DRAW_SIZE)


@lru_cache(maxsize=4)
def sum_distribution_exact(max_number=MAIN_MAX, draw_size=DRAW_SIZE):
    """Distribution exacte de la somme d'un tirage de `draw_size` numéros distincts parmi
    1..max_number, par dénombrement (programmation dynamique façon 0/1-knapsack).

    Retourne (sums, probabilities) : deux tableaux numpy de même longueur, probabilities somme à 1.
    """
    dp = [dict() for _ in range(draw_size + 1)]
    dp[0][0] = 1
    for n in range(1, max_number + 1):
        top_k = min(draw_size, n)
        for k in range(top_k, 0, -1):  # ordre décroissant : ne pas réutiliser n deux fois dans la même passe
            for s, c in list(dp[k - 1].items()):
                dp[k][s + n] = dp[k].get(s + n, 0) + c

    total = dp[draw_size]
    n_subsets = comb(max_number, draw_size)
    if sum(total.values()) != n_subsets:
        raise AssertionError(
            f"dénombrement incorrect : {sum(total.values())} sous-ensembles trouvés, "
            f"C({max_number},{draw_size})={n_subsets} attendus"
        )
    sums = np.array(sorted(total))
    probs = np.array([total[s] for s in sums], dtype=float) / n_subsets
    return sums, probs
