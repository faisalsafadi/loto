"""Catalogue des tests exécutables par le registre d'hypothèses (SPEC_V2 §3-4, M3). Chaque test
tourne sur un sous-ensemble de tirages (ceux postérieurs à l'enregistrement) et retourne
{statistic, p_value, detail}. La direction du test (bilatéral / unilatéral) est fixée à
l'enregistrement, jamais après avoir vu les données."""
from loto_research.db.core import ValidationError
from loto_research.statistics.descriptive import number_frequencies
from loto_research.statistics.uniformity import chi_square_uniformity, monte_carlo_uniformity_pvalue
from loto_research.statistics.descriptive import bonus_frequencies
from loto_research.temporal.autocorrelation import per_number_autocorrelation
from loto_research.temporal.consecutive_pairs import (
    build_consecutive_mask, draws_to_bitmasks, permutation_test_mean_intersection,
)
from loto_research.validation.schema import NUMBER_COLUMNS


def _check_keys(params, allowed):
    unknown = set(params) - set(allowed)
    if unknown:
        raise ValidationError(f"Paramètres inconnus : {sorted(unknown)} (autorisés : {sorted(allowed)})")


def _check_min_int(params, key, minimum):
    if key in params and (not isinstance(params[key], int) or isinstance(params[key], bool) or params[key] < minimum):
        raise ValidationError(f"{key} doit être un entier >= {minimum}")


# --- uniformité des numéros principaux (Monte-Carlo, amendement A1) ---
def _validate_uniformity_main(game, params):
    _check_keys(params, {"n_sim"})
    _check_min_int(params, "n_sim", 1000)


def _run_uniformity_main(df, params, seed):
    n_sim = params.get("n_sim", 100000)
    freq = number_frequencies(df)
    chi = chi_square_uniformity(freq["count"].values, freq["expected"].values)
    mc = monte_carlo_uniformity_pvalue(chi["chi2"], len(df), n_sim, seed, progress=False)
    return {"statistic": float(chi["chi2"]), "p_value": float(mc["p_value_monte_carlo"]),
            "detail": {"n_sim": n_sim, "seed": seed}}


# --- uniformité du complémentaire (chi2 classique, amendement A7) ---
def _validate_uniformity_bonus(game, params):
    _check_keys(params, set())


def _run_uniformity_bonus(df, params, seed):
    freq = bonus_frequencies(df)
    chi = chi_square_uniformity(freq["count"].values, freq["expected"].values)
    return {"statistic": float(chi["chi2"]), "p_value": float(chi["p_value"]), "detail": {}}


# --- intersection entre tirages réellement consécutifs (permutation, amendement A5) ---
def _validate_consecutive_overlap(game, params):
    _check_keys(params, {"n_perm"})
    _check_min_int(params, "n_perm", 1000)


def _run_consecutive_overlap(df, params, seed):
    n_perm = params.get("n_perm", 20000)
    valid_mask = build_consecutive_mask(df)
    masks = draws_to_bitmasks(df, NUMBER_COLUMNS)
    res = permutation_test_mean_intersection(masks, valid_mask, n_perm, seed, progress=False)
    return {"statistic": float(res["observed_mean_intersection"]), "p_value": float(res["p_value_permutation"]),
            "detail": {"n_valid_pairs": int(res["n_valid_pairs"]), "n_perm": n_perm, "seed": seed}}


# --- autocorrélation lag-1 d'UNE valeur du complémentaire (cas de H009) ---
DIRECTIONS = ("two_sided", "positive")


def _validate_bonus_lag1(game, params):
    _check_keys(params, {"value", "direction"})
    if game["bonus_range"] is None:
        raise ValidationError("Ce jeu n'a pas de complémentaire")
    v = params.get("value")
    if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= game["bonus_range"]):
        raise ValidationError(f"value doit être un entier dans [1, {game['bonus_range']}]")
    if params.get("direction", "two_sided") not in DIRECTIONS:
        raise ValidationError(f"direction doit être l'une de {DIRECTIONS}")


def _run_bonus_lag1(df, params, seed):
    value = params["value"]
    direction = params.get("direction", "two_sided")
    res = per_number_autocorrelation(df, ["bonus"])
    row = res[res["number"] == value].iloc[0]
    rho, z, p_two = float(row["rho"]), float(row["z"]), float(row["p_value"])
    if direction == "positive":
        p = p_two / 2 if rho > 0 else 1 - p_two / 2
    else:
        p = p_two
    return {"statistic": rho, "p_value": p,
            "detail": {"value": value, "direction": direction, "z": z, "p_two_sided": p_two, "n": int(row["n"])}}


CATALOG = {
    "uniformity_main": {"validate": _validate_uniformity_main, "run": _run_uniformity_main},
    "uniformity_bonus": {"validate": _validate_uniformity_bonus, "run": _run_uniformity_bonus},
    "consecutive_overlap": {"validate": _validate_consecutive_overlap, "run": _run_consecutive_overlap},
    "bonus_lag1": {"validate": _validate_bonus_lag1, "run": _run_bonus_lag1},
}
