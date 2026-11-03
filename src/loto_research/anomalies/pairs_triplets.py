"""Recherche de structures : paires et triplets (Cahier §16-17, HYPOTHESES.md H005-H006).

Comme pour les numéros individuels (Phase 4) et le complémentaire, une paire/triplet FIXÉ a une
probabilité CONSTANTE par tirage (p_pair=C(6,2)/C(49,2), p_triplet=C(6,3)/C(49,3)), et les tirages
sont indépendants entre eux : le compte sur N tirages suit EXACTEMENT une loi binomiale. Aucune
simulation Monte-Carlo n'est nécessaire pour le test lui-même — seul le pipeline exploration /
confirmation hors-échantillon protège contre le p-hacking sur un aussi grand nombre de tests.
"""
from itertools import combinations
from math import comb

import pandas as pd
from scipy.stats import binomtest

from loto_research.validation.schema import MAIN_MAX, MAIN_MIN, NUMBER_COLUMNS

DRAW_SIZE = 6


def pair_probability():
    return comb(DRAW_SIZE, 2) / comb(MAIN_MAX, 2)


def triplet_probability():
    return comb(DRAW_SIZE, 3) / comb(MAIN_MAX, 3)


def draws_to_bitmasks(df, columns=NUMBER_COLUMNS):
    """Même encodage que la Phase 5 : un entier par tirage, bit i = numéro i présent."""
    arr = df[columns].to_numpy()
    return [int(sum(1 << int(v) for v in row)) for row in arr]


def _present_numbers(mask):
    return [i for i in range(MAIN_MIN, MAIN_MAX + 1) if mask & (1 << i)]


def count_pairs(masks):
    """Occurrence conjointe de chaque paire (i,j), i<j. Toutes les C(49,2)=1176 paires sont
    présentes dans le résultat, y compris celles jamais observées (count=0)."""
    counts = {pair: 0 for pair in combinations(range(MAIN_MIN, MAIN_MAX + 1), 2)}
    for m in masks:
        for pair in combinations(_present_numbers(m), 2):
            counts[pair] += 1
    return counts


def count_triplets(masks):
    """Occurrence conjointe de chaque triplet (i,j,k), i<j<k. Les 18424 triplets possibles sont
    tous présents dans le résultat, y compris ceux jamais observés (count=0)."""
    counts = {t: 0 for t in combinations(range(MAIN_MIN, MAIN_MAX + 1), 3)}
    for m in masks:
        for t in combinations(_present_numbers(m), 3):
            counts[t] += 1
    return counts


def pairs_dataframe(masks, p=None):
    p = p if p is not None else pair_probability()
    n = len(masks)
    counts = count_pairs(masks)
    rows = []
    for (i, j), c in counts.items():
        res = binomtest(c, n, p, alternative="two-sided")
        rows.append({"i": i, "j": j, "count": c, "expected": n * p, "raw_p_value": res.pvalue,
                     "effect_ratio": (c / (n * p)) if n * p > 0 else float("nan")})
    return pd.DataFrame(rows)


def triplets_dataframe(masks, p=None):
    p = p if p is not None else triplet_probability()
    n = len(masks)
    counts = count_triplets(masks)
    rows = []
    for (i, j, k), c in counts.items():
        res = binomtest(c, n, p, alternative="two-sided")
        rows.append({"i": i, "j": j, "k": k, "count": c, "expected": n * p, "raw_p_value": res.pvalue,
                     "effect_ratio": (c / (n * p)) if n * p > 0 else float("nan")})
    return pd.DataFrame(rows)


def split_exploration_confirmation(df):
    """Scinde le dataset en deux AVANT tout calcul sur les paires/triplets (pas de data snooping) :
    exploration = première moitié chronologique, confirmation = seconde moitié."""
    d = df.sort_values("chronological_id").reset_index(drop=True)
    mid = len(d) // 2
    return d.iloc[:mid].reset_index(drop=True), d.iloc[mid:].reset_index(drop=True)


def confirm_candidates(df_confirmation, candidates, combo_cols, p, count_fn):
    """Teste en confirmation UNIQUEMENT les candidats identifiés en exploration (jamais de nouvelle
    recherche ici). Test UNILATÉRAL dans le sens observé en exploration (sur-représenté reste testé
    comme sur-représenté, et inversement) : c'est une confirmation, pas une seconde exploration."""
    masks = draws_to_bitmasks(df_confirmation)
    n = len(masks)
    all_counts = count_fn(masks)
    rows = []
    for _, cand in candidates.iterrows():
        combo = tuple(int(cand[c]) for c in combo_cols)
        c = all_counts.get(combo, 0)
        direction = "greater" if cand["count"] > cand["expected"] else "less"
        res = binomtest(c, n, p, alternative=direction)
        row = {col: cand[col] for col in combo_cols}
        row.update({"count_confirmation": c, "expected_confirmation": n * p,
                    "direction": direction, "raw_p_value_confirmation": res.pvalue})
        rows.append(row)
    return pd.DataFrame(rows)
