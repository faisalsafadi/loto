"""Noyau d'analyse rapide de `loto analyze` (SPEC_V2 §4, M2). Réutilise les fonctions de v1 sans les
modifier : H001, H002, H003, H004, H007. Les fonctions de v1 sont écrites pour le 6/49 ; tant
qu'elles ne sont pas généralisées, tout autre jeu est refusé explicitement."""
import math

from loto_research.statistics.descriptive import bonus_frequencies, number_frequencies
from loto_research.statistics.multiple_testing import fdr_bh
from loto_research.statistics.uniformity import chi_square_uniformity, monte_carlo_uniformity_pvalue
from loto_research.temporal.consecutive_pairs import (
    build_consecutive_mask, draws_to_bitmasks, permutation_test_mean_intersection,
)
from loto_research.temporal.gaps import per_number_gap_test
from loto_research.temporal.period_homogeneity import homogeneity_test
from loto_research.validation.schema import NUMBER_COLUMNS

P_MAIN = 6 / 49
P_BONUS = 1 / 49


def ensure_supported_game(game):
    if not (game["k"] == 6 and game["n_max"] == 49 and game["bonus_range"] == 49 and game["bonus_exclusive"]):
        raise NotImplementedError(
            f"Le jeu '{game['name']}' (k={game['k']}, N={game['n_max']}) n'est pas encore supporté : "
            f"les fonctions d'analyse de v1 sont écrites pour le 6/49 avec complémentaire exclusif. "
            f"La généralisation k parmi N est prévue (SPEC_V2 D4)."
        )


def _f(x):
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) else x


def _gap_family(df, columns, p):
    gaps = per_number_gap_test(df, columns, p)
    valid = gaps["p_value"].notna()
    corr = fdr_bh(gaps.loc[valid, "p_value"].tolist(), alpha=0.05)
    adjusted = list(corr["adjusted_p_value"])
    raw = gaps.loc[valid, "p_value"].tolist()
    return {
        "family_size": int(valid.sum()),
        "n_flagged": int(sum(a < 0.05 for a in adjusted)),
        "min_p_raw": _f(min(raw)) if raw else None,
        "min_p_adjusted": _f(min(adjusted)) if adjusted else None,
    }


def run_quick_analysis(df, n_sim, n_perm, seed, progress=False):
    """Retourne une liste de résultats {label, statistic, p_raw, p_adjusted, method, family_size, detail}."""
    n_draws = len(df)
    results = []

    # H001 : uniformité des principaux (test primaire = p-value Monte-Carlo, amendement A1)
    freq_main = number_frequencies(df)
    chi2_naive = chi_square_uniformity(freq_main["count"].values, freq_main["expected"].values)
    mc = monte_carlo_uniformity_pvalue(chi2_naive["chi2"], n_draws, n_sim, seed, progress=progress)
    results.append(dict(
        label="H001", statistic=_f(chi2_naive["chi2"]), p_raw=_f(mc["p_value_monte_carlo"]), p_adjusted=None,
        method="monte_carlo", family_size=1,
        detail={"chi2_df48_naif_p": _f(chi2_naive["p_value"]), "n_simulations": n_sim, "seed": seed},
    ))

    # H002 : uniformité du complémentaire (chi2 classique, amendement A7)
    freq_bonus = bonus_frequencies(df)
    chi2_bonus = chi_square_uniformity(freq_bonus["count"].values, freq_bonus["expected"].values)
    results.append(dict(
        label="H002", statistic=_f(chi2_bonus["chi2"]), p_raw=_f(chi2_bonus["p_value"]), p_adjusted=None,
        method="chi2_classique_df48", family_size=1, detail={},
    ))

    # H003 : intersection entre tirages réellement consécutifs (permutation, amendement A5)
    valid_mask = build_consecutive_mask(df)
    masks = draws_to_bitmasks(df, NUMBER_COLUMNS)
    h003 = permutation_test_mean_intersection(masks, valid_mask, n_perm, seed, progress=progress)
    results.append(dict(
        label="H003", statistic=_f(h003["observed_mean_intersection"]), p_raw=_f(h003["p_value_permutation"]),
        p_adjusted=None, method="permutation", family_size=1,
        detail={"n_valid_pairs": int(h003["n_valid_pairs"]), "expected_under_h0": _f(h003["expected_under_h0"]),
                "n_permutations": n_perm, "seed": seed},
    ))

    # H007 : homogénéité entre périodes (découpage unique pré-enregistré, amendement A3)
    for label, cols in (("H007_main", NUMBER_COLUMNS), ("H007_bonus", ["bonus"])):
        h = homogeneity_test(df, cols)
        results.append(dict(
            label=label, statistic=_f(h["chi2"]), p_raw=_f(h["p_value"]), p_adjusted=None,
            method="chi2_homogeneite", family_size=1, detail={"df": int(h["df"])},
        ))

    # H004 : gaps vs loi géométrique exacte, FDR-BH sur 49 numéros
    for label, cols, p in (("H004_main", NUMBER_COLUMNS, P_MAIN), ("H004_bonus", ["bonus"], P_BONUS)):
        g = _gap_family(df, cols, p)
        results.append(dict(
            label=label, statistic=float(g["n_flagged"]), p_raw=g["min_p_raw"], p_adjusted=g["min_p_adjusted"],
            method="fdr_bh", family_size=g["family_size"],
            detail={"statistic_is": "nombre de numéros significatifs après FDR-BH (alpha 0,05)",
                    "p_raw_is": "plus petite p-value brute de la famille"},
        ))
    return results
