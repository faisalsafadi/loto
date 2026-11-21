import numpy as np
import pandas as pd
import pytest

from loto_research.temporal.consecutive_pairs import (
    build_consecutive_mask, draws_to_bitmasks, intersection_size_distribution,
    observed_mean_intersection, permutation_test_mean_intersection,
)
from loto_research.temporal.period_homogeneity import assign_period, homogeneity_test, period_frequency_table
from loto_research.temporal.runs import runs_test

NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]


def _draw_row(values, **extra):
    return {**{f"n{i + 1}": v for i, v in enumerate(values)}, **extra}


# ---------- consecutive_pairs ----------

def test_build_consecutive_mask_hand_traced_example():
    """Trace a la main :
    (1->2) N suit, ecart 2j -> valide
    (2->4) N ne suit pas -> invalide
    (4->1) N=1 (reset) mais ecart 5j>4 -> invalide
    (1->2) N suit, ecart 1j -> valide
    """
    df = pd.DataFrame({
        "chronological_id": [1, 2, 3, 4, 5],
        "draw_number_source": [1, 2, 4, 1, 2],
        "date": pd.to_datetime(["2020-01-01", "2020-01-03", "2020-01-05", "2020-01-10", "2020-01-11"]),
    })
    mask = build_consecutive_mask(df, max_date_gap_days=4)
    np.testing.assert_array_equal(mask, [True, False, False, True])


def test_draws_to_bitmasks_and_intersection_hand_verifiable():
    df = pd.DataFrame([
        _draw_row([1, 2, 3, 4, 5, 6], chronological_id=1),
        _draw_row([4, 5, 6, 7, 8, 9], chronological_id=2),      # intersection avec ligne 1 = {4,5,6} = 3
        _draw_row([10, 11, 12, 13, 14, 15], chronological_id=3),  # intersection avec ligne 2 = 0
    ])
    masks = draws_to_bitmasks(df, columns=NUMBER_COLUMNS)
    assert (masks[0] & masks[1]).bit_count() == 3
    assert (masks[1] & masks[2]).bit_count() == 0

    mean_int, n_pairs = observed_mean_intersection(masks, np.array([True, True]))
    assert n_pairs == 2
    assert mean_int == pytest.approx(1.5)


def test_permutation_test_reproducible_with_same_seed():
    df = pd.DataFrame([
        _draw_row(v, chronological_id=k + 1) for k, v in enumerate(
            [[1, 2, 3, 4, 5, 6], [4, 5, 6, 7, 8, 9], [10, 11, 12, 13, 14, 15], [1, 7, 13, 20, 30, 40]])
    ])
    masks = draws_to_bitmasks(df, columns=NUMBER_COLUMNS)
    valid_mask = np.array([True, True, True])
    a = permutation_test_mean_intersection(masks, valid_mask, n_permutations=50, seed=1, progress=False)
    b = permutation_test_mean_intersection(masks, valid_mask, n_permutations=50, seed=1, progress=False)
    assert a["p_value_permutation"] == b["p_value_permutation"]
    assert 0 <= a["p_value_permutation"] <= 1
    assert a["n_valid_pairs"] == 3


def test_intersection_size_distribution_sums_to_n_pairs():
    df = pd.DataFrame([
        _draw_row(v, chronological_id=k + 1) for k, v in
        enumerate([[1, 2, 3, 4, 5, 6], [4, 5, 6, 7, 8, 9], [10, 11, 12, 13, 14, 15]])
    ])
    masks = draws_to_bitmasks(df, columns=NUMBER_COLUMNS)
    res = intersection_size_distribution(masks, np.array([True, True]))
    assert sum(res["observed_counts"]) == res["n_pairs"] == 2
    assert sum(res["expected_counts"]) == pytest.approx(2, abs=1e-6)


# ---------- runs test ----------

def test_runs_test_hand_verified_example():
    """[1,1,1,0,0,0] : n1=3, n2=3, 2 suites, E[R]=2*3*3/6+1=4, Var=2*9*12/180=1.2."""
    res = runs_test([1, 1, 1, 0, 0, 0])
    assert res["n1"] == 3 and res["n2"] == 3
    assert res["n_runs"] == 2
    assert res["expected_runs"] == pytest.approx(4.0)
    assert res["z"] == pytest.approx((2 - 4) / (1.2 ** 0.5), rel=1e-6)


def test_runs_test_alternating_sequence_has_max_runs():
    res = runs_test([1, 0, 1, 0, 1, 0])
    assert res["n_runs"] == 6
    assert res["z"] > 0  # plus de suites que l'attendu sous H0 -> alternance, pas dependance positive


def test_runs_test_constant_sequence_is_degenerate_not_significant():
    res = runs_test([1, 1, 1, 1])
    assert res["p_value"] == 1.0


# ---------- period homogeneity ----------

def test_assign_period_boundaries():
    assert assign_period(2001) == "2001-2005"
    assert assign_period(2005) == "2001-2005"
    assert assign_period(2006) == "2006-2010"
    assert assign_period(2026) == "2021-2026"
    assert assign_period(2000) is None
    assert assign_period(2027) is None


def _fake_period_draws(counts_per_year, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for year, n in counts_per_year.items():
        for _ in range(n):
            picked = rng.choice(np.arange(1, 50), size=6, replace=False)
            rows.append(_draw_row(picked, year=year))
    return pd.DataFrame(rows)


def test_period_frequency_table_shape_and_totals():
    df = _fake_period_draws({2002: 20, 2008: 20, 2013: 20, 2018: 20, 2023: 20})
    table = period_frequency_table(df, NUMBER_COLUMNS)
    assert table.shape == (5, 49)
    assert table.values.sum() == 5 * 20 * 6


def test_homogeneity_test_returns_valid_pvalue_and_df():
    df = _fake_period_draws({2002: 50, 2008: 50, 2013: 50, 2018: 50, 2023: 50}, seed=1)
    res = homogeneity_test(df, NUMBER_COLUMNS)
    assert 0 <= res["p_value"] <= 1
    assert res["df"] == (5 - 1) * (49 - 1)
