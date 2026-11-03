import numpy as np
import pandas as pd
import pytest

from loto_research.features.build import (
    build_feature_dataset, draw_level_lag_features, gap_current_matrix, rolling_frequency_matrix,
)

NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]


def _row(values, chronological_id):
    return {**{f"n{i + 1}": v for i, v in enumerate(values)}, "chronological_id": chronological_id}


def test_rolling_frequency_matrix_hand_verified():
    presence = np.array([[1, 0], [1, 0], [0, 1], [1, 0]])
    freq = rolling_frequency_matrix(presence, windows=[2])
    # k=2 : freq[t] = sum(presence[max(0,t-2):t])
    # t=0: vide -> [0,0] ; t=1: lignes[0:1] -> [1,0] ; t=2: lignes[0:2] -> [2,0] ; t=3: lignes[1:3] -> [1,1]
    expected = np.array([[0, 0], [1, 0], [2, 0], [1, 1]])
    np.testing.assert_array_equal(freq[2], expected)


def test_gap_current_matrix_hand_verified():
    """Un seul numero, apparitions aux indices 2 et 5 (0-indexe) sur 7 tirages."""
    presence = np.array([[0], [0], [1], [0], [0], [1], [0]])
    gap = gap_current_matrix(presence)
    expected = np.array([-1, -1, -1, 1, 2, 3, 1]).reshape(-1, 1)
    np.testing.assert_array_equal(gap, expected)


def test_gap_current_never_uses_the_appearance_at_t_itself():
    """A l'indice ou le numero apparait pour la premiere fois, le gap doit etre -1 (pas 0) :
    l'apparition AU temps t ne doit jamais compter comme deja vue depuis le point de vue de t."""
    presence = np.array([[0], [1], [0]])
    gap = gap_current_matrix(presence)
    assert gap[1, 0] == -1  # premiere apparition EN t=1 : gap a t=1 ne doit pas "voir" t=1


def test_draw_level_lag_features_hand_verified():
    df = pd.DataFrame([
        _row([1, 2, 3, 4, 5, 6], 1),
        _row([4, 5, 6, 7, 8, 9], 2),
        _row([7, 8, 9, 10, 11, 12], 3),
    ])
    res = draw_level_lag_features(df, NUMBER_COLUMNS)
    assert np.isnan(res["prev_sum"].iloc[0])
    assert res["prev_sum"].iloc[1] == 21   # somme du tirage 1 : 1+2+3+4+5+6
    assert res["prev_sum"].iloc[2] == 39   # somme du tirage 2 : 4+5+6+7+8+9
    assert np.isnan(res["prev_overlap"].iloc[0])
    assert np.isnan(res["prev_overlap"].iloc[1])
    assert res["prev_overlap"].iloc[2] == 3  # intersection({1..6},{4..9}) = {4,5,6}


def test_build_feature_dataset_structure_and_target_sum_per_draw():
    rng = np.random.default_rng(0)
    rows = [
        _row(sorted(rng.choice(np.arange(1, 50), size=6, replace=False).tolist()), k + 1)
        for k in range(30)
    ]
    df = pd.DataFrame(rows)
    feats = build_feature_dataset(df)
    assert len(feats) == 30 * 49
    # Dependance structurelle (IMPLEMENTATION_SPEC §29) : exactement 6 cibles=1 par tirage
    sums_per_draw = feats.groupby("chronological_id")["target"].sum()
    assert (sums_per_draw == 6).all()
    assert set(feats["number"]) == set(range(1, 50))


def test_build_feature_dataset_first_draw_has_no_history():
    df = pd.DataFrame([_row([1, 2, 3, 4, 5, 6], 1), _row([7, 8, 9, 10, 11, 12], 2)])
    feats = build_feature_dataset(df, windows=(10,))
    first = feats[feats["chronological_id"] == 1]
    assert (first["gap_current"] == -1).all()
    assert (first["freq_last_10"] == 0).all()
    assert first["prev_sum"].isna().all()
