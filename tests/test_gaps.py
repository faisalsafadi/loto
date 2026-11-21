import numpy as np
import pandas as pd
import pytest

from loto_research.temporal.gaps import (
    compare_gaps_to_geometric, geometric_gap_pmf, observed_gaps_for_number, per_number_gap_test,
)


def test_geometric_gap_pmf_hand_verified():
    """p=0.5, max_k=3 : pmf=[0.5,0.25,0.125] puis le dernier bin absorbe la queue -> [0.5,0.25,0.25]."""
    k, pmf = geometric_gap_pmf(0.5, 3)
    np.testing.assert_allclose(pmf, [0.5, 0.25, 0.25])
    assert pmf.sum() == pytest.approx(1.0)
    np.testing.assert_array_equal(k, [1, 2, 3])


def test_observed_gaps_for_number_hand_verified():
    df = pd.DataFrame({
        "chronological_id": [1, 2, 3, 4, 5, 6],
        "n1": [7, 1, 7, 2, 3, 7],
        "n2": [8, 8, 8, 8, 8, 8],
    })
    gaps = observed_gaps_for_number(df, ["n1", "n2"], 7)
    # numero 7 apparait aux chronological_id 1, 3, 6 -> gaps interieurs = 3-1=2, 6-3=3
    np.testing.assert_array_equal(gaps, [2, 3])


def test_observed_gaps_for_number_less_than_two_appearances_returns_empty():
    df = pd.DataFrame({"chronological_id": [1, 2, 3], "n1": [1, 2, 3]})
    assert len(observed_gaps_for_number(df, ["n1"], 99)) == 0
    assert len(observed_gaps_for_number(df, ["n1"], 1)) == 0  # une seule apparition -> pas de gap interieur


def test_compare_gaps_to_geometric_zero_chi2_when_matching_exactly():
    """p=0.5, max_k=2 -> pmf=[0.5,0.5]. 5 gaps de valeur 1, 5 gaps >=2 : correspond exactement."""
    gaps = np.array([1] * 5 + [5] * 5)
    res = compare_gaps_to_geometric(gaps, p=0.5, max_k=2)
    assert res["chi2"] == pytest.approx(0.0)


def test_per_number_gap_test_structure():
    rng = np.random.default_rng(0)
    rows = [
        {**{f"n{i + 1}": v for i, v in enumerate(rng.choice(np.arange(1, 50), size=6, replace=False))},
         "chronological_id": k + 1}
        for k in range(500)
    ]
    df = pd.DataFrame(rows)
    res = per_number_gap_test(df, [f"n{i}" for i in range(1, 7)], p=6 / 49)
    assert len(res) == 49
    assert (res["n_gaps"] > 0).all()  # 500 tirages, largement assez pour au moins 2 apparitions/numero
    assert res["p_value"].dropna().between(0, 1).all()
    assert res["theoretical_mean_gap"].nunique() == 1  # meme p pour tous les numeros -> meme valeur
    assert res["theoretical_mean_gap"].iloc[0] == pytest.approx(49 / 6)
