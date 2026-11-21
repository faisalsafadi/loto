from math import comb

import pandas as pd
import pytest

from loto_research.anomalies.pairs_triplets import (
    confirm_candidates, count_pairs, count_triplets, draws_to_bitmasks, pair_probability,
    pairs_dataframe, split_exploration_confirmation, triplet_probability, triplets_dataframe,
)

NUMBER_COLUMNS = [f"n{i}" for i in range(1, 7)]


def _two_draws_df():
    # draw1={1,2,3,4,5,6} ; draw2={4,5,6,7,8,9} ; intersection = {4,5,6}
    return pd.DataFrame([
        {f"n{i + 1}": v for i, v in enumerate([1, 2, 3, 4, 5, 6])},
        {f"n{i + 1}": v for i, v in enumerate([4, 5, 6, 7, 8, 9])},
    ])


def test_pair_and_triplet_probability_hand_verified():
    assert pair_probability() == pytest.approx(comb(6, 2) / comb(49, 2))
    assert pair_probability() == pytest.approx(15 / 1176)
    assert triplet_probability() == pytest.approx(comb(6, 3) / comb(49, 3))
    assert triplet_probability() == pytest.approx(20 / 18424)


def test_count_pairs_hand_verified():
    masks = draws_to_bitmasks(_two_draws_df(), columns=NUMBER_COLUMNS)
    counts = count_pairs(masks)
    assert counts[(4, 5)] == 2    # 4 et 5 co-occurrent dans les DEUX tirages
    assert counts[(1, 2)] == 1    # uniquement dans le premier tirage
    assert counts[(1, 7)] == 0    # jamais ensemble
    assert len(counts) == comb(49, 2)


def test_count_triplets_hand_verified():
    masks = draws_to_bitmasks(_two_draws_df(), columns=NUMBER_COLUMNS)
    counts = count_triplets(masks)
    assert counts[(4, 5, 6)] == 2
    assert counts[(1, 2, 3)] == 1
    assert counts[(1, 2, 7)] == 0
    assert len(counts) == comb(49, 3)


def test_pairs_dataframe_structure():
    masks = draws_to_bitmasks(_two_draws_df(), columns=NUMBER_COLUMNS)
    df = pairs_dataframe(masks)
    assert len(df) == comb(49, 2)
    assert df["raw_p_value"].between(0, 1).all()
    assert df.loc[(df["i"] == 4) & (df["j"] == 5), "count"].iloc[0] == 2


def test_triplets_dataframe_structure():
    masks = draws_to_bitmasks(_two_draws_df(), columns=NUMBER_COLUMNS)
    df = triplets_dataframe(masks)
    assert len(df) == comb(49, 3)
    assert df["raw_p_value"].between(0, 1).all()


def test_split_exploration_confirmation_covers_all_rows_without_overlap():
    df = pd.DataFrame({"chronological_id": range(1, 101)})
    explore, confirm = split_exploration_confirmation(df)
    assert len(explore) == 50
    assert len(confirm) == 50
    assert set(explore["chronological_id"]).isdisjoint(set(confirm["chronological_id"]))
    assert set(explore["chronological_id"]) | set(confirm["chronological_id"]) == set(range(1, 101))
    assert explore["chronological_id"].max() < confirm["chronological_id"].min()


def test_confirm_candidates_uses_only_the_given_combo_not_a_new_search():
    df_confirm = _two_draws_df()
    candidates = pd.DataFrame([
        {"i": 4, "j": 5, "count": 10, "expected": 1.0},   # sur-represente en exploration
        {"i": 1, "j": 7, "count": 0, "expected": 1.0},    # sous-represente en exploration
    ])
    res = confirm_candidates(df_confirm, candidates, ["i", "j"], p=pair_probability(), count_fn=count_pairs)
    assert len(res) == 2
    row_45 = res[(res["i"] == 4) & (res["j"] == 5)].iloc[0]
    assert row_45["count_confirmation"] == 2  # recompte reellement sur df_confirm, pas invente
    assert row_45["direction"] == "greater"
    row_17 = res[(res["i"] == 1) & (res["j"] == 7)].iloc[0]
    assert row_17["count_confirmation"] == 0
    assert row_17["direction"] == "less"
