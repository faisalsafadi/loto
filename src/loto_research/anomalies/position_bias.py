"""Recherche de biais de POSITION (Cahier des charges §20) — EXPLORATOIRE UNIQUEMENT.

Hypothèse NON vérifiée : les colonnes n1..n6 du fichier source pourraient représenter l'ordre réel
de sortie des boules (elles ne sont pas triées par ordre croissant — voir diagnostic Phase 1, ex.
première ligne 8,46,39,41,33,40). Aucune source officielle ne confirme que ces colonnes correspondent
à l'ordre physique d'extraction plutôt qu'à un artefact de saisie. Ce test reste donc EXPLORATOIRE
et ne peut en aucun cas justifier une conclusion sur un biais mécanique (absence d'information
physique sur la machine, §20 du Cahier).
"""
import pandas as pd

from loto_research.statistics.uniformity import chi_square_uniformity
from loto_research.validation.schema import MAIN_MAX, MAIN_MIN, NUMBER_COLUMNS


def position_uniformity_tests(df):
    """Pour chaque position (colonne) 1..6 : χ²(48) classique (comme pour le complémentaire,
    amendement A7). Une position ISOLÉE fournit un seul numéro par tirage : pas de corrélation à
    corriger dans le décompte marginal sur tous les tirages (la corrélation entre positions ne
    joue qu'AU SEIN d'un même tirage, pas nécessaire ici puisqu'on teste une colonne à la fois)."""
    n = len(df)
    expected = n / 49
    rows = []
    for col in NUMBER_COLUMNS:
        counts = pd.Series(0, index=range(MAIN_MIN, MAIN_MAX + 1), dtype="int64")
        counts.update(df[col].value_counts())
        res = chi_square_uniformity(counts.values, [expected] * 49)
        rows.append({"position": col, **res})
    return pd.DataFrame(rows)
