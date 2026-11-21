"""Comparaison inter-périodes (H007) — découpage temporel UNIQUE pré-enregistré (amendement A3).

Toute autre segmentation (ex. blocs de 500 tirages) serait POST_HOC — voir HYPOTHESES.md A3.
"""
import pandas as pd
from scipy.stats import chi2_contingency

PERIODS = [(2001, 2005), (2006, 2010), (2011, 2015), (2016, 2020), (2021, 2026)]


def assign_period(year):
    for lo, hi in PERIODS:
        if lo <= year <= hi:
            return f"{lo}-{hi}"
    return None


def period_frequency_table(df, columns):
    """Table de contingence période x numéro (1..49), comptage brut."""
    d = df.copy()
    d["_period"] = d["year"].apply(assign_period)
    table = pd.DataFrame(0, index=[f"{lo}-{hi}" for lo, hi in PERIODS], columns=range(1, 50), dtype="int64")
    for period, g in d.groupby("_period"):
        vc = g[columns].melt(value_name="number")["number"].value_counts()
        table.loc[period, vc.index] = vc.values
    return table


def homogeneity_test(df, columns):
    """χ² d'indépendance période x numéro. H0 : même distribution de fréquence dans les 5 périodes
    (test PRIMAIRE de H007, amendement A2)."""
    table = period_frequency_table(df, columns)
    chi2, p, dof, expected = chi2_contingency(table)
    return {
        "chi2": float(chi2), "df": int(dof), "p_value": float(p),
        "table": table, "expected": pd.DataFrame(expected, index=table.index, columns=table.columns),
    }
