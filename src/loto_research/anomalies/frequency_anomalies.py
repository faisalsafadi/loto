"""Anomalies de fréquence par numéro, avec tests EXACTS (pas Monte-Carlo) et correction multiple.

Pourquoi un test exact suffit ici (contrairement au test joint des 6 numéros de la Phase 3) :
pour UN numéro fixé, l'indicateur "apparu dans le tirage t" est i.i.d. Bernoulli(p) d'un tirage à
l'autre (les tirages sont indépendants entre eux). Le compte sur N tirages suit donc exactement
Binomial(N, p) — aucune approximation, aucune simulation requise. La corrélation entre numéros
(tirage sans remise) n'existe qu'AU SEIN d'un même tirage, pas d'un tirage à l'autre pour un même numéro.
"""
import pandas as pd
from scipy.stats import binomtest

from loto_research.validation.schema import MAIN_MAX, MAIN_MIN


def per_number_binomial_test(df, columns, p):
    """Test binomial exact bilatéral, pour chaque numéro 1..49, sur les colonnes données.

    columns=NUMBER_COLUMNS, p=6/49 pour les principaux ; columns=["bonus"], p=1/49 pour le complémentaire.
    """
    n = len(df)
    counts = pd.Series(0, index=range(MAIN_MIN, MAIN_MAX + 1), dtype="int64")
    vc = df[columns].melt(value_name="number")["number"].value_counts()
    counts.update(vc)

    rows = []
    for number, count in counts.items():
        res = binomtest(int(count), n, p, alternative="two-sided")
        rows.append({
            "number": int(number), "count": int(count), "expected": n * p, "raw_p_value": res.pvalue,
        })
    return pd.DataFrame(rows).sort_values("number").reset_index(drop=True)


def classify_anomaly_level(adjusted_p, alpha=0.05):
    """Niveau A (observation) ou B (anomalie statistique brute), Cahier des charges §2.

    Niveau C exige la survie à une investigation multi-période/indépendante (Phases 5-7) : jamais
    attribué ici. Niveau D exige une validation hors-échantillon (Phase 10) : jamais avant.
    """
    return "B" if adjusted_p < alpha else "A"
